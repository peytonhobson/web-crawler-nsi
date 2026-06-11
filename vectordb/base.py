"""
Shared interface for vector-database uploaders.

Both the Pinecone and Upstash uploaders implement this interface so the
dual-write coordinator in ``vectordb/upload.py`` can treat them uniformly.
"""

from abc import ABC, abstractmethod


class VectorDBUploader(ABC):
    """Connects to a vector store, upserts crawled chunks, and prunes stale ones."""

    @abstractmethod
    def upsert_records(self, records) -> int:
        """Upsert the given records. Returns the number of records upserted."""

    @abstractmethod
    def delete_older_than_retention_period(self) -> int:
        """Delete records older than the retention window. Returns the count deleted."""
