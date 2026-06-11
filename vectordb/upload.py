#!/usr/bin/env python3
"""
Vector-store upload coordinator.

During the Pinecone -> Upstash migration this dual-writes every crawl to both
stores. Pinecone remains the source of truth (its failures propagate and abort
the run); Upstash writes are best-effort (failures are logged but never fail the
crawl). Upstash is only attempted when its credentials are present.

Once the migration is complete, drop the Pinecone branch and keep Upstash only.
"""

import logging
import os
import sys
from dotenv import load_dotenv

from vectordb.pinecone import PineconeUploader
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
    """Delete stale records then upsert the fresh batch, mirroring prior behavior."""
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
    Upload chunks to the configured vector store(s).

    Args:
        chunks: List of chunks to upload
        config: Optional configuration object
    """
    load_dotenv(override=True)

    kwargs = _vector_db_kwargs(config)

    # --- Pinecone: source of truth, failures abort the run ---
    required_vars = ["PINECONE_API_KEY", "PINECONE_INDEX_NAME"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    index_name = os.getenv("PINECONE_INDEX_NAME")
    pinecone_uploader = PineconeUploader(
        os.getenv("PINECONE_API_KEY"),
        index_name,
        **kwargs,
    )
    _run(pinecone_uploader, chunks, "pinecone")

    # --- Upstash: best-effort dual-write, never fails the crawl ---
    upstash_url = os.getenv("UPSTASH_VECTOR_REST_URL")
    upstash_token = os.getenv("UPSTASH_VECTOR_REST_TOKEN")
    if not (upstash_url and upstash_token):
        logger.info(
            "Upstash not configured (UPSTASH_VECTOR_REST_URL / "
            "UPSTASH_VECTOR_REST_TOKEN unset); skipping dual-write."
        )
        return

    # One shared Upstash index, one namespace per company. Default the namespace
    # to the Pinecone index name so each company maps 1:1 without extra config.
    namespace = (
        getattr(config, "upstash_namespace", None) if config else None
    ) or os.getenv("UPSTASH_NAMESPACE") or index_name

    try:
        upstash_uploader = UpstashUploader(
            upstash_url,
            upstash_token,
            namespace,
            **kwargs,
        )
        _run(upstash_uploader, chunks, "upstash")
    except Exception as e:
        logger.error(
            f"[upstash] dual-write failed (continuing; Pinecone is source "
            f"of truth): {e}"
        )
