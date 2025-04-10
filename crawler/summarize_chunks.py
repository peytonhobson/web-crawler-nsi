#!/usr/bin/env python3
"""
Chunk Summarization Script (with Parallel Processing)

This script processes chunked markdown files concurrently,
evaluates their content, removes unnecessary links, and adds
summaries to useful chunks.
"""

import os
import sys
import glob
import concurrent.futures
from dotenv import load_dotenv
from openai import OpenAI

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Configurable parameters
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.3
MAX_TOKENS = 800
MAX_WORKERS = 10


def process_chunk_content(content, client):
    """Process chunk content and determine if it should be kept."""
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert at evaluating content.\n"
                        "Your task is to ONLY delete content that is "
                        "completely useless.\n\n"
                        "ALWAYS KEEP content unless it is:\n"
                        "- Completely empty\n"
                        "- Only navigation links with no text\n"
                        "- Only social media buttons/links\n"
                        "- Only generic 'Contact Us' or 'Menu' text\n\n"
                        "For all other content, even if minimal:\n"
                        "1. Keep the content\n"
                        "2. Generate a SINGLE SENTENCE summary that:\n"
                        "   - Describes the overall topic/purpose of the chunk\n"
                        "   - Focuses on what information the chunk contains\n"
                        "   - Avoids listing specific items from the content\n"
                        "   - Uses precise terminology for RAG retrieval\n"
                        "   - Includes key descriptive words not in content\n"
                        "     if they would aid retrieval (e.g. if content\n"
                        "     lists items, add descriptive category words)\n"
                        "3. Return 'KEEP' followed by summary and content\n\n"
                        "Format response as:\n"
                        "KEEP\n"
                        "[Single-sentence summary]\n"
                        "[Content]\n"
                        "or\n"
                        "DELETE"
                    ),
                },
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

        # Print debug info
        print(f"Summary length: {len(summary)}")
        print(f"Content length: {len(cleaned_content)}")

        return cleaned_content, summary

    except Exception as e:
        print(f"Error processing chunk: {e}")
        return None, "DELETE"


def process_file(md_file, client):
    """Process an individual markdown file."""
    try:
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Skip if already has a summary
        if content.startswith("This chunk covers"):
            print(f"Skipping {os.path.basename(md_file)} - already processed")
            return "skipped"

        # Process content using the API
        cleaned_content, summary = process_chunk_content(content, client)

        if summary == "DELETE":
            # Delete both the markdown file and its corresponding metadata file
            os.remove(md_file)
            json_file = md_file.replace(".md", "_metadata.json")
            if os.path.exists(json_file):
                os.remove(json_file)
            print(
                f"Deleted {os.path.basename(md_file)} and its metadata file - no useful content"
            )
            return "deleted"
        else:
            updated_content = f"{summary}\n\n{cleaned_content}"
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(updated_content)
            print(f"Updated {os.path.basename(md_file)} with summary")
            return "kept"
    except Exception as e:
        print(f"Error processing {os.path.basename(md_file)}: {e}")
        return "error"


def process_chunks(chunks_dir):
    """Process all chunks in the directory concurrently."""
    md_files = glob.glob(os.path.join(chunks_dir, "*.md"))
    print(f"Found {len(md_files)} chunks to process")

    if not md_files:
        print("No chunk files found!")
        return

    # Initialize OpenAI client
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_file = {
            executor.submit(process_file, md_file, client): md_file
            for md_file in md_files
        }
        for future in concurrent.futures.as_completed(future_to_file):
            result = future.result()
            results.append(result)

    kept_count = results.count("kept")
    deleted_count = results.count("deleted")

    print("\nProcessing complete:")
    print(f"- Kept {kept_count} chunks with useful content")
    print(f"- Deleted {deleted_count} chunks with no useful content")


def main():
    if "OPENAI_API_KEY" not in os.environ:
        print("⚠️  OPENAI_API_KEY environment variable is not set.")
        return

    # Process chunks
    chunks_dir = "crawler/winery_content/chunks"
    process_chunks(chunks_dir)


if __name__ == "__main__":
    main()
