import re
from urllib.parse import urlparse


def process_markdown_results(results):
    """
    Process all crawled results with various cleaning operations.

    This function acts as an orchestrator for different markdown cleaning
    operations. It can remove links and perform other cleaning tasks.

    Args:
        results (list): List of crawler result objects

    Returns:
        list: Processed results with all cleaning operations applied
    """
    # Remove web page links but preserve file links (PDFs, etc.)
    processed_results = remove_web_page_links(results)

    # Future cleaning operations can be added here
    # processed_results = another_cleaning_function(processed_results)

    return processed_results


def is_file_link(url):
    """Check if a URL points to a file (has a file extension).

    Args:
        url (str): The URL to check

    Returns:
        bool: True if the URL points to a file, False otherwise
    """
    try:
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()

        # Check if the path contains a dot followed by letters/numbers
        # This indicates a file extension
        return "." in path and any(c.isalnum() for c in path.split(".")[-1])
    except Exception:
        return False


def remove_web_page_links(results):
    """
    Remove web page links from all documents while preserving file links (PDFs, etc.).
    Only removes links that point to web pages, keeps links to files.

    Args:
        results (list): List of crawler result objects

    Returns:
        list: Processed results with web page links removed, file links preserved
    """
    processed_results = []

    # Regular expression to identify markdown links
    # This matches exactly [text](url) format
    link_pattern = re.compile(r"\[(.*?)\]\((.*?)\)")

    for result in results:
        if not hasattr(result, "markdown") or not result.markdown:
            processed_results.append(result)
            continue

        def replace_link(match):
            link_text = match.group(1)
            link_url = match.group(2)

            # If it's a file link, preserve the entire markdown link
            if is_file_link(link_url):
                return f"[{link_text}]({link_url})"
            else:
                # If it's a web page link, just return the text
                return link_text

        # Replace links selectively
        modified_content = link_pattern.sub(replace_link, result.markdown)

        # Update the markdown content
        result.markdown = modified_content
        processed_results.append(result)

    return processed_results


def remove_all_markdown_links(results):
    """
    Remove all markdown links from all documents, preserving only the link text.

    This is the original function kept for backward compatibility.

    Args:
        results (list): List of crawler result objects

    Returns:
        list: Processed results with all links removed, only text preserved
    """
    processed_results = []

    # Regular expression to identify markdown links
    # This matches exactly [text](url) format
    link_pattern = re.compile(r"\[(.*?)\]\((.*?)\)")

    for result in results:
        if not hasattr(result, "markdown") or not result.markdown:
            processed_results.append(result)
            continue

        # Replace all links with just their text content
        modified_content = link_pattern.sub(r"\1", result.markdown)

        # Update the markdown content
        result.markdown = modified_content
        processed_results.append(result)

    return processed_results
