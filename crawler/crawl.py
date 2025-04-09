import asyncio
import os
import shutil
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
import subprocess
import sys

# Add the parent directory to Python path so we can import from crawler
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crawler.sanitize_filename import sanitize_filename
from crawler.clean_markdown import process_markdown_results

# Load environment variables from .env file
load_dotenv()


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
        return None

    openai_config = LLMConfig(
        provider="openai/gpt-4o-mini",
        api_token=os.environ.get("OPENAI_API_KEY"),
    )

    content_filter = LLMContentFilter(
        llm_config=openai_config,
        instruction="""
        You are an assistant who is an expert at filtering content extracted 
        from winery websites. You are given a page from a winery website.
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
        - ALL navigation links and menu items (e.g., [VENUE], [FAQ], [PRICING], 
        [GALLERY], etc.)
        - ALL social media links and sharing buttons
        - ALL generic call-to-action buttons (e.g., [SHOP NOW], [LEARN MORE], 
        [VISIT US])
        - "CONTACT US", "MENU", "INQUIRIES" and similar standalone 
        call-to-action text
        - Header navigation and top-of-page links
        - Footer navigation and bottom-of-page links
        - Indicators like "top of page" or "bottom of page"
        - Login/signup sections
        - Shopping cart elements
        - Generic welcome messages with no specific information
        - Breadcrumbs and pagination elements
        - Header and footer sections that do not contain substantive 
        information
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
    if os.path.exists(base_output_dir):
        print(f"Removing existing '{base_output_dir}' directory...")
        shutil.rmtree(base_output_dir)
    print("Creating new output directory...")
    os.makedirs(base_output_dir, exist_ok=True)

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
                    if (style.display === 'none' || 
                        style.visibility === 'hidden') {
                        return true;
                    }
                    if (el.getAttribute('hidden') !== null || 
                        el.getAttribute('aria-hidden') === 'true') {
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
            try:
                canonical_url = canonicalize_url(url)
                if canonical_url in global_canonical_urls:
                    print(f"Skipping already processed URL: {url}")
                    continue
                global_canonical_urls.add(canonical_url)
                print(f"Sequentially crawling URL: {url}")
                results = await crawler.arun(url, config=config)
                all_results.extend(results)
            except Exception as e:
                print(f"Error crawling {url}: {e}")
                continue

    print(f"Crawling complete. Retrieved {len(all_results)} results.")

    valid_pages = [res for res in all_results if res.status_code == 200]

    print("Post-processing results to remove redundant links...")
    processed_pages = process_markdown_results(valid_pages)

    print("\n📄 Saving original filtered content...")
    saved_count = 0
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
            print(f"Saved: {filename} (URL: {res.url})")
            saved_count += 1
        except Exception as e:
            print(f"❌ Failed to save page {res.url} due to: {e}")
            continue

    print("\n✅ Crawling complete!")
    print(f"- Crawled and processed {saved_count} pages")
    print(f"- Files are in '{base_output_dir}' directory")

    # Call chunk_only.py to handle chunking
    print("\n🔪 Starting chunking process...")
    chunk_script = os.path.join(os.path.dirname(__file__), "chunk_only.py")
    subprocess.run([sys.executable, chunk_script])

    return base_output_dir  # Return the output directory


if __name__ == "__main__":
    asyncio.run(main())
