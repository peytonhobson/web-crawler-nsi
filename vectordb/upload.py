#!/usr/bin/env python3
"""
Vector-store upload coordinator. Uploads crawled chunks to Upstash Vector.
"""

import logging
import os
import sys
from dotenv import load_dotenv

from vectordb.upstash import UpstashUploader

logger = logging.getLogger(__name__)


def _vector_db_kwargs(config):
    """Extract the shared uploader settings from the crawler config."""
    return dict(
        chunk_id_prefix=getattr(config, "chunk_id_prefix", None) if config else None,
        record_retention_hours=(
            getattr(config, "record_retention_hours", None) if config else None
        ),
        upsert_batch_size=getattr(config, "upsert_batch_size", None) if config else None,
        delete_old_records=(
            getattr(config, "delete_old_records", None) if config else None
        ),
    )


def _run(uploader, chunks, label):
    """Delete stale records then upsert the fresh batch."""
    deleted_count = uploader.delete_older_than_retention_period()
    logger.info(f"[{label}] Deleted {deleted_count} old records")

    upserted_count = uploader.upsert_records(chunks)
    logger.info(f"[{label}] Upserted {upserted_count} records")

    logger.info(
        f"[{label}] Operation complete: {upserted_count} records upserted, "
        f"{deleted_count} old records deleted."
    )


def upload_chunks(chunks, config=None):
    """
    Upload chunks to Upstash Vector.

    Args:
        chunks: List of chunks to upload
        config: Optional configuration object
    """
    load_dotenv(override=True)

    kwargs = _vector_db_kwargs(config)

    required_vars = ["UPSTASH_VECTOR_REST_URL", "UPSTASH_VECTOR_REST_TOKEN"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    namespace = (
        getattr(config, "upstash_namespace", None) if config else None
    ) or os.getenv("UPSTASH_NAMESPACE")

    if not namespace:
        logger.error("UPSTASH_NAMESPACE must be set")
        sys.exit(1)

    upstash_uploader = UpstashUploader(
        os.getenv("UPSTASH_VECTOR_REST_URL"),
        os.getenv("UPSTASH_VECTOR_REST_TOKEN"),
        namespace,
        **kwargs,
    )
    _run(upstash_uploader, chunks, "upstash")
