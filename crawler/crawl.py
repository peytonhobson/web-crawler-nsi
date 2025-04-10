import os
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
from crawler.sanitize_filename import sanitize_filename
from crawler.clean_markdown import process_markdown_results

# Load environment variables from .env file
load_dotenv()


async def crawl():
    """
    Crawl winery websites, process content, and return processed results.

    Args:
        run_chunking (bool): Whether to run the chunking process after crawling.

    Returns:
        list: Processed content results with duplicates removed.
    """
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
        value to customers visiting the winery website.
        The purpose of the content is to help customers learn about the winery 
        and its products by using it as RAG for a chatbot.
        
        FORMAT REQUIREMENTS:
        - Use clear, hierarchical headers (H1, H2, H3) for each section
        - Create concise, scannable bulleted lists for important details
        - Organize content logically by topic
        - Preserve exact pricing, dates, hours, and contact information
        - Remove all navigation indicators like "»" or ">"
        - Remove standalone links without context
        - Combine related content into cohesive paragraphs
        - Remove any text that appears to be part of the website's navigation
        - Ensure ALL links preserved have real informational value and aren't 
          just navigation
        
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
        
        Remember: Quality over quantity. Only extract truly useful customer 
        information that directly helps answer questions about visiting, 
        purchasing, or learning about the winery and its products.
        """,
        verbose=True,
    )

    md_generator = DefaultMarkdownGenerator(content_filter=content_filter)

    deep_crawl = BFSDeepCrawlStrategy(max_depth=3, include_external=False)
    config = CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl,
        scraping_strategy=LXMLWebScrapingStrategy(),
        markdown_generator=md_generator,
        # TODO: Add to config
        excluded_tags=["footer", "nav"],
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_external_images=True,
        verbose=True,
        js_code=[get_hidden_elements_removal_js()],
    )

    global_content_hashes = set()
    global_canonical_urls = set()

    all_results = []
    # TODO: Add to config
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

                # Get the filename from the URL to provide context
                page_path = sanitize_filename(url)

                # Add page context to the content filter
                context_str = f"Processing content for page: {page_path}\n"
                content_filter.context = context_str

                results = await crawler.arun(url, config=config)
                all_results.extend(results)
            except Exception as e:
                print(f"Error crawling {url}: {e}")
                continue

    print(f"Crawling complete. Retrieved {len(all_results)} results.")

    valid_pages = [res for res in all_results if res.status_code == 200]

    print("Post-processing results to remove links...")
    processed_pages = process_markdown_results(valid_pages)

    # Filter out empty or duplicate content
    final_results = []
    for res in processed_pages:
        try:
            # Skip empty content
            if not res.markdown or res.markdown.isspace():
                print(f"Skipping empty content for {res.url}")
                continue

            content_hash = get_content_hash(res.markdown)
            if content_hash in global_content_hashes:
                print(f"Duplicate content detected for {res.url}")
                continue

            global_content_hashes.add(content_hash)

            # Add metadata to the result object
            res.page_path = sanitize_filename(res.url)
            res.content_hash = content_hash

            final_results.append(res)

        except Exception as e:
            print(f"❌ Failed to process page {res.url} due to: {e}")
            continue

    print(f"\n✅ Crawling complete! Processed {len(final_results)} unique pages")

    return final_results  # Return the processed results


def canonicalize_url(url):
    """Normalize a URL to avoid trivial duplicates (e.g., trailing slashes)."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def get_content_hash(content):
    """Generate a SHA256 hash for deduplication of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_hidden_elements_removal_js():
    """Return JavaScript code that removes hidden elements from the DOM.

    This script runs in the browser context and removes elements that are
    hidden via CSS or HTML attributes to clean up the page before scraping.
    """
    return """
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
