import sys
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from crawler.crawl import crawl
from summary import summarize_content

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


async def main():
    """Main orchestrator function that runs crawler, summarization,
    and Pinecone upload in sequence."""
    try:
        # Load environment variables
        load_dotenv()

        # Create logs directory if it doesn't exist
        # Path("logs").mkdir(exist_ok=True)

        logger.info("Starting orchestration process...")

        # Run crawler
        logger.info("Starting crawler...")
        crawling_results = await crawl()
        logger.info(f"Crawling completed with {len(crawling_results)} results")

        # Run summarization with the crawl results directly
        logger.info("Starting content summarization...")
        summarized_results = summarize_content(crawling_results)
        logger.info(f"Summarization completed with {len(summarized_results)} results")

        # Run Pinecone upload
        run_pinecone_upload()

        logger.info("Orchestration completed successfully")

    except Exception as e:
        logger.error(f"Orchestration failed: {str(e)}")
        sys.exit(1)


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


if __name__ == "__main__":
    asyncio.run(main())
