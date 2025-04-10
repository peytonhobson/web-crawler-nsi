import sys
import logging
import asyncio
import argparse
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from crawler.crawl import crawl
from chunk_content import chunk_content
from summary import summarize_content

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


async def main(dry_run=False):
    """Main orchestrator function that runs crawler, chunking, summarization,
    and Pinecone upload in sequence."""
    try:
        # Load environment variables
        load_dotenv()

        logger.info("Starting orchestration process...")

        # Run crawler
        logger.info("Starting crawler...")
        crawling_results = await crawl()
        logger.info(f"Crawling completed with {len(crawling_results)} results")

        # Run content chunking on the crawl results
        logger.info("Starting content chunking...")
        chunked_results = chunk_content(crawling_results)
        logger.info(f"Chunking completed with {len(chunked_results)} chunks")

        # Run summarization with the chunk results
        logger.info("Starting content summarization...")
        summarized_results = summarize_content(chunked_results)
        results_count = len(summarized_results)
        logger.info(f"Summarization completed with {results_count} results")

        if dry_run:
            # Save the summarized results instead of uploading to Pinecone
            logger.info("Saving results to chunks folder")
            save_results_to_folder(summarized_results)
        else:
            # Run Pinecone upload
            run_pinecone_upload()

        logger.info("Orchestration completed successfully")

    except Exception as e:
        logger.error(f"Orchestration failed: {str(e)}")
        sys.exit(1)


def save_results_to_folder(results):
    """Save the chunked results to a folder as simple text files.

    Args:
        results (list): List of processed chunk results
    """
    try:
        # Create the output directory if it doesn't exist
        output_dir = Path("cleaned_output")
        output_dir.mkdir(exist_ok=True)

        print(f"Saving {len(results)} chunks to {output_dir}")

        # Save each result as a simple text file
        for i, result in enumerate(results):
            # Get URL for filename
            page_path = getattr(result, "chunk_name", "unknown")
            page_path_part = (
                page_path.split("//")[-1].replace("/", "_").replace(":", "_")
            )

            # Create filename with index for uniqueness
            filename = f"{page_path_part}-{i+1}.txt"
            file_path = output_dir / filename

            # Write the content to the file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(result.markdown)

            logger.info(f"Saved chunk {i+1} to {file_path}")

    except Exception as e:
        logger.error(f"Error saving chunks to folder: {str(e)}")
        raise


def run_pinecone_upload():
    """Run the Pinecone upload script."""
    try:
        logger.info("Starting Pinecone upload...")
        from vectordb.pinecone import main as run_upload

        run_upload()
        logger.info("Pinecone upload completed successfully")
    except Exception as e:
        logger.error(f"Error running Pinecone upload: {str(e)}")
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
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run))
