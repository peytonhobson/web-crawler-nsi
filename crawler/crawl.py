import asyncio
import os
import shutil
import json
import spacy
import hashlib
from urllib.parse import urlparse, urlunparse
from dotenv import load_dotenv
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    LXMLWebScrapingStrategy,
    LLMContentFilter,
    LLMConfig,
    DefaultMarkdownGenerator,
)
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from .sanitize_filename import sanitize_filename
from .clean_markdown import process_markdown_results
from langchain.schema import Document
import datetime

# Load environment variables from .env file and spaCy model
load_dotenv()
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
            chunk_id = f"{customer_id}_{sanitize_filename(source_url)}_{i+1}"

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


def canonicalize_url(url):
    """Normalize a URL to avoid trivial duplicates (e.g., trailing slashes)."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def get_content_hash(content):
    """Generate a SHA256 hash for deduplication of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def main():
    if "OPENAI_API_KEY" not in os.environ:
        print("⚠️  OPENAI_API_KEY environment variable is not set.")
        return

    openai_config = LLMConfig(
        provider="openai/gpt-4o-mini",
        api_token=os.environ.get("OPENAI_API_KEY"),
    )

    content_filter = LLMContentFilter(
        llm_config=openai_config,
        instruction="""
        You are an assistant who is an expert at filtering content extracted from winery 
        websites. You are given a page from a winery website.
        Your task is to extract ONLY substantive content that provides real 
        value to customers visiting the winery website. The purpose of the 
        content is to help customers learn about the winery and its products 
        by using it as RAG for a chatbot.
        
        Include:
        - Detailed descriptions of the winery's history, mission, and values
        - Specific information about wine varieties and tasting notes
        - Detailed descriptions of the property, facilities, and amenities
        - Event information including types of events and venue details
        - Tour information including types of tours and what they include
        - Pricing information for wines, tours, and events
        - Contact information and location details
        
        Exclude:
        - ALL navigation links and menu items (e.g., [VENUE], [FAQ], [PRICING], [GALLERY], etc.)
        - ALL social media links and sharing buttons
        - ALL generic call-to-action buttons (e.g., [SHOP NOW], [LEARN MORE], [VISIT US])
        - "CONTACT US", "MENU", "INQUIRIES" and similar standalone call-to-action text
        - Header navigation and top-of-page links
        - Footer navigation and bottom-of-page links
        - Indicators like "top of page" or "bottom of page"
        - Login/signup sections
        - Shopping cart elements
        - Generic welcome messages with no specific information
        - Breadcrumbs and pagination elements
        - Header and footer sections that do not contain substantive information
        - Redundant links that appear in multiple places
        - Marketing taglines without specific information
        - "SUBSCRIBE" or newsletter signup sections
        - Any link that appears to be part of site navigation

        FORMAT REQUIREMENTS:
        - Use clear, hierarchical headers (H1, H2, H3)
        - Create concise, scannable bulleted lists for important details
        - Organize content logically by topic
        - Preserve exact pricing, dates, hours, and contact information
        - Remove all navigation indicators like "»" or ">"
        - Remove standalone links without context
        - Combine related content into cohesive paragraphs
        - Remove any text that appears to be part of the website's navigation
        - Ensure ALL links preserved have real informational value and aren't just navigation
        
        Remember: Quality over quantity. Only extract truly useful customer 
        information that directly helps answer questions about visiting, 
        purchasing, or learning about the winery and its products.
        """,
        verbose=True,
    )

    md_generator = DefaultMarkdownGenerator(content_filter=content_filter)

    base_output_dir = "crawler/winery_content"
    chunks_output_dir = os.path.join(base_output_dir, "chunks")
    if os.path.exists(base_output_dir):
        print(f"Removing existing '{base_output_dir}' directory...")
        shutil.rmtree(base_output_dir)
    print("Creating new output directories...")
    os.makedirs(base_output_dir, exist_ok=True)
    os.makedirs(chunks_output_dir, exist_ok=True)

    deep_crawl = BFSDeepCrawlStrategy(max_depth=3, include_external=False)
    config = CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl,
        scraping_strategy=LXMLWebScrapingStrategy(),
        markdown_generator=md_generator,
        excluded_tags=["footer", "nav"],
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_external_images=True,
        verbose=True,
        js_code=[
            """
            (async () => {
                function isElementHidden(el) {
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') {
                        return true;
                    }
                    if (el.getAttribute('hidden') !== null || el.getAttribute('aria-hidden') === 'true') {
                        return true;
                    }
                    return false;
                }
                if (document.body) {
                    const elements = document.body.querySelectorAll('*');
                    for (let el of elements) {
                        if (isElementHidden(el)) {
                            el.remove();
                        }
                    }
                }
            })();
            """
        ],
    )

    global_content_hashes = set()
    global_canonical_urls = set()

    all_results = []
    starting_urls = [
        "https://www.westhillsvineyards.com/wines",
    ]

    async with AsyncWebCrawler() as crawler:
        for url in starting_urls:
            canonical_url = canonicalize_url(url)
            if canonical_url in global_canonical_urls:
                print(f"Skipping already processed URL: {url}")
                continue
            global_canonical_urls.add(canonical_url)
            print(f"Sequentially crawling URL: {url}")
            results = await crawler.arun(url, config=config)
            all_results.extend(results)

    print(f"Crawling complete. Retrieved {len(all_results)} results.")

    valid_pages = [res for res in all_results if res.status_code == 200]

    print("Post-processing results to remove redundant links...")
    processed_pages = process_markdown_results(valid_pages)

    print("\n📄 Saving original filtered content...")
    saved_count = 0
    docs = []
    for res in processed_pages:
        try:
            if not res.markdown or res.markdown.isspace():
                print(f"Skipping empty content for {res.url}")
                continue

            content_hash = get_content_hash(res.markdown)
            if content_hash in global_content_hashes:
                print(f"Duplicate content detected for {res.url}")
                continue
            global_content_hashes.add(content_hash)

            page_path = sanitize_filename(res.url)
            filename = os.path.join(base_output_dir, f"{page_path}.md")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(res.markdown)

            page_title = "Unknown"
            for line in res.markdown.splitlines():
                if line.startswith("# "):
                    page_title = line[2:].strip()
                    break

            doc = Document(
                page_content=res.markdown,
                metadata={"url": res.url, "title": page_title, "source_file": filename},
            )
            docs.append(doc)
            print(f"Saved: {filename} (URL: {res.url})")
            saved_count += 1
        except Exception as e:
            print(f"❌ Failed to save page {res.url} due to: {e}")
            continue

    print("\n🔪 Chunking documents...")
    chunks = chunk_documents(docs, chunk_size=700, overlap_ratio=0.3)
    print(f"Created {len(chunks)} chunks from {len(docs)} documents")

    print("\n💾 Saving chunks with metadata-based names...")
    chunk_index = {}
    for i, chunk in enumerate(chunks):
        try:
            metadata = chunk.metadata
            # Use chunk_id as the primary identifier for the file
            chunk_id = metadata.get("chunk_id")
            if not chunk_id:
                # Fallback if chunk_id is missing
                url_part = metadata.get("source_url", "unknown").split("/")[-1]
                url_part = sanitize_filename(url_part)[:30]
                chunk_id = f"{metadata.get('customer_id', 'unknown')}_{url_part}_{i+1}"

            # Create a cleaner filename
            filename_part = sanitize_filename(chunk_id)
            base_filename = os.path.join(chunks_output_dir, filename_part)
            filename = f"{base_filename}.md"

            with open(filename, "w", encoding="utf-8") as f:
                f.write(chunk.page_content)
            metadata_filename = f"{base_filename}_metadata.json"
            with open(metadata_filename, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            chunk_index[filename] = {
                "metadata": metadata,
                "token_count": metadata.get("token_count", 0),
                "keywords": metadata.get("keywords", []),
                # Add these fields at the root level for easier access
                "source_url": metadata.get("source_url"),
                "customer_id": metadata.get("customer_id"),
                "chunk_id": metadata.get("chunk_id"),
            }
            print(f"Saved chunk: {filename}")
        except Exception as e:
            print(f"Failed to save chunk {i}: {e}")
            continue

    with open(
        os.path.join(base_output_dir, "chunk_index.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(chunk_index, f, indent=2)

    print("\n✅ Process complete!")
    print(f"- Crawled and processed {saved_count} pages")
    print(f"- Created {len(chunks)} chunks")
    print(f"- Files are in '{base_output_dir}' directory")
    print(f"- Chunks are in '{chunks_output_dir}' directory")
    print(
        f"- Chunk index is available at '{os.path.join(base_output_dir, 'chunk_index.json')}'"
    )


if __name__ == "__main__":
    asyncio.run(main())
