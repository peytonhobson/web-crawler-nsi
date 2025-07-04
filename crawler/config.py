"""
Configuration module for web crawler settings.
"""

import os
import yaml
import json
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv(override=True)


@dataclass
class CrawlerConfig:
    """Configuration class for the web crawler."""

    # Crawling parameters
    start_urls: List[str] = field(default_factory=list)
    max_depth: int = 3
    batch_size: int = 10
    include_external: bool = False

    # Content filtering
    excluded_tags: List[str] = field(
        default_factory=lambda: ["footer", "nav", "header"]
    )
    exclude_hidden_elements: bool = True
    delay_before_return_html: int = 3

    # Infinite scroll configuration
    enable_infinite_scroll: bool = True
    infinite_scroll_max_scrolls: int = 20
    infinite_scroll_delay: float = 2.0

    # Validation parameters
    expected_chunks: int = 0  # 0 means no validation
    chunk_threshold_pct: float = 20.0  # Default 20% threshold

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
        - ALL images
        
        Remember: Only include content that actually exists on the page. Do not invent, generate, or create any content that isn't present.
    """
    chunk_token_threshold: int = 400
    overlap_rate: float = 0.2

    # Chunking parameters
    embedding_model_name: str = "text-embedding-3-small"
    buffer_size: int = 3

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

    # Browser configuration
    browser_type: str = "chromium"
    headless: bool = True
    light_mode: bool = False  # Enable full features for JS execution
    text_mode: bool = False  # Enable images/content for proper infinite scroll
    ignore_https_errors: bool = True
    user_agent: str = "UntapAI-Crawler"

    # Output directories
    output_dir: str = "cleaned_output"
    logs_dir: str = "logs"

    @classmethod
    def from_environment(cls) -> "CrawlerConfig":
        """Load configuration from environment variables."""
        config = cls()

        # Process START_URLS (comma-separated string to list)
        if "START_URLS" in os.environ:
            config.start_urls = [
                url.strip() for url in os.environ["START_URLS"].split(",")
            ]

        # Process numeric values
        if "MAX_DEPTH" in os.environ:
            config.max_depth = int(os.environ["MAX_DEPTH"])

        if "BATCH_SIZE" in os.environ:
            config.batch_size = int(os.environ["BATCH_SIZE"])

        # Validation parameters
        if "EXPECTED_CHUNKS" in os.environ:
            config.expected_chunks = int(os.environ["EXPECTED_CHUNKS"])

        if "CHUNK_THRESHOLD_PCT" in os.environ:
            config.chunk_threshold_pct = float(os.environ["CHUNK_THRESHOLD_PCT"])

        if "DELAY_BEFORE_RETURN_HTML" in os.environ:
            config.delay_before_return_html = int(
                os.environ["DELAY_BEFORE_RETURN_HTML"]
            )

        if "EMBEDDING_MODEL_NAME" in os.environ:
            config.embedding_model_name = os.environ["EMBEDDING_MODEL_NAME"]

        if "BUFFER_SIZE" in os.environ:
            config.buffer_size = int(os.environ["BUFFER_SIZE"])

        # Summarization parameters
        if "SUMMARY_MODEL_NAME" in os.environ:
            config.summary_model_name = os.environ["SUMMARY_MODEL_NAME"]

        if "SUMMARY_TEMPERATURE" in os.environ:
            config.summary_temperature = float(os.environ["SUMMARY_TEMPERATURE"])

        if "SUMMARY_MAX_TOKENS" in os.environ:
            config.summary_max_tokens = int(os.environ["SUMMARY_MAX_TOKENS"])

        if "SUMMARY_MAX_WORKERS" in os.environ:
            config.summary_max_workers = int(os.environ["SUMMARY_MAX_WORKERS"])

        # Vector DB parameters
        if "CHUNK_ID_PREFIX" in os.environ:
            config.chunk_id_prefix = os.environ["CHUNK_ID_PREFIX"]

        if "RECORD_RETENTION_HOURS" in os.environ:
            config.record_retention_hours = int(os.environ["RECORD_RETENTION_HOURS"])

        if "UPSERT_BATCH_SIZE" in os.environ:
            config.upsert_batch_size = int(os.environ["UPSERT_BATCH_SIZE"])

        if "DELETE_OLD_RECORDS" in os.environ:
            config.delete_old_records = os.environ["DELETE_OLD_RECORDS"].lower() in [
                "true",
                "1",
                "yes",
            ]

        if "DRY_RUN" in os.environ:
            config.dry_run = os.environ["DRY_RUN"].lower() in ["true", "1", "yes"]

        if "VERBOSE" in os.environ:
            config.verbose = os.environ["VERBOSE"].lower() in ["true", "1", "yes"]

        # Process lists
        if "EXCLUDED_TAGS" in os.environ:
            try:
                config.excluded_tags = json.loads(os.environ["EXCLUDED_TAGS"])
            except json.JSONDecodeError:
                # Fallback to comma-separated string
                config.excluded_tags = [
                    tag.strip() for tag in os.environ["EXCLUDED_TAGS"].split(",")
                ]

        # Directory settings
        if "OUTPUT_DIR" in os.environ:
            config.output_dir = os.environ["OUTPUT_DIR"]

        if "LOGS_DIR" in os.environ:
            config.logs_dir = os.environ["LOGS_DIR"]

        # LLM settings
        if "LLM_PROVIDER" in os.environ:
            config.llm_provider = os.environ["LLM_PROVIDER"]

        if "LLM_INSTRUCTION" in os.environ:
            config.llm_instruction = os.environ["LLM_INSTRUCTION"]

        if "EXCLUDE_HIDDEN_ELEMENTS" in os.environ:
            config.exclude_hidden_elements = os.environ[
                "EXCLUDE_HIDDEN_ELEMENTS"
            ].lower() in ["true", "1", "yes"]

        # Browser configuration
        if "BROWSER_TYPE" in os.environ:
            config.browser_type = os.environ["BROWSER_TYPE"]

        if "HEADLESS" in os.environ:
            config.headless = os.environ["HEADLESS"].lower() in ["true", "1", "yes"]

        if "LIGHT_MODE" in os.environ:
            config.light_mode = os.environ["LIGHT_MODE"].lower() in ["true", "1", "yes"]

        if "TEXT_MODE" in os.environ:
            config.text_mode = os.environ["TEXT_MODE"].lower() in ["true", "1", "yes"]

        if "IGNORE_HTTPS_ERRORS" in os.environ:
            config.ignore_https_errors = os.environ["IGNORE_HTTPS_ERRORS"].lower() in [
                "true",
                "1",
                "yes",
            ]

        if "USER_AGENT" in os.environ:
            config.user_agent = os.environ["USER_AGENT"]

        # Infinite scroll configuration
        if "ENABLE_INFINITE_SCROLL" in os.environ:
            config.enable_infinite_scroll = os.environ[
                "ENABLE_INFINITE_SCROLL"
            ].lower() in ["true", "1", "yes"]

        if "INFINITE_SCROLL_MAX_SCROLLS" in os.environ:
            config.infinite_scroll_max_scrolls = int(
                os.environ["INFINITE_SCROLL_MAX_SCROLLS"]
            )

        if "INFINITE_SCROLL_DELAY" in os.environ:
            config.infinite_scroll_delay = float(os.environ["INFINITE_SCROLL_DELAY"])

        return config

    @classmethod
    def from_yaml(cls, yaml_file: str) -> "CrawlerConfig":
        """Load configuration from a YAML file."""
        if not os.path.exists(yaml_file):
            raise FileNotFoundError(f"Config file not found: {yaml_file}")

        with open(yaml_file, "r") as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data)
