import spacy
from langchain_core.documents import Document
import sys

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    print(f"Error loading spaCy model: {e}")
    print("Installing spaCy model...")
    import subprocess

    subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")


def chunk_documents(docs, chunk_size=700, overlap_ratio=0.3):
    """Split Document's page_content into chunks, preserving the exact original content."""
    all_chunks = []
    for doc in docs:
        original_content = doc.page_content

        # Use spaCy just for detecting sentence boundaries
        nlp_doc = nlp(original_content)

        # Get original sentence spans with exact original text
        sentences = []
        for sent in nlp_doc.sents:
            # Extract the exact original text for this sentence
            original_sent = original_content[sent.start_char : sent.end_char]
            sentences.append(original_sent)

        # Create chunks by combining sentences
        chunks = []
        current_chunk = []
        current_length = 0

        for sent in sentences:
            sent_length = len(nlp(sent))

            # Check if adding this sentence exceeds chunk size
            if current_length + sent_length > chunk_size and current_chunk:
                # Save current chunk
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(chunk_text)

                # Create overlap with some previous sentences if needed
                overlap_size = int(chunk_size * overlap_ratio)
                overlap_text = []
                overlap_length = 0

                # Add sentences from the end until we reach desired overlap
                for prev_sent in reversed(current_chunk):
                    prev_length = len(nlp(prev_sent))
                    if overlap_length + prev_length <= overlap_size:
                        overlap_text.insert(0, prev_sent)
                        overlap_length += prev_length
                    else:
                        break

                # Start new chunk with overlap
                current_chunk = overlap_text
                current_length = overlap_length

            # Add current sentence to chunk
            current_chunk.append(sent)
            current_length += sent_length

        # Add final chunk if it exists
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(chunk_text)

        # Create Document objects for each chunk
        for i, chunk_text in enumerate(chunks):
            # Set metadata
            metadata = (
                doc.metadata.copy() if hasattr(doc, "metadata") and doc.metadata else {}
            )
            metadata.update(
                {
                    "url": doc.metadata.get("url", "unknown"),
                    "page_path": doc.metadata.get("page_path", "unknown"),
                    "chunk_name": f"{doc.metadata.get('page_path', 'unknown')}-{i+1}",
                }
            )

            # Create Document with original chunk text
            chunk_doc = Document(page_content=chunk_text, metadata=metadata)
            all_chunks.append(chunk_doc)

    return all_chunks


def clean_text(text: str) -> str:
    """Clean and normalize text, preserving original formatting."""
    # Only do minimal cleaning to preserve formatting
    # Remove multiple newlines and clean up spacing
    cleaned_text = text.replace("\r\n", "\n")
    cleaned_text = "\n".join(line.strip() for line in cleaned_text.split("\n"))
    return cleaned_text
