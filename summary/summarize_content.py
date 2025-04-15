#!/usr/bin/env python3
"""
Chunk Keyword Generation Module

This module processes chunked documents directly in memory,
evaluates their content, and adds relevant keywords to useful content.
It doesn't perform any file I/O operations.
"""

import os
import concurrent.futures
from typing import List
from dotenv import load_dotenv
from openai import OpenAI
from langchain_core.documents import Document

# Load environment variables
load_dotenv()

# Configurable parameters
MODEL_NAME = os.getenv("SUMMARY_MODEL_NAME", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("SUMMARY_TEMPERATURE", "0.3"))
MAX_TOKENS = int(os.getenv("SUMMARY_MAX_TOKENS", "800"))
MAX_WORKERS = int(os.getenv("SUMMARY_MAX_WORKERS", "10"))

client = OpenAI()

# System prompt for content evaluation
system_prompt = """
You are an expert at evaluating content and generating relevant keywords.
Your task is to ONLY delete content that is "completely useless".
ALWAYS KEEP content unless it is:
- Completely empty
- Only navigation links with no text
- Only social media buttons/links
- Only generic 'Contact Us' or 'Menu' text

CRITICAL: NEVER modify, expand, or fabricate the original content. Do not add any information that is not explicitly present in the input.

For all other content, even if minimal:
- Keep the EXACT content without changes
- Generate 5-10 KEYWORDS that:
  * DO NOT already exist in the content
  * Are semantically related to the content
  * Would help a vector search engine find this content
  * Use precise terminology for RAG retrieval
  * Are comma-separated without bullets or numbering

Format response as:
KEEP
[comma-separated keywords]
[UNMODIFIED original content]
or
DELETE
"""


def summarize_content(chunked_documents: List[Document], config=None):
    """Process chunked documents concurrently and return results with keywords.

    Args:
        chunked_documents (list): List of Document objects with chunk content
        config: Optional configuration object with summarization parameters

    Returns:
        list: Filtered documents with added keywords
    """
    print(f"Found {len(chunked_documents)} chunks to process")

    if not chunked_documents:
        print("No chunks found!")
        return []

    # Use configuration if provided
    model_name = MODEL_NAME
    temperature = TEMPERATURE
    max_tokens = MAX_TOKENS
    max_workers = MAX_WORKERS

    if config:
        model_name = getattr(config, "summary_model_name", model_name)
        temperature = getattr(config, "summary_temperature", temperature)
        max_tokens = getattr(config, "summary_max_tokens", max_tokens)
        max_workers = getattr(config, "summary_max_workers", max_workers)

    processed_results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_chunk = {
            executor.submit(
                process_chunk, chunk, model_name, temperature, max_tokens
            ): chunk
            for chunk in chunked_documents
        }
        for future in concurrent.futures.as_completed(future_to_chunk):
            chunk = future_to_chunk[future]
            status, processed_chunk = future.result()
            url = chunk.metadata.get("url", "unknown")
            print(f"Processed chunk from {url} - {status}")
            if processed_chunk is not None:
                processed_results.append(processed_chunk)

    return processed_results


def process_chunk(
    chunk, model_name=MODEL_NAME, temperature=TEMPERATURE, max_tokens=MAX_TOKENS
):
    """Process an individual chunk.

    Args:
        chunk: A Document object with page_content and metadata
        model_name: The OpenAI model to use
        temperature: Temperature setting for generation
        max_tokens: Maximum tokens for the response

    Returns:
        tuple: (status, processed_chunk) where status is one of
        "kept", "deleted", "skipped", or "error"
    """
    try:
        # Get content from the chunk
        content = chunk.page_content
        url = chunk.metadata.get("url", "unknown")

        # Process content using the API
        cleaned_content, keywords = process_chunk_content(
            content, client, model_name, temperature, max_tokens
        )

        if keywords == "DELETE":
            print(f"Marked for deletion: chunk from {url} - no useful content")
            return "deleted", None
        else:
            # Create a new result object similar to the crawl results
            # to maintain compatibility with downstream processing
            from types import SimpleNamespace

            result = SimpleNamespace()

            # Add the metadata from the original chunk
            for key, value in chunk.metadata.items():
                setattr(result, key, value)

            # Set standard attributes expected by downstream processes
            result.url = url
            result.markdown = (
                f"[View Source]({url})\n\n"
                f"Keywords: {keywords}\n\n"
                f"{cleaned_content}"
            )

            print(f"Updated chunk from {url} with keywords")
            return "kept", result
    except Exception as e:
        print(f"Error processing chunk from {url}: {e}")
        return "error", None


def process_chunk_content(
    content,
    client,
    model_name=MODEL_NAME,
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS,
):
    """Process chunk content and determine if it should be kept.

    Args:
        content (str): The content to process
        client: OpenAI client instance
        model_name: Model to use for processing
        temperature: Temperature setting for generation
        max_tokens: Maximum tokens in the response

    Returns:
        tuple: (processed_content, keywords) or (None, "DELETE")
    """
    try:
        # Verify content is not empty
        if not content or content.isspace():
            return None, "DELETE"

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Process this content:\n\n{content}",
                },
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        result = response.choices[0].message.content.strip()

        if result.startswith("DELETE"):
            return None, "DELETE"

        # Parse the response - skip the "KEEP" line
        lines = result.split("\n")
        if len(lines) < 3:  # Need at least KEEP, keywords, and content
            print(f"Unexpected response format: {result}")
            return None, "DELETE"

        keywords = lines[1].strip()
        # Compare the length of the input and output content to detect hallucination
        cleaned_content = "\n".join(lines[2:]).strip()

        # Check if content length has significantly increased (potential hallucination)
        if len(cleaned_content) > len(content) * 1.2:  # 20% increase threshold
            print(f"Potential content hallucination detected - using original content")
            cleaned_content = content  # Use original content instead

        return cleaned_content, keywords

    except Exception as e:
        print(f"Error processing chunk: {e}")
        return None, "DELETE"
