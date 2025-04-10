import sys
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

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


async def run_crawler():
    """Run the crawler script and return the output directory."""
    try:
        logger.info("Starting crawler...")
        from crawler.crawl import main as run_crawler

        output_dir = await run_crawler()
        if output_dir is None:
            logger.error("Crawler failed to return output directory")
            raise RuntimeError("Crawler failed to return output directory")

        logger.info(f"Crawler completed successfully. Output directory: {output_dir}")
        return output_dir
    except Exception as e:
        logger.error(f"Error running crawler: {str(e)}")
        raise


def run_summarization():
    """Run the chunk summarization script."""
    try:
        logger.info("Starting chunk summarization...")
        from crawler.summarize_chunks import main as run_summarize

        run_summarize()
        logger.info("Summarization completed successfully")
    except Exception as e:
        logger.error(f"Error running summarization: {str(e)}")
        raise


def run_pinecone_upload():
    """Run the Pinecone upload script."""
    try:
        logger.info("Starting Pinecone upload...")
        from vectordb.upload_to_pinecone_v2 import main as run_upload

        run_upload()
        logger.info("Pinecone upload completed successfully")
    except Exception as e:
        logger.error(f"Error running Pinecone upload: {str(e)}")
        raise


async def main():
    """Main orchestrator function that runs crawler, summarization, and Pinecone upload in sequence."""
    try:
        # Load environment variables
        load_dotenv()

        # Create logs directory if it doesn't exist
        Path("logs").mkdir(exist_ok=True)

        logger.info("Starting orchestration process...")

        # Run crawler
        await run_crawler()

        # Run summarization
        run_summarization()

        # Run Pinecone upload
        run_pinecone_upload()

        logger.info("Orchestration completed successfully")

    except Exception as e:
        logger.error(f"Orchestration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
