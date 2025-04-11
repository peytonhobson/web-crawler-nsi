import os
import asyncio
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

    Returns:
        list: Processed content results with duplicates removed.
    """
    if "OPENAI_API_KEY" not in os.environ:
        print("⚠️  OPENAI_API_KEY environment variable is not set.")
        return None

    deep_crawl = BFSDeepCrawlStrategy(max_depth=0, include_external=False)

    basic_config = CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl,
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_external_images=True,
        verbose=False,
        js_code=[get_hidden_elements_removal_js()],
    )

    openai_config = LLMConfig(
        provider="openai/gpt-4o-mini",
        api_token=os.environ.get("OPENAI_API_KEY"),
    )

    content_filter = LLMContentFilter(
        llm_config=openai_config,
        instruction="""
        You are an assistant who is an expert at filtering content extracted 
        from websites. You are given a page from a website.
        Your task is to extract ONLY substantive content that provides real 
        value to customers visiting the website.
        The purpose of the content is to help customers learn about the company 
        and its products by using it as chunks for RAG.
        
        FORMAT REQUIREMENTS:
        - Use clear, hierarchical headers (H1, H2, H3) for each section
        - Add new lines between paragraphs and lists for better readability
        - Create concise, scannable bulleted lists for important details
        - Organize content logically by topic
        - Preserve exact pricing, dates, hours, and contact information
        - Combine related content into cohesive paragraphs
        
        Exclude:
        - ALL navigation links and menu items (e.g., [VENUE], [FAQ], [PRICING], 
        [GALLERY], etc.)
        - ALL social media links and sharing buttons
        - Any other information that is not relevant to the company and its 
        products
        
        Remember: Quality over quantity. Only extract truly useful customer 
        information that directly helps answer questions about visiting, 
        purchasing, or learning about the company and its products.
        """,
        verbose=False,
    )

    md_generator = DefaultMarkdownGenerator(content_filter=content_filter)

    # TODO: Add max depth to config
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=0, include_external=False),
        scraping_strategy=LXMLWebScrapingStrategy(),
        markdown_generator=md_generator,
        # TODO: Add to config
        excluded_tags=["footer", "nav"],
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_external_images=True,
        verbose=False,
        js_code=[get_hidden_elements_removal_js()],
    )

    unique_links = set()
    all_results = []

    async with AsyncWebCrawler() as crawler:
        response = await crawler.arun(
            # TODO: Make starting url in config
            "https://www.westhillsvineyards.com",
            config=basic_config,
        )
        for results in response:
            for r in results:
                internal_links = r.links.get("internal", [])
                for link in internal_links:
                    if len(unique_links) > 1:
                        break
                    unique_links.add(link["href"])

        print(f"Found {len(unique_links)} unique links.")

        # Define a helper function to crawl a single URL
        async def crawl_url(url):
            try:
                results = await crawler.arun(url, config=config)
                print(f"Completed: {url}")
                return results
            except Exception as e:
                print(f"Error crawling {url}: {e}")
                return []

        # Process URLs in batches of 10
        batch_size = 10
        url_list = list(unique_links)
        total_batches = (len(url_list) + batch_size - 1) // batch_size

        print(f"Processing URLs in {total_batches} batches of {batch_size}")

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(url_list))
            batch_urls = url_list[start_idx:end_idx]

            print(
                f"Processing batch {batch_num + 1}/{total_batches} "
                f"with {len(batch_urls)} URLs"
            )

            # Use asyncio.gather to process batch of URLs in parallel
            tasks = [crawl_url(url) for url in batch_urls]
            results_list = await asyncio.gather(*tasks)

            # Flatten results from this batch
            for results in results_list:
                all_results.extend(results)

            print(f"Completed batch {batch_num + 1}/{total_batches}")

    print(f"Crawling complete. Retrieved {len(all_results)} results.")

    valid_pages = [res for res in all_results if res.status_code == 200]

    print("Post-processing results to remove links...")
    processed_pages = process_markdown_results(valid_pages)

    # Filter out empty content
    final_results = []
    for res in processed_pages:
        try:
            # Skip empty content
            if not res.markdown or res.markdown.isspace():
                print(f"Skipping empty content for {res.url}")
                continue

            # Add metadata to the result object
            res.page_path = sanitize_filename(res.url)

            final_results.append(res)

        except Exception as e:
            print(f"❌ Failed to process page {res.url} due to: {e}")
            continue

    print(f"✅ Crawling complete! Processed {len(final_results)} unique pages")

    return final_results  # Return the processed results


def canonicalize_url(url):
    """Normalize a URL to avoid trivial duplicates (e.g., trailing slashes)."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


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
