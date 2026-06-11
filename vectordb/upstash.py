#!/usr/bin/env python3
"""
Upstash Vector uploader — NSI fork.

Same as the upstream UpstashUploader but preserves the NSI-specific ``f_code``
metadata field: if a record carries an f-code (set by chunk_content.py's
extract_f_code_from_page), it is stored in Upstash metadata so that
dialogue-foundry-nsi can filter results by facility/property code.
"""

import logging
import re
import time
import unicodedata
from datetime import datetime, timedelta

from upstash_vector import Index
from upstash_vector.types import Data

logger = logging.getLogger(__name__)


class UpstashUploader:
    """
    Handles connecting to Upstash Vector, uploading new records using the
    built-in embedding model, and deleting outdated web-scraped records by
    timestamp within the company's namespace.
    """

    def __init__(
        self,
        url: str,
        token: str,
        namespace: str,
        chunk_id_prefix,
        record_retention_hours,
        upsert_batch_size,
        delete_old_records,
    ):
        self.namespace = namespace or ""
        self.chunk_id_prefix = chunk_id_prefix
        self.record_retention_hours = record_retention_hours
        self.upsert_batch_size = upsert_batch_size
        self.delete_old_records = delete_old_records

        self.index = Index(url=url, token=token)

        logger.info(f"Initializing Upstash Vector client, namespace: '{self.namespace}'")
        logger.info(f"Using chunk ID prefix: {self.chunk_id_prefix}")
        logger.info(f"Record retention hours: {self.record_retention_hours}")
        logger.info(f"Upsert batch size: {self.upsert_batch_size}")
        logger.info(f"Delete old records: {self.delete_old_records}")

    def sanitize_vector_id(self, id_str: str) -> str:
        normalized = unicodedata.normalize("NFKD", id_str)
        ascii_str = normalized.encode("ASCII", "ignore").decode("ASCII")
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", ascii_str)
        return sanitized

    def upsert_records(self, records) -> int:
        """
        Upsert the provided records into the namespace using Upstash's built-in
        embedding (raw text passed via the ``data`` field). NSI: preserves
        ``f_code`` in metadata when present on the record.
        """
        try:
            total_records = len(records)
            logger.info(
                f"Upserting {total_records} records into namespace: '{self.namespace}'"
            )

            formatted_records = []
            for record in records:
                # NSI: extract f-code from record attributes or metadata dict
                f_code = getattr(record, "f_code", None)
                if not f_code and hasattr(record, "metadata"):
                    f_code = record.metadata.get("f_code", None)

                metadata = {
                    "url": record.url,
                    "upload_timestamp": datetime.now().isoformat(),
                }
                if f_code:
                    metadata["f_code"] = f_code
                    logger.debug(
                        f"Added f-code '{f_code}' to chunk {record.chunk_name}"
                    )

                formatted_records.append(
                    Data(
                        id=self.sanitize_vector_id(
                            f"{self.chunk_id_prefix}_{record.chunk_name}"
                        ),
                        data=record.markdown,
                        metadata=metadata,
                    )
                )

            batch_size = self.upsert_batch_size
            total_batches = (len(formatted_records) + batch_size - 1) // batch_size
            records_upserted = 0

            logger.info(
                f"Processing {total_batches} batches of up to {batch_size} records each"
            )

            for i in range(total_batches):
                start_idx = i * batch_size
                end_idx = min(start_idx + batch_size, len(formatted_records))
                batch = formatted_records[start_idx:end_idx]

                self.index.upsert(vectors=batch, namespace=self.namespace)
                records_upserted += len(batch)

                logger.info(
                    f"Completed batch {i+1}/{total_batches}. "
                    f"Progress: {records_upserted}/{total_records}"
                )

                if i < total_batches - 1:
                    time.sleep(0.5)

            logger.info(
                f"Upsert operation completed. "
                f"Total records upserted: {records_upserted}"
            )
            return records_upserted
        except Exception as e:
            logger.error(f"Error during Upstash upsert: {e}")
            raise

    def delete_older_than_retention_period(self) -> int:
        """
        Delete records under this namespace whose id starts with the chunk
        prefix and whose ``upload_timestamp`` metadata is older than the
        retention period. Returns the number of deleted records.
        """
        if not self.delete_old_records:
            logger.info("Record deletion is disabled, skipping.")
            return 0

        try:
            retention_threshold = datetime.now() - timedelta(
                hours=self.record_retention_hours
            )
            logger.info(
                f"Deleting Upstash records older than "
                f"{self.record_retention_hours} hours "
                f"(threshold {retention_threshold.isoformat()})"
            )

            old_vector_ids = []
            cursor = ""
            while True:
                res = self.index.range(
                    cursor=cursor,
                    prefix=self.chunk_id_prefix,
                    limit=100,
                    include_metadata=True,
                    namespace=self.namespace,
                )

                for v in res.vectors:
                    upload_timestamp = (v.metadata or {}).get("upload_timestamp")
                    if not upload_timestamp:
                        logger.warning(f"Vector {v.id} has no upload_timestamp metadata")
                        continue
                    try:
                        if datetime.fromisoformat(upload_timestamp) < retention_threshold:
                            old_vector_ids.append(v.id)
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"Could not parse timestamp {upload_timestamp} "
                            f"for vector {v.id}: {e}"
                        )

                cursor = res.next_cursor
                if not cursor:
                    break

            total_deleted = 0
            batch_size = self.upsert_batch_size
            for i in range(0, len(old_vector_ids), batch_size):
                batch = old_vector_ids[i : i + batch_size]
                self.index.delete(ids=batch, namespace=self.namespace)
                total_deleted += len(batch)

            logger.info(
                f"Successfully deleted {total_deleted} Upstash vectors older than "
                f"{self.record_retention_hours} hours"
            )
            return total_deleted

        except Exception as e:
            logger.error(f"Error during deletion of old Upstash records: {e}")
            raise
