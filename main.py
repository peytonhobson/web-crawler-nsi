#!/usr/bin/env python3
"""
Main entry point for the web crawler and content processing system.

This script provides a command-line interface to run either the web crawler
or the Pinecone upload process, or both in sequence.

Usage:
    python main.py [--crawler] [--pinecone] [--dry-run]

Options:
    --crawler     Run the web crawler to fetch and process content
    --pinecone    Run the Pinecone upload process
    --dry-run     Run in dry mode for Pinecone (process but don't upload)

If no options are specified, both crawler and Pinecone upload will run.
"""

import os
import sys
import argparse
import importlib.util
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def import_module_from_file(module_name, file_path):
    """Dynamically import a module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        logger.error(f"Failed to load module '{module_name}' from {file_path}")
        return None

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error(f"Error loading module '{module_name}': {e}")
        return None


def run_crawler():
    """Run the web crawler to fetch and process content."""
    logger.info("Starting web crawler...")

    # Import the crawler module
    crawler_path = Path("crawler/crawl.py")
    if not crawler_path.exists():
        logger.error(f"Crawler file not found at {crawler_path}")
        return False

    crawler_module = import_module_from_file("crawler.crawl", crawler_path)
    if crawler_module is None:
        return False

    # Run the crawler main function
    try:
        if hasattr(crawler_module, "main"):
            import asyncio

            asyncio.run(crawler_module.main())
        else:
            logger.error("Crawler module does not have a main function")
            return False

        logger.info("Web crawler completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error running crawler: {e}")
        return False


def run_pinecone_upload(dry_run=False):
    """Run the Pinecone upload process."""
    mode = "dry run" if dry_run else "upload"
    logger.info(f"Starting Pinecone {mode} process...")

    # Import the vectordb upload module
    upload_path = Path("vectordb/upload_to_pinecone.py")
    if not upload_path.exists():
        logger.error(f"Upload file not found at {upload_path}")
        return False

    upload_module = import_module_from_file("vectordb.upload_to_pinecone", upload_path)
    if upload_module is None:
        return False

    # Run the Pinecone upload process
    try:
        # Call the process_markdown_files function directly
        if hasattr(upload_module, "process_markdown_files"):
            num_processed = upload_module.process_markdown_files(
                input_dir="crawler/winery_content", dry_run=dry_run
            )

            if num_processed > 0:
                logger.info(f"Successfully processed {num_processed} chunks")
                return True
            else:
                logger.error("No files were processed")
                return False
        else:
            logger.error(
                "Upload module does not have the process_markdown_files function"
            )
            return False

    except Exception as e:
        logger.error(f"Error running Pinecone upload: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run web crawler and/or Pinecone upload process"
    )
    parser.add_argument("--crawler", action="store_true", help="Run the web crawler")
    parser.add_argument(
        "--pinecone", action="store_true", help="Run the Pinecone upload process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry mode for Pinecone (process but don't upload)",
    )

    args = parser.parse_args()

    # If no options are specified, run both
    run_crawler_flag = args.crawler or not (args.crawler or args.pinecone)
    run_pinecone_flag = args.pinecone or not (args.crawler or args.pinecone)

    status = True

    if run_crawler_flag:
        crawler_success = run_crawler()
        if not crawler_success:
            logger.warning("The crawler process had errors")
            status = False

    if run_pinecone_flag:
        pinecone_success = run_pinecone_upload(dry_run=args.dry_run)
        if not pinecone_success:
            logger.warning("The Pinecone upload process had errors")
            status = False

    if status:
        logger.info("All requested processes completed successfully")
        return 0
    else:
        logger.error("One or more processes had errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
