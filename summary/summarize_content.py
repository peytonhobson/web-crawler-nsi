#!/usr/bin/env python3
"""
Chunk Summarization Module

This module processes crawl results directly in memory,
evaluates their content, and adds summaries to useful content.
It doesn't perform any file I/O operations.
"""

import concurrent.futures
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configurable parameters
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.3
MAX_TOKENS = 800
MAX_WORKERS = 10

client = OpenAI()

# System prompt for content evaluation
system_prompt = """
You are an expert at evaluating content.
Your task is to ONLY delete content that is "completely useless".
ALWAYS KEEP content unless it is:
- Completely empty
- Only navigation links with no text
- Only social media buttons/links
- Only generic 'Contact Us' or 'Menu' text

For all other content, even if minimal:
- Keep the content
- Generate a SINGLE SENTENCE summary that describes the overall topic/purpose 
  of the chunk
- Focuses on what information the chunk contains
- Avoids listing specific items from the content
- Uses precise terminology for RAG retrieval
- Includes key descriptive words not in content

Format response as:
KEEP
[Single-sentence summary]
[Content]
or
DELETE
"""


def summarize_content(crawl_results):
    """Process crawl results concurrently and return summarized results.

    Args:
        crawl_results (list): List of crawl result objects with markdown content

    Returns:
        list: Filtered and summarized crawl results
    """
    print(f"Found {len(crawl_results)} crawl results to process")

    if not crawl_results:
        print("No crawl results found!")
        return []

    processed_results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_result = {
            executor.submit(process_crawl_result, result): result
            for result in crawl_results
        }
        for future in concurrent.futures.as_completed(future_to_result):
            status, processed_result = future.result()
            print(f"Processed {processed_result.url} - {status}")
            if processed_result is not None:
                processed_results.append(processed_result)

    return processed_results


def process_crawl_result(result):
    """Process an individual crawl result.

    Args:
        result: A single crawl result object with markdown content
        client: OpenAI client instance

    Returns:
        tuple: (status, processed_result) where status is one of
        "kept", "deleted", "skipped", or "error"
    """
    try:
        # Get content from the crawl result
        content = result.markdown

        # Process content using the API
        cleaned_content, summary = process_chunk_content(content, client)

        if summary == "DELETE":
            print(f"Marked for deletion: {result.url} - no useful content")
            return "deleted", None
        else:
            # Update the result with the new content and summary
            updated_content = f"{summary}\n\n{cleaned_content}"
            result.markdown = updated_content
            print(f"Updated {result.url} with summary")
            return "kept", result
    except Exception as e:
        print(f"Error processing {result.url}: {e}")
        return "error", result


def process_chunk_content(content, client):
    """Process chunk content and determine if it should be kept.

    Args:
        content (str): The content to process
        client: OpenAI client instance

    Returns:
        tuple: (processed_content, summary) or (None, "DELETE")
    """
    try:
        # TODO: Output this as structured content using tooling
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Process this content:\n\n{content}",
                },
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

        result = response.choices[0].message.content.strip()

        if result.startswith("DELETE"):
            return None, "DELETE"

        # Parse the response - skip the "KEEP" line
        lines = result.split("\n")
        if len(lines) < 3:  # Need at least KEEP, summary, and content
            print(f"Unexpected response format: {result}")
            return None, "DELETE"

        summary = lines[1].strip()
        # Join all remaining lines as content
        cleaned_content = "\n".join(lines[2:]).strip()

        # Ensure summary format
        if not summary.startswith("This chunk covers"):
            summary = f"This chunk covers {summary}"
        if not summary.endswith("."):
            summary = f"{summary}."

        return cleaned_content, summary

    except Exception as e:
        print(f"Error processing chunk: {e}")
        return None, "DELETE"
