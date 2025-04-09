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
    """Clean and normalize text using spaCy."""
    doc = nlp(text)
    return " ".join(token.text for token in doc)


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
    """Split Document's page_content into fixed-size token chunks with overlap."""
    all_chunks = []
    for doc in docs:
        cleaned_content = clean_text(doc.page_content)
        spacy_doc = nlp(cleaned_content)
        sentences = [sent.text.strip() for sent in spacy_doc.sents if sent.text.strip()]

        chunks = []
        chunk_texts = []
        current_chunk = []
        current_chunk_text = []
        current_tokens = 0
        overlap_size = int(chunk_size * overlap_ratio)

        for sent in sentences:
            sent_doc = nlp(sent)
            sent_tokens = [token.text for token in sent_doc]
            sent_len = len(sent_tokens)

            if current_tokens + sent_len > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                chunk_texts.append(" ".join(current_chunk_text))
                current_chunk = (
                    current_chunk[-overlap_size:]
                    if overlap_size < len(current_chunk)
                    else current_chunk
                )
                current_chunk_text = (
                    current_chunk_text[-overlap_size:]
                    if overlap_size < len(current_chunk_text)
                    else current_chunk_text
                )
                current_tokens = len(current_chunk)

            current_chunk.extend(sent_tokens)
            current_chunk_text.append(sent)
            current_tokens += sent_len

        if current_chunk:
            chunks.append(" ".join(current_chunk))
            chunk_texts.append(" ".join(current_chunk_text))

        # Extract source info from the URL for better targeting
        source_url = doc.metadata.get("url", "unknown")
        source_domain = urlparse(source_url).netloc
        source_path = urlparse(source_url).path

        # Get customer ID from environment or default to domain name
        customer_id = os.environ.get("CUSTOMER_ID", source_domain.replace(".", "_"))

        for i, (chunk, chunk_text) in enumerate(zip(chunks, chunk_texts)):
            keywords = extract_keywords(chunk_text)
            chunk_name = (
                f"{i+1}_{'_'.join(keywords[:2])}" if keywords else f"{i+1}_chunk"
            )

            # Create a unique chunk ID that's consistent for targeting
            chunk_id = generate_vector_id(customer_id, i + 1)

            metadata = (
                doc.metadata.copy() if hasattr(doc, "metadata") and doc.metadata else {}
            )
            metadata.update(
                {
                    # Core identifiers for targeting in database
                    "chunk_id": chunk_id,
                    "customer_id": customer_id,
                    "source_url": source_url,
                    "source_domain": source_domain,
                    "source_path": source_path,
                    # Chunk information
                    "chunk_index": i + 1,
                    "chunk_name": chunk_name,
                    "total_chunks": len(chunks),
                    # Content metadata
                    "keywords": keywords,
                    "token_count": len(nlp(chunk)),
                    "page_title": metadata.get("title", "unknown"),
                    # For tracking origin
                    "crawl_timestamp": datetime.datetime.now().isoformat(),
                    "chunk_hash": hashlib.md5(chunk.encode("utf-8")).hexdigest(),
                }
            )
            chunk_doc = Document(page_content=chunk, metadata=metadata)
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
