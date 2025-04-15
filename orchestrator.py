import sys
import logging
import asyncio
import argparse
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from crawler.crawl import crawl
from chunk_content import chunk_content
from summary import summarize_content
from vectordb.pinecone import upload_chunks
from crawler.config import CrawlerConfig

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            f'logs/orchestrator_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def format_time(seconds):
    """Format seconds into a human-readable time string."""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours > 0:
        return f"{int(hours)}h {int(minutes)}m {seconds:.2f}s"
    elif minutes > 0:
        return f"{int(minutes)}m {seconds:.2f}s"
    else:
        return f"{seconds:.2f}s"


async def main(dry_run=False):
    """Main orchestrator function that runs crawler, chunking, summarization,
    and Pinecone upload in sequence."""
    try:
        # Start timing the entire process
        total_start_time = time.time()

        # Load environment variables
        load_dotenv()

        # Create configuration from environment variables
        config = CrawlerConfig.from_environment()

        # Override dry_run from command line if specified
        if dry_run:
            config.dry_run = True

        logger.info("Starting orchestration process...")
        logger.info(f"Using configuration with {len(config.start_urls)} start URLs")

        # Run crawler with configuration
        logger.info("Starting crawler...")
        crawl_start_time = time.time()
        crawling_results = await crawl(config)
        crawl_time = time.time() - crawl_start_time
        logger.info(
            f"Crawling completed with {len(crawling_results)} results "
            f"in {format_time(crawl_time)}"
        )

        # Run content chunking on the crawl results with configuration
        logger.info("Starting content chunking...")
        chunk_start_time = time.time()
        chunked_results = chunk_content(crawling_results, config)
        chunk_time = time.time() - chunk_start_time
        logger.info(
            f"Chunking completed with {len(chunked_results)} chunks "
            f"in {format_time(chunk_time)}"
        )

        # Run summarization with the chunk results and configuration
        logger.info("Starting content summarization...")
        summary_start_time = time.time()
        summarized_results = summarize_content(chunked_results, config)
        summary_time = time.time() - summary_start_time
        results_count = len(summarized_results)
        logger.info(
            f"Summarization completed with {results_count} results "
            f"in {format_time(summary_time)}"
        )

        if config.dry_run:
            # Save the summarized results instead of uploading to Pinecone
            logger.info(f"Saving results to {config.output_dir} folder")
            save_start_time = time.time()
            save_results_to_folder(summarized_results, config.output_dir)
            save_time = time.time() - save_start_time
            logger.info(f"Results saved to folder in {format_time(save_time)}")
        else:
            # Run Pinecone upload with configuration
            upload_start_time = time.time()
            upload_chunks(summarized_results, config)
            upload_time = time.time() - upload_start_time
            logger.info(f"Upload to Pinecone completed in {format_time(upload_time)}")

        # Calculate and log the total execution time
        total_time = time.time() - total_start_time
        logger.info(
            f"Orchestration completed successfully in {format_time(total_time)}"
        )

        # Print timing summary
        logger.info("===== Performance Summary =====")
        logger.info(f"Crawling:      {format_time(crawl_time)}")
        logger.info(f"Chunking:      {format_time(chunk_time)}")
        logger.info(f"Summarization: {format_time(summary_time)}")
        if config.dry_run:
            logger.info(f"Saving:        {format_time(save_time)}")
        else:
            logger.info(f"Upload:        {format_time(upload_time)}")
        logger.info(f"Total time:    {format_time(total_time)}")
        logger.info("=============================")

    except Exception as e:
        # Calculate execution time even if there's an error
        total_time = time.time() - total_start_time
        logger.error(f"Orchestration failed after {format_time(total_time)}: {str(e)}")
        sys.exit(1)


def save_results_to_folder(results, output_dir="cleaned_output"):
    """Save the chunked results to a folder as simple text files.

    Args:
        results (list): List of processed chunk results
        output_dir (str): Directory to save results to
    """
    try:
        # Create the output directory if it doesn't exist
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        # Clear all existing files in the output directory
        logger.info(f"Clearing existing files in {output_dir}")
        existing_files = list(output_dir.glob("*.md"))
        if existing_files:
            for file in existing_files:
                try:
                    file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete file {file}: {e}")
            logger.info(f"Removed {len(existing_files)} existing files")
        else:
            logger.info("No existing files found to clear")

        print(f"Saving {len(results)} chunks to {output_dir}")

        # Save each result as a simple text file
        for i, result in enumerate(results):
            # Get URL for filename
            page_path = getattr(result, "chunk_name", "unknown")
            page_path_part = (
                page_path.split("//")[-1].replace("/", "_").replace(":", "_")
            )

            # Create filename with index for uniqueness
            filename = f"{page_path_part}.md"
            file_path = output_dir / filename

            # Write the content to the file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(result.markdown)

            logger.info(f"Saved chunk {i+1} to {file_path}")

    except Exception as e:
        logger.error(f"Error saving chunks to folder: {str(e)}")
        raise


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Run the web crawler orchestration process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Save results to folder instead of uploading to Pinecone",
    )
    parser.add_argument(
        "--config",
        help="Path to YAML configuration file",
    )
    args = parser.parse_args()

    # Load config from file if specified
    config = None
    if args.config:
        try:
            config = CrawlerConfig.from_yaml(args.config)
            if args.dry_run:
                config.dry_run = True
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            sys.exit(1)

    asyncio.run(main(dry_run=args.dry_run if not config else config.dry_run))
