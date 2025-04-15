"""
Configuration module for web crawler settings.
"""

import os
import yaml
import json
from dataclasses import dataclass, field
from typing import List


@dataclass
class CrawlerConfig:
    """Configuration class for the web crawler."""

    # Crawling parameters
    start_urls: List[str] = field(default_factory=list)
    max_depth: int = 3
    include_external: bool = False
    batch_size: int = 20

    # Content filtering
    excluded_tags: List[str] = field(
        default_factory=lambda: ["footer", "nav", "header"]
    )

    # LLM settings
    llm_provider: str = "openai/gpt-4.1-nano"
    llm_instruction: str = """
        You are an assistant who is an expert at filtering content extracted from websites. You are given a page from a website.
        Your task is to extract ONLY substantive content that provides real value to customers visiting the website.
        The purpose of the content is to help customers learn about the company and its products by using it as chunks for RAG.
        
        IMPORTANT: Do NOT generate or create any content that doesn't explicitly exist on the page. Only extract content that is actually present.
        
        FORMAT REQUIREMENTS:
        - Use clear, hierarchical headers (H1, H2, H3) for each section
        - Add new lines between paragraphs and lists for better readability
        - Create concise, scannable bulleted lists for important details
        - Organize content logically while maintaining its actual presence on the page
        - Preserve exact pricing, dates, hours, and contact information
        - Preserve the existing content structure - do not invent new organization
        
        Exclude:
        - ALL navigation links and menu items
        - ALL social media links and sharing buttons
        - Any other information that is not relevant to the company and its products
        
        Remember: Only include content that actually exists on the page. Do not invent, generate, or create any content that isn't present.
    """

    # Chunking parameters
    chunk_size: int = 500
    chunk_overlap_ratio: float = 0.2

    # Summarization parameters
    summary_model_name: str = "gpt-4.1-nano"
    summary_temperature: float = 0.3
    summary_max_workers: int = 10

    # Vector DB parameters
    chunk_id_prefix: str = "web_crawl"
    record_retention_hours: int = 1
    upsert_batch_size: int = 50
    delete_old_records: bool = True

    # Processing control
    dry_run: bool = False
    verbose: bool = False

    # Output directories
    output_dir: str = "cleaned_output"
    logs_dir: str = "logs"

    @classmethod
    def from_environment(cls) -> "CrawlerConfig":
        """Load configuration from environment variables."""
        config = cls()

        # Process START_URLS (comma-separated string to list)
        if os.getenv("START_URLS"):
            config.start_urls = [
                url.strip() for url in os.getenv("START_URLS").split(",")
            ]

        # Process numeric values
        if os.getenv("MAX_DEPTH"):
            config.max_depth = int(os.getenv("MAX_DEPTH"))

        if os.getenv("BATCH_SIZE"):
            config.batch_size = int(os.getenv("BATCH_SIZE"))

        if os.getenv("CHUNK_SIZE"):
            config.chunk_size = int(os.getenv("CHUNK_SIZE"))

        if os.getenv("CHUNK_OVERLAP_RATIO"):
            config.chunk_overlap_ratio = float(os.getenv("CHUNK_OVERLAP_RATIO"))

        # Summarization parameters
        if os.getenv("SUMMARY_MODEL_NAME"):
            config.summary_model_name = os.getenv("SUMMARY_MODEL_NAME")

        if os.getenv("SUMMARY_TEMPERATURE"):
            config.summary_temperature = float(os.getenv("SUMMARY_TEMPERATURE"))

        if os.getenv("SUMMARY_MAX_TOKENS"):
            config.summary_max_tokens = int(os.getenv("SUMMARY_MAX_TOKENS"))

        if os.getenv("SUMMARY_MAX_WORKERS"):
            config.summary_max_workers = int(os.getenv("SUMMARY_MAX_WORKERS"))

        # Vector DB parameters
        if os.getenv("CHUNK_ID_PREFIX"):
            config.chunk_id_prefix = os.getenv("CHUNK_ID_PREFIX")

        if os.getenv("RECORD_RETENTION_HOURS"):
            config.record_retention_hours = int(os.getenv("RECORD_RETENTION_HOURS"))

        if os.getenv("UPSERT_BATCH_SIZE"):
            config.upsert_batch_size = int(os.getenv("UPSERT_BATCH_SIZE"))

        if os.getenv("DELETE_OLD_RECORDS"):
            config.delete_old_records = os.getenv("DELETE_OLD_RECORDS").lower() in [
                "true",
                "1",
                "yes",
            ]

        if os.getenv("DRY_RUN"):
            config.dry_run = os.getenv("DRY_RUN").lower() in ["true", "1", "yes"]

        if os.getenv("VERBOSE"):
            config.verbose = os.getenv("VERBOSE").lower() in ["true", "1", "yes"]

        # Process lists
        if os.getenv("EXCLUDED_TAGS"):
            try:
                config.excluded_tags = json.loads(os.getenv("EXCLUDED_TAGS"))
            except json.JSONDecodeError:
                # Fallback to comma-separated string
                config.excluded_tags = [
                    tag.strip() for tag in os.getenv("EXCLUDED_TAGS").split(",")
                ]

        # Directory settings
        if os.getenv("OUTPUT_DIR"):
            config.output_dir = os.getenv("OUTPUT_DIR")

        if os.getenv("LOGS_DIR"):
            config.logs_dir = os.getenv("LOGS_DIR")

        # LLM settings
        if os.getenv("LLM_PROVIDER"):
            config.llm_provider = os.getenv("LLM_PROVIDER")

        if os.getenv("LLM_INSTRUCTION"):
            config.llm_instruction = os.getenv("LLM_INSTRUCTION")

        return config

    @classmethod
    def from_yaml(cls, yaml_file: str) -> "CrawlerConfig":
        """Load configuration from a YAML file."""
        if not os.path.exists(yaml_file):
            raise FileNotFoundError(f"Config file not found: {yaml_file}")

        with open(yaml_file, "r") as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data)
