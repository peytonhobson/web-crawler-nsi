import asyncio
import os
from urllib.parse import urlparse, urlunparse
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    LLMContentFilter,
    LLMConfig,
    DefaultMarkdownGenerator,
)
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawler.sanitize_filename import sanitize_filename
from crawler.clean_markdown import process_markdown_results
from crawler.config import CrawlerConfig


async def crawl(config: CrawlerConfig = None):
    """
    Crawl websites based on provided configuration, process content,
    and return processed results.

    Args:
        config (CrawlerConfig, optional): Configuration object. If None,
                                         load from environment.

    Returns:
        list: Processed content results with duplicates removed.
    """
    deep_crawl = BFSDeepCrawlStrategy(
        max_depth=config.max_depth, include_external=config.include_external
    )

    crawler_link_config = CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl,
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_external_images=True,
        verbose=config.verbose,
        delay_before_return_html=1,
        scan_full_page=True,
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
        markdown_generator=md_generator,
        excluded_tags=config.excluded_tags,
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_external_images=True,
        verbose=config.verbose,
        delay_before_return_html=1,
        scan_full_page=True,
        js_code=[
            get_hidden_elements_removal_js(),
            get_universal_structure_fix_js(),
        ],
    )

    # Crawler config for repeated elements to crawl once
    crawler_config_repeated_elements = CrawlerRunConfig(
        target_elements=config.excluded_tags,
        markdown_generator=md_generator,
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_external_images=True,
        verbose=config.verbose,
        delay_before_return_html=1,
        scan_full_page=True,
        js_code=[
            get_hidden_elements_removal_js(),
            get_universal_structure_fix_js(),
        ],
    )

    unique_links = set()
    all_results = []

    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        light_mode=True,
        text_mode=True,
        ignore_https_errors=True,
    )

    start_urls = config.start_urls

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
                        normalized_link = normalize_url(link["href"])
                        if not is_image_url(normalized_link):
                            unique_links.add(normalized_link)

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

            all_results.extend(results_list)

            print(f"Completed batch {batch_num + 1}/{total_batches}")

        for start_url in start_urls:
            results = await crawler.arun(
                start_url, config=crawler_config_repeated_elements
            )
            results.url = "repeated_elements"
            all_results.append(results)

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


def get_universal_structure_fix_js():
    """Return JavaScript that detects and fixes inverted content structures across various site builders.

    This script runs in the browser context to identify and reorder elements where content appears before its logical heading - a common issue in sites built with visual builders
    like Wix, Squarespace, etc.
    """
    return """
    (async () => {
        const baseTextSize = document.documentElement.style.fontSize;
        const baseTextSizePx = parseFloat(baseTextSize);
        
        function isLikelyHeading(el) {
            if (!el) return false;
            const text = el.textContent.trim();
            if (!text || text.length > 120) return false;

            if (el.querySelector('h1,h2,h3,h4,h5,h6')) return true;

            const style = window.getComputedStyle(el);
            const fontSize = parseFloat(style.fontSize);
            const fontWeight = parseInt(style.fontWeight);

            return (fontSize >= baseTextSizePx * 1.2 || fontWeight >= 600);
        }

        function isLikelyContent(el) {
            if (!el) return false;
            const text = el.textContent.trim();
            if (text.length > 150) return true;
            if (el.querySelectorAll('p, ul, ol, li').length >= 3) return true;

            return false;
        }

        // Go through all containers
        document.querySelectorAll('div, section, article').forEach(container => {
            const children = Array.from(container.children);
            for (let i = 0; i < children.length - 1; i++) {
                const current = children[i];
                const next = children[i + 1];

                if (
                    isLikelyContent(current) &&
                    isLikelyHeading(next) &&
                    !(i > 0 && isLikelyHeading(children[i - 1]))
                ) {
                    try {
                        container.insertBefore(next, current);
                    } catch (e) {
                        // fallback in case insertBefore fails
                        const temp = next.cloneNode(true);
                        container.insertBefore(temp, current);
                        next.remove();
                    }
                }
            }
        });
    })();
    """


def normalize_url(url):
    """
    Normalize a URL by removing query parameters and fragments.

    Args:
        url (str): The URL to normalize

    Returns:
        str: Normalized URL with only scheme, netloc, and path
    """
    parsed = urlparse(url)
    # Keep only scheme, netloc, and path components
    normalized = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/") or "/",  # Keep slash only for root
            "",  # Remove params
            "",  # Remove query
            "",  # Remove fragment
        )
    )
    return normalized


def is_image_url(url):
    """Check if a URL points to an image file.

    Args:
        url (str): The URL to check

    Returns:
        bool: True if the URL is an image, False otherwise
    """
    # List of common image file extensions
    image_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        ".bmp",
        ".tiff",
        ".ico",
    ]

    # Parse the URL and extract the path
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()

    # Check if the path ends with any of the image extensions
    return any(path.endswith(ext) for ext in image_extensions)
