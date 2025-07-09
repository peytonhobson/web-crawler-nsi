#!/usr/bin/env python3
import re
from chunk_content.chunk_utils import character_chunk_documents
from langchain_core.documents import Document


def extract_f_code_from_page(text: str) -> str:
    """
    Extract f-code from page text using regex.
    F-codes are defined as the letter 'f' followed by 5-7 digits.

    Args:
        text: The text to search for f-codes

    Returns:
        Single f-code found in the text, or None if not found
    """
    if not text:
        return None

    # Regex pattern: f followed by 5-7 digits (case insensitive)
    pattern = r"[fF]\d{5,7}"
    match = re.search(pattern, text)

    # Return the first f-code found, converted to lowercase for consistency
    return match.group(0).lower() if match else None


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

            # Check if this page contains an f-code
            page_f_code = extract_f_code_from_page(content)

            # Create document metadata
            metadata = {
                "url": url,
                "page_path": result.page_path,
            }

            # Add f-code to metadata if found on the page
            if page_f_code:
                metadata["f_code"] = page_f_code
                print(f"Found f-code '{page_f_code}' on page: {url}")

            # Create Document object
            doc = Document(
                page_content=content,
                metadata=metadata,
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
