import re


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
    # Remove all markdown links
    processed_results = remove_all_markdown_links(results)

    # Future cleaning operations can be added here
    # processed_results = another_cleaning_function(processed_results)

    return processed_results


def remove_all_markdown_links(results):
    """
    Remove all markdown links from all documents, preserving only the link text.

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
        modified_content = link_pattern.sub(r"\1", result.markdown.fit_markdown)

        # Update the markdown content
        result.markdown = modified_content
        processed_results.append(result)

    return processed_results
