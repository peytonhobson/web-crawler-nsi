import asyncio
import os
import shutil  # Import shutil for directory operations
from dotenv import load_dotenv
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    DefaultMarkdownGenerator,
    LLMConfig,
    LLMContentFilter,
)
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from sanitize_filename import sanitize_filename
from clean_markdown import process_markdown_results

# Load environment variables from .env file
load_dotenv()


async def main():
    # Check if API key is set in environment
    if "OPENAI_API_KEY" not in os.environ:
        print("⚠️ Warning: OPENAI_API_KEY environment variable is not set.")
        print("Please set your OpenAI API key using:")
        print("    export OPENAI_API_KEY='your-api-key'")
        return

    # Configuration for OpenAI model
    openai_config = LLMConfig(
        # TODO: Experiment with other models
        provider="openai/gpt-4o-mini",
        api_token=os.environ.get("OPENAI_API_KEY"),
    )

    # Content filter with improved instructions
    content_filter = LLMContentFilter(
        llm_config=openai_config,
        instruction="""
        You are an assistant who is an expert at extracting content from winery 
        websites. You are given a page from a winery website.
        Your task is to extract ONLY substantive content that provides real 
        value to customers visiting the winery website. The purpose of the 
        content is to help customers learn about the winery and its products 
        by using it as RAG for a chatbot.
        
        Include:
        - Any details relevant to a customer visiting the winery website.
        - This could include product details, events, details about the winery.
        
        Exclude
        - Repeated links such as those in headers and nav sections.
        - "Skip to content" links or accessibility controls
        - Social media links and sharing buttons
        - Login/signup sections
        - Shopping cart elements
        - Generic welcome messages with no specific information
        - Breadcrumbs and pagination elements

        FORMAT REQUIREMENTS:
        - Use clear, hierarchical headers (H1, H2, H3)
        - Create concise, scannable bulleted lists for important details
        - Organize content logically by topic
        - Preserve exact pricing, dates, hours, and contact information
        - Remove all navigation indicators like "»" or ">"
        
        Remember: Quality over quantity. Only extract truly useful customer 
        information that directly helps answer questions about visiting, 
        purchasing, or learning about the winery and its products.
        """,
        verbose=True,
    )

    md_generator = DefaultMarkdownGenerator(content_filter=content_filter)

    # Create a directory for the markdown files if it doesn't exist
    output_dir = "winery_content"

    # Delete the output directory if it exists
    if os.path.exists(output_dir):
        print(f"Removing existing '{output_dir}' directory...")
        shutil.rmtree(output_dir)

    # Create a fresh directory
    print(f"Creating new '{output_dir}' directory...")
    os.makedirs(output_dir, exist_ok=True)

    # Crawler configuration
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=2, include_external=False),
        scraping_strategy=LXMLWebScrapingStrategy(),
        markdown_generator=md_generator,
        excluded_tags=["footer", "nav"],
        # Link filtering
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_external_images=True,
        verbose=True,
    )

    async with AsyncWebCrawler() as crawler:
        try:
            # Run the crawler
            results = await crawler.arun(
                "https://www.westhillsvineyards.com", config=config
            )
        except Exception as e:
            print(f"❌ Crawling failed due to exception: {e}")
            return  # exit gracefully on failure

        # Filter for valid pages
        valid_pages = [result for result in results if result.status_code == 200]

        # Post-process to remove redundant links
        print("Post-processing results to remove redundant links...")
        processed_pages = process_markdown_results(valid_pages)

        saved_count = 0
        for result in processed_pages:
            try:
                # Generate filename based on URL path
                page_path = sanitize_filename(result.url)
                filename = f"{output_dir}/{page_path}.md"

                with open(filename, "w", encoding="utf-8") as f:
                    f.write(result.markdown)
                print(f"Saved: {filename} (URL: {result.url})")
                saved_count += 1
            except Exception as e:
                print(f"❌ Failed to save page {result.url} due to: {e}")
                continue

        print(f"\n✅ Crawled, processed, and saved {saved_count} pages successfully!")
        print(f"Files are saved in the '{output_dir}' directory.")


if __name__ == "__main__":
    # To run this script:
    # 1. Make sure you have set the OPENAI_API_KEY environment variable:
    #    export OPENAI_API_KEY='your-api-key'
    # 2. Install required packages:
    #    pip install crawl4ai python-dotenv
    asyncio.run(main())
