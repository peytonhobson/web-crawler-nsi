#!/usr/bin/env python3
from chunk_content.chunk_utils import character_chunk_documents
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

    if config:
        # Configurable chunk size and overlap
        chunk_size = getattr(config, "chunk_size", 2000) if config else 2000
        chunk_overlap = getattr(config, "chunk_overlap", 200) if config else 200
    else:
        chunk_size = 2000
        chunk_overlap = 200

    # Chunk the documents with configuration parameters
    chunks = character_chunk_documents(
        docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    print(f"Created {len(chunks)} chunks from {len(docs)} documents")

    # Return the chunks
    return chunks
