#!/usr/bin/env python3
"""
Document Chunking Script

This script takes crawl results, chunks them using spaCy, and returns the chunks.
"""

from chunk_content.chunk_utils import chunk_documents
from langchain_core.documents import Document


def chunk_content(crawl_results, config=None):
    """
    Chunks content from crawl results.

    Args:
        crawl_results (list): List of crawl results with markdown content.
        config: Optional configuration object with chunking parameters.

    Returns:
        list: List of chunk objects with content and metadata
    """
    # Create Document objects from crawl results
    docs = []
    file_count = 0

    print(f"Processing {len(crawl_results)} crawl results")
    for result in crawl_results:
        try:
            content = result.markdown
            url = result.url

            # Create Document object
            doc = Document(
                page_content=content,
                metadata={
                    "url": url,
                    "page_path": result.page_path,
                },
            )
            docs.append(doc)
            file_count += 1
            print(f"Added document from crawl: {url}")
        except Exception as e:
            print(f"Error processing crawl result {result.url}: {e}")

    print(f"\nSuccessfully processed {file_count} files")
    print("\n🔪 Chunking documents...")

    # Use config parameters if provided
    chunk_size = 500
    overlap_ratio = 0.2

    if config:
        chunk_size = getattr(config, "chunk_size", chunk_size)
        overlap_ratio = getattr(config, "chunk_overlap_ratio", overlap_ratio)

    # Chunk the documents with configuration parameters
    chunks = chunk_documents(docs, chunk_size=chunk_size, overlap_ratio=overlap_ratio)
    print(f"Created {len(chunks)} chunks from {len(docs)} documents")

    # Return the chunks
    return chunks
