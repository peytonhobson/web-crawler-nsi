import spacy
from langchain_core.documents import Document
import datetime
import hashlib
from urllib.parse import urlparse
import os
import sys

# Add the parent directory to Python path so we can import from crawler
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crawler.sanitize_filename import sanitize_filename

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    print(f"Error loading spaCy model: {e}")
    print("Installing spaCy model...")
    import subprocess

    subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")


def clean_text(text: str) -> str:
    """Clean and normalize text, preserving original formatting."""
    # Only do minimal cleaning to preserve formatting
    # Remove multiple newlines and clean up spacing
    cleaned_text = text.replace("\r\n", "\n")
    cleaned_text = "\n".join(line.strip() for line in cleaned_text.split("\n"))
    return cleaned_text


def extract_keywords(text, num_keywords=5):
    """Extract key phrases for chunk naming, avoiding Markdown syntax."""
    cleaned_text = text
    for char in ["#", "*", "_", "`", "[", "]", "(", ")", ">", "\n", "$"]:
        cleaned_text = cleaned_text.replace(char, " ")

    doc = nlp(cleaned_text)
    keywords = [
        chunk.text.lower()
        for chunk in doc.noun_chunks
        if not any(
            c in chunk.text for c in ["[", "]", "(", ")", "#", "*", "`", "\n", "$"]
        )
        and len(chunk.text) > 3
    ]
    keywords.extend(
        [
            ent.text.lower()
            for ent in doc.ents
            if not any(
                c in ent.text for c in ["[", "]", "(", ")", "#", "*", "`", "\n", "$"]
            )
            and len(ent.text) > 3
        ]
    )

    keyword_freq = {}
    for keyword in keywords:
        if len(keyword.split()) > 1:
            keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1

    top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[
        :num_keywords
    ]
    return (
        [sanitize_filename(k) for k, _ in top_keywords]
        if top_keywords
        else ["general_content"]
    )


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
                chunk_text = "".join(current_chunk)
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
            chunk_text = "".join(current_chunk)
            chunks.append(chunk_text)

        # Extract metadata
        source_url = doc.metadata.get("url", "unknown")
        source_domain = urlparse(source_url).netloc
        source_path = urlparse(source_url).path

        # Get customer ID
        customer_id = os.environ.get("CUSTOMER_ID", source_domain.replace(".", "_"))

        # Create Document objects for each chunk
        for i, chunk_text in enumerate(chunks):
            # Extract basic keywords for naming (without fancy filtering)
            keywords = extract_keywords(chunk_text)
            chunk_name = (
                f"{i+1}_{'_'.join(keywords[:2])}" if keywords else f"{i+1}_chunk"
            )

            # Create chunk ID
            chunk_id = generate_vector_id(customer_id, i + 1)

            # Set metadata
            metadata = (
                doc.metadata.copy() if hasattr(doc, "metadata") and doc.metadata else {}
            )
            metadata.update(
                {
                    "chunk_id": chunk_id,
                    "customer_id": customer_id,
                    "source_url": source_url,
                    "source_domain": source_domain,
                    "source_path": source_path,
                    "chunk_index": i + 1,
                    "chunk_name": chunk_name,
                    "total_chunks": len(chunks),
                    "keywords": keywords,
                    "token_count": len(nlp(chunk_text)),
                    "page_title": metadata.get("title", "unknown"),
                    "crawl_timestamp": datetime.datetime.now().isoformat(),
                    "chunk_hash": hashlib.md5(chunk_text.encode("utf-8")).hexdigest(),
                }
            )

            # Create Document with original chunk text
            chunk_doc = Document(page_content=chunk_text, metadata=metadata)
            all_chunks.append(chunk_doc)

    return all_chunks


def generate_vector_id(customer_id, chunk_index):
    """
    Generate a unique vector ID using a customer ID and chunk index.
    The ID format enables targeted deletion of web crawl data by date.

    :param customer_id: The customer identifier (e.g., winery name)
    :param chunk_index: The index of the chunk within the document
    :return: A unique vector ID with clear web crawl identifier and date
    """
    # Get current date in YYYYMMDD format for daily identification
    today = datetime.datetime.now().strftime("%Y%m%d")

    # Create ID with explicit web_crawl prefix and date for targeted deletion
    return f"web_crawl_{today}_{customer_id}_chunk_{chunk_index}"


# Original spaCy tokenization version - preserving for reference but not using
def tokenize_text(text: str) -> str:
    """Tokenize text using spaCy (creates spacing issues - not used)."""
    doc = nlp(text)
    return " ".join(token.text for token in doc)
