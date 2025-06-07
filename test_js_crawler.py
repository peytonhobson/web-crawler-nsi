#!/usr/bin/env python3
"""
Test script to run the crawler with JavaScript enabled.
This helps debug why the crawler is finding 0 internal links.
"""

import asyncio
import os
from crawler.config import CrawlerConfig
from crawler.crawl import crawl


async def main():
    # Set environment variables to enable JavaScript
    os.environ["TEXT_MODE"] = "false"
    os.environ["HEADLESS"] = "false"  # Run in visible mode for debugging
    os.environ["LIGHT_MODE"] = "false"
    os.environ["MAX_DEPTH"] = "1"  # Start with depth 1 for testing
    os.environ["VERBOSE"] = "true"

    # Load configuration
    config = CrawlerConfig.from_env()

    print("Configuration:")
    print(f"  Browser type: {config.browser_type}")
    print(f"  Headless: {config.headless}")
    print(f"  Light mode: {config.light_mode}")
    print(f"  Text mode: {config.text_mode}")
    print(f"  Max depth: {config.max_depth}")
    print(f"  Start URLs: {config.start_urls}")
    print()

    # Run the crawler
    results = await crawl(config)

    print(f"Crawling completed. Found {len(results)} results.")
    for i, result in enumerate(results[:3]):  # Show first 3 results
        print(f"Result {i+1}: {len(result)} characters")


if __name__ == "__main__":
    asyncio.run(main())
