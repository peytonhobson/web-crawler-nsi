import os
import asyncio
from urllib.parse import urlparse, urlunparse
from dotenv import load_dotenv
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
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

    deep_crawl = BFSDeepCrawlStrategy(
        max_depth=config.max_depth, include_external=config.include_external
    )

    crawler_link_config = CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl,
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_external_images=True,
        verbose=config.verbose,
        js_code=[
            get_hidden_elements_removal_js(),
            get_universal_structure_fix_js(),
            get_revolution_slider_extraction_js(),
            get_stats_extraction_js(),
        ],
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
        # Remove LXMLWebScrapingStrategy to use fully rendered DOM
        markdown_generator=md_generator,
        excluded_tags=config.excluded_tags,
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_external_images=True,
        verbose=config.verbose,
        js_code=[
            get_hidden_elements_removal_js(),
            get_universal_structure_fix_js(),
            get_revolution_slider_extraction_js(),
            get_stats_extraction_js(),
        ],
    )

    unique_links = set()
    all_results = []

    # Set up a fixed browser configuration that works well in containerized environments
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        light_mode=True,
        text_mode=True,
        ignore_https_errors=True,
        viewport_width=1280,
        viewport_height=720,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )

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


def get_universal_structure_fix_js():
    """Return JavaScript that detects and fixes inverted content structures across various site builders.

    This script runs in the browser context to identify and reorder elements where content
    appears before its logical heading - a common issue in sites built with visual builders
    like Wix, Squarespace, etc.
    """
    return """
    (async () => {
        function isLikelyHeading(el) {
            if (!el) return false;
            const text = el.textContent.trim();
            if (!text || text.length > 120) return false;

            if (el.querySelector('h1,h2,h3,h4,h5,h6')) return true;

            const style = window.getComputedStyle(el);
            const fontSize = parseFloat(style.fontSize);
            const fontWeight = parseInt(style.fontWeight);

            return (fontSize >= 17 || fontWeight >= 600);
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


def get_revolution_slider_extraction_js():
    """Return JavaScript that extracts content from Revolution Slider <rs-layer> tags and formats it properly.

    This script runs in the browser context to extract text from Revolution Slider layers,
    wrap them in appropriate HTML tags, and append them to the DOM for proper content extraction.
    """
    return """
    (async () => {
        // Wait for minimum content to load
        async function waitForContent() {
            const maxAttempts = 10;
            const minLayers = 5;  // Minimum number of rs-layers to consider content loaded
            
            for (let i = 0; i < maxAttempts; i++) {
                const layers = document.querySelectorAll('rs-layer');
                if (layers.length >= minLayers) {
                    return true;
                }
                await new Promise(r => setTimeout(r, 1000));  // Check every second
            }
            return false;
        }
        
        // Wait for content to load
        const contentLoaded = await waitForContent();
        if (!contentLoaded) {
            console.warn('Revolution Slider content did not load within timeout');
        }
        
        // Create a container for extracted content
        const contentContainer = document.createElement('div');
        contentContainer.id = 'extracted-slider-content';
        contentContainer.style.position = 'absolute';
        contentContainer.style.left = '0';
        contentContainer.style.top = '0';
        contentContainer.style.zIndex = '9999';
        contentContainer.style.backgroundColor = 'white';
        contentContainer.style.padding = '20px';
        contentContainer.style.margin = '20px';
        contentContainer.style.border = '1px solid #ccc';
        
        // Extract and format content from all rs-layers
        document.querySelectorAll('rs-layer').forEach(layer => {
            const text = layer.innerText.trim();
            if (text) {
                // Create a paragraph for the content
                const p = document.createElement('p');
                p.textContent = text;
                
                // Copy relevant styles for semantic understanding
                const style = window.getComputedStyle(layer);
                if (parseFloat(style.fontSize) >= 24 || parseInt(style.fontWeight) >= 600) {
                    // Likely a heading
                    const h = document.createElement('h2');
                    h.textContent = text;
                    contentContainer.appendChild(h);
                } else {
                    // Regular content
                    contentContainer.appendChild(p);
                }
            }
        });
        
        // Append the formatted content to the body
        if (contentContainer.children.length > 0) {
            document.body.appendChild(contentContainer);
            
            // Ensure the content is visible to the DOM extractor
            contentContainer.scrollIntoView();
        }
    })();
    """


def get_stats_extraction_js():
    """Return JavaScript that extracts and formats statistics from the page.

    This script runs in the browser context to find statistics (numbers with labels),
    group them together, and format them for proper content extraction.
    """
    return """
    (async () => {
        function waitForNonZeroStats(maxRetries = 10, delay = 1000) {
            return new Promise((resolve) => {
                let attempt = 0;
                const check = () => {
                    const elements = Array.from(document.querySelectorAll('*'));
                    const hasNonZeroValues = elements.some(el => {
                        const dataValue = el.getAttribute("data-counter-value");
                        return dataValue && !isNaN(dataValue) && parseInt(dataValue) > 0;
                    });
                    
                    if (hasNonZeroValues || attempt >= maxRetries) {
                        resolve();
                    } else {
                        attempt++;
                        setTimeout(check, delay);
                    }
                };
                check();
            });
        }

        await waitForNonZeroStats();

        const container = document.createElement('div');
        container.id = 'extracted-stats-content';
        container.style.display = 'block';

        // Find all elements with data-counter-value
        const statElements = Array.from(document.querySelectorAll('[data-counter-value]'));
        
        statElements.forEach(el => {
            const value = el.getAttribute("data-counter-value");
            if (value && !isNaN(value)) {
                // Find the associated label (usually in a nearby element)
                const labelEl = el.closest('.stat-item, .counter, .summary-item, .vc_column-inner, .stats-box');
                if (labelEl) {
                    // Get all text content from the container, excluding the number itself
                    const containerText = labelEl.innerText.trim();
                    const numberText = el.innerText.trim();
                    const labelText = containerText.replace(numberText, '').trim();
                    
                    if (labelText) {
                        const p = document.createElement('p');
                        p.textContent = `${labelText} - ${value}`;
                        container.appendChild(p);
                    }
                }
            }
        });

        if (container.children.length > 0) {
            document.body.appendChild(container);
            container.scrollIntoView();
        }
    })();
    """
