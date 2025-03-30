import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

async def main():
    # Check the available parameters for CrawlerRunConfig
    # Common parameters are typically:
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=2, include_external=False),
        scraping_strategy=LXMLWebScrapingStrategy(),
        # Remove request_timeout as it's not recognized
        verbose=True
    )

    async with AsyncWebCrawler() as crawler:
        try:
            # You might be able to set timeout here instead
            results = await crawler.arun("https://www.westhillsvineyards.com", config=config)
        except Exception as e:
            print(f"❌ Crawling failed due to exception: {e}")
            return  # exit the function gracefully on failure

        valid_pages = [result for result in results if result.status_code == 200]

        for i, result in enumerate(valid_pages):
            try:
                filename = f'page_{i+1}.md'
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(result.markdown)
                print(f'Saved: {filename} (URL: {result.url})')
            except Exception as e:
                print(f"❌ Failed to save page {result.url} due to: {e}")
                continue  # safely continue processing other results

        print(f"\n✅ Crawled and saved {len(valid_pages)} valid pages successfully!")

if __name__ == "__main__":
    asyncio.run(main())
