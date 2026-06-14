#!/usr/bin/env python3
"""
Upstash Vector uploader.

Upstash embeds raw text server-side when the index is created with a hosted
embedding model, so we upsert the chunk text via the ``data`` field rather than
precomputing vectors. Per-company data is isolated by namespace: one shared
Upstash index, one namespace per company.
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
        """
        Args:
            url: Upstash Vector REST URL
            token: Upstash Vector REST token
            namespace: Per-company namespace
            chunk_id_prefix: Prefix for chunk IDs
            record_retention_hours: How many hours to keep old records before deletion
            upsert_batch_size: Number of records to upsert in each batch
            delete_old_records: Whether to delete old records
        """
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
        """
        Sanitize vector ID to ensure it contains only ASCII characters.
        """
        normalized = unicodedata.normalize("NFKD", id_str)
        ascii_str = normalized.encode("ASCII", "ignore").decode("ASCII")
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", ascii_str)
        return sanitized

    def upsert_records(self, records) -> int:
        """
        Upsert the provided records into the namespace using Upstash's built-in
        embedding (raw text passed via the ``data`` field). Processed in batches.
        """
        try:
            total_records = len(records)
            logger.info(
                f"Upserting {total_records} records into namespace: '{self.namespace}'"
            )

            # Format all records as Data objects (data -> embedded text, returned
            # on query via include_data=True).
            formatted_records = []
            for record in records:
                formatted_records.append(
                    Data(
                        id=self.sanitize_vector_id(
                            f"{self.chunk_id_prefix}_{record.chunk_name}"
                        ),
                        data=record.markdown,
                        metadata={
                            "url": record.url,
                            "upload_timestamp": datetime.now().isoformat(),
                        },
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

                # Small pause between batches to avoid rate limiting
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

            # Scan the namespace by prefix, collecting stale ids across all pages
            # first, then delete — avoids mutating the set mid-pagination.
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

            # Delete the stale ids in batches
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
