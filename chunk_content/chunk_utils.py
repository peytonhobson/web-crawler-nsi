from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def character_chunk_documents(docs, chunk_size=2000, chunk_overlap=200, **kwargs):
    """
    Chunk documents using character-based splitting optimized for LLM
    processing.

    Args:
        docs: List of Document objects to chunk
        chunk_size: Maximum characters per chunk (default 2000 for good
                   LLM context)
        chunk_overlap: Character overlap between chunks (default 200 for
                      continuity)
        **kwargs: Additional parameters for the text splitter

    Returns:
        List of chunked Document objects
    """
    # Create character-based text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
        # Try to split on paragraphs first
        separators=["\n\n", "\n", " ", ""],
        **kwargs,
    )

    # Clean document content before chunking
    cleaned_docs = []
    for doc in docs:
        # Apply text cleaning to document content
        cleaned_content = clean_text(doc.page_content)
        # Create new document with cleaned content
        cleaned_doc = Document(
            page_content=cleaned_content,
            metadata=doc.metadata if hasattr(doc, "metadata") else {},
        )
        cleaned_docs.append(cleaned_doc)

    # Split documents into chunks
    chunked_docs = text_splitter.split_documents(cleaned_docs)

    all_docs = []
    page_count_map = {}

    for i, doc in enumerate(chunked_docs):
        # Set metadata
        has_metadata = hasattr(doc, "metadata") and doc.metadata
        metadata = doc.metadata.copy() if has_metadata else {}

        page_path = doc.metadata.get("page_path", "unknown")
        page_count = page_count_map.get(page_path, 1)
        page_count_map[page_path] = page_count + 1

        metadata.update(
            {
                "url": doc.metadata.get("url", "unknown"),
                "page_path": page_path,
                "chunk_name": f"{page_path}-{page_count}",
                "chunk_size": len(doc.page_content),
            }
        )

        # Create Document with chunk text
        chunk_doc = Document(page_content=doc.page_content, metadata=metadata)
        all_docs.append(chunk_doc)

    return all_docs


def clean_text(text: str) -> str:
    """Clean and normalize text, preserving original formatting."""
    # Only do minimal cleaning to preserve formatting
    # Remove multiple newlines and clean up spacing
    cleaned_text = text.replace("\r\n", "\n")
    cleaned_text = "\n".join(line.strip() for line in cleaned_text.split("\n"))
    return cleaned_text
