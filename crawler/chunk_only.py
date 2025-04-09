#!/usr/bin/env python3
"""
Document Chunking Script

This script takes markdown files from the winery_content directory,
chunks them using spaCy, and saves the chunks to winery_content/chunks
without running the crawler again.
"""

import os
import sys
import json
import hashlib
import datetime
import shutil
import glob
from pathlib import Path
import spacy

# Add the parent directory to Python path so we can import from crawler
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crawler.chunk_utils import chunk_documents, sanitize_filename
from langchain_core.documents import Document

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    print(f"Error loading spaCy model: {e}")
    print("Installing spaCy model...")
    import subprocess

    subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")


def get_content_hash(content):
    """Generate a hash of the content for deduplication."""
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def extract_keywords(text, max_keywords=5):
    """Extract keywords from text using spaCy."""
    doc = nlp(text)
    # Get all noun chunks and named entities as potential keywords
    keywords = []
    # Add named entities
    for ent in doc.ents:
        if ent.label_ in [
            "ORG",
            "PERSON",
            "GPE",
            "LOC",
            "PRODUCT",
            "EVENT",
            "WORK_OF_ART",
        ]:
            keywords.append(ent.text.strip().lower())
    # Add noun chunks
    for chunk in doc.noun_chunks:
        keyword = chunk.text.strip().lower()
        if len(keyword) > 3 and keyword not in keywords:  # Avoid very short keywords
            keywords.append(keyword)

    # Remove duplicates and limit to max_keywords
    unique_keywords = []
    for kw in keywords:
        if kw not in unique_keywords and len(unique_keywords) < max_keywords:
            unique_keywords.append(kw)

    return unique_keywords


def generate_vector_id(customer_id, chunk_index):
    """Generate a unique vector ID using customer ID and chunk index."""
    # Get current date in YYYYMMDD format
    today = datetime.datetime.now().strftime("%Y%m%d")
    # Create ID with web_crawl prefix and date for targeted deletion
    return f"web_crawl_{today}_{customer_id}_chunk_{chunk_index}"


def main():
    # Get customer ID from environment or use default
    customer_id = os.environ.get("CUSTOMER_ID", "demo-customer")

    # Set up directories
    base_output_dir = "crawler/winery_content"
    chunks_output_dir = os.path.join(base_output_dir, "chunks")

    # Create chunks directory if it doesn't exist
    if os.path.exists(chunks_output_dir):
        print(f"Removing existing '{chunks_output_dir}' directory...")
        shutil.rmtree(chunks_output_dir)
    print("Creating chunks directory...")
    os.makedirs(chunks_output_dir, exist_ok=True)

    # Get all markdown files in winery_content
    md_files = glob.glob(os.path.join(base_output_dir, "*.md"))
    print(f"Found {len(md_files)} markdown files to process")
    if not md_files:
        print("No markdown files found!")
        return

    # Create Document objects from markdown files
    docs = []
    file_count = 0

    for file_path in md_files:
        file_name = os.path.basename(file_path)
        print(f"Processing {file_name}...")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract title from content (first line with # if exists)
            page_title = "Unknown"
            for line in content.splitlines():
                if line.startswith("# "):
                    page_title = line[2:].strip()
                    break

            # Construct a fake URL from filename
            file_slug = os.path.splitext(file_name)[0]
            url = f"https://www.westhillsvineyards.com/{file_slug}"

            # Create Document object
            doc = Document(
                page_content=content,
                metadata={"url": url, "title": page_title, "source_file": file_path},
            )
            docs.append(doc)
            file_count += 1
            print(f"Added document: {file_path} (Title: {page_title})")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    print(f"\nSuccessfully processed {file_count} files")
    print("\n🔪 Chunking documents...")

    # Chunk the documents (using the function from chunk_utils.py)
    chunks = chunk_documents(docs, chunk_size=500, overlap_ratio=0.2)
    print(f"Created {len(chunks)} chunks from {len(docs)} documents")

    # Save chunks with metadata
    chunk_index = {}
    for i, chunk in enumerate(chunks):
        try:
            metadata = chunk.metadata
            # Use chunk_id as primary identifier
            chunk_id = generate_vector_id(customer_id, i + 1)
            metadata["chunk_id"] = chunk_id
            metadata["customer_id"] = customer_id
            metadata["chunk_index"] = i + 1

            # Extract domain info from URL
            url = metadata.get("url", "")
            domain_parts = url.split("//")[-1].split("/")[0].split(".")
            metadata["source_domain"] = ".".join(
                domain_parts[-2:] if len(domain_parts) > 1 else domain_parts
            )
            metadata["source_path"] = "/" + "/".join(url.split("//")[-1].split("/")[1:])

            # Add keywords if not present
            if "keywords" not in metadata:
                metadata["keywords"] = extract_keywords(chunk.page_content)

            # Add token count if not present
            if "token_count" not in metadata:
                metadata["token_count"] = len(nlp(chunk.page_content))

            # Add timestamps
            metadata["crawl_timestamp"] = datetime.datetime.now().isoformat()
            metadata["chunk_hash"] = hashlib.md5(
                chunk.page_content.encode("utf-8")
            ).hexdigest()

            # Create chunk name from keywords
            keywords = metadata.get("keywords", [])
            chunk_name = (
                f"{i+1}_{'_'.join(keywords[:2])}" if keywords else f"{i+1}_chunk"
            )
            metadata["chunk_name"] = chunk_name
            metadata["total_chunks"] = len(chunks)

            # Create filenames
            filename_part = sanitize_filename(chunk_id)
            base_filename = os.path.join(chunks_output_dir, filename_part)
            filename = f"{base_filename}.md"

            # Save chunk content
            with open(filename, "w", encoding="utf-8") as f:
                f.write(chunk.page_content)

            # Save metadata
            metadata_filename = f"{base_filename}_metadata.json"
            with open(metadata_filename, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            # Add to index
            chunk_index[filename] = {
                "metadata": metadata,
                "token_count": metadata.get("token_count", 0),
                "keywords": metadata.get("keywords", []),
                "source_url": metadata.get("url"),
                "customer_id": metadata.get("customer_id"),
                "chunk_id": metadata.get("chunk_id"),
            }
            print(f"Saved chunk: {filename}")
        except Exception as e:
            print(f"Failed to save chunk {i}: {e}")
            continue

    # Save chunk index
    with open(
        os.path.join(base_output_dir, "chunk_index.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(chunk_index, f, indent=2)

    print("\n✅ Chunking complete!")
    print(f"- Processed {file_count} files")
    print(f"- Created {len(chunks)} chunks")
    print(f"- Chunks are saved in '{chunks_output_dir}'")
    print(
        f"- Chunk index is available at '{os.path.join(base_output_dir, 'chunk_index.json')}'"
    )
    print(
        "\nYou can now run the upload_to_pinecone_v2.py script to upload these chunks to Pinecone."
    )


if __name__ == "__main__":
    main()
