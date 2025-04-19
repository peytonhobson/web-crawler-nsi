from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import (
    OpenAIEmbeddings,
)  # or use HuggingFaceEmbeddings for lower cost
from langchain_core.documents import Document


def semantic_chunk_documents(
    docs, embedding_model_name="text-embedding-3-small", buffer_size=3, **kwargs
):
    # Choose embedding model: OpenAI (high performance, higher cost) or
    # HuggingFace (lower cost)
    embedding_model = OpenAIEmbeddings(model=embedding_model_name)

    chunker = SemanticChunker(
        embeddings=embedding_model,
        buffer_size=buffer_size,  # Number of sentences per group
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=90,  # Optional: tune for more/less chunks
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

    # docs: list of langchain_core.documents.Document
    chunked_docs = chunker.split_documents(cleaned_docs)

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
            }
        )

        # Create Document with original chunk text
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
