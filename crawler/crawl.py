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
    BrowserConfig,
)
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawler.sanitize_filename import sanitize_filename
from crawler.clean_markdown import process_markdown_results
from crawler.config import CrawlerConfig

# Load environment variables from .env file
load_dotenv()


async def crawl(config: CrawlerConfig = None):
    """
    Crawl websites based on provided configuration, process content, and return processed results.

    Args:
        config (CrawlerConfig, optional): Configuration object. If None, load from environment.

    Returns:
        list: Processed content results with duplicates removed.
    """
    if "OPENAI_API_KEY" not in os.environ:
        print("⚠️  OPENAI_API_KEY environment variable is not set.")
        return None

    # Set up a fixed browser configuration that works well in containerized environments
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=False,
        light_mode=True,
        text_mode=True,
        ignore_https_errors=True,
        viewport_width=1280,
        viewport_height=720,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )

    deep_crawl = BFSDeepCrawlStrategy(
        max_depth=config.max_depth, include_external=config.include_external
    )

    crawler_link_config = CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl,
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_external_images=True,
        verbose=config.verbose,
        js_code=[get_hidden_elements_removal_js()],
    )

    openai_config = LLMConfig(
        provider=config.llm_provider,
        api_token=os.environ.get("OPENAI_API_KEY"),
    )

    content_filter = LLMContentFilter(
        llm_config=openai_config,
        instruction=config.llm_instruction,
        verbose=config.verbose,
    )

    md_generator = DefaultMarkdownGenerator(content_filter=content_filter)

    crawler_config = CrawlerRunConfig(
        # Use unique links to crawl at a depth of 0
        # TODO: Convert to non-deep crawl strategy for better performance
        deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=0, include_external=False),
        scraping_strategy=LXMLWebScrapingStrategy(),
        markdown_generator=md_generator,
        excluded_tags=config.excluded_tags,
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_external_images=True,
        verbose=config.verbose,
        js_code=[get_hidden_elements_removal_js()],
    )

    unique_links = set()
    all_results = []

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # If no specific start URLs are provided, use a default
        if not config.start_urls:
            raise ValueError("No start URLs provided in configuration")
        else:
            start_urls = config.start_urls

        # First, crawl to collect all links
        for start_url in start_urls:
            print(f"Starting crawl from: {start_url}")
            response = await crawler.arun(
                start_url,
                config=crawler_link_config,
            )
            for results in response:
                for r in results:
                    internal_links = r.links.get("internal", [])
                    for link in internal_links:
                        unique_links.add(link["href"])

        print(f"Found {len(unique_links)} unique links.")

        # Define a helper function to crawl a single URL
        async def crawl_url(url):
            try:
                results = await crawler.arun(url, config=crawler_config)
                print(f"Completed: {url}")
                return results
            except Exception as e:
                print(f"Error crawling {url}: {e}")
                return []

        # Process URLs in batches
        batch_size = config.batch_size
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
