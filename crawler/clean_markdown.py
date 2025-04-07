import re


def remove_redundant_markdown_links(results):
    """
    Remove redundant markdown links across all documents.
    Ensures each unique link appears only once across all documents.

    Args:
        results (list): List of crawler result objects

    Returns:
        list: Processed results with redundant links removed
    """
    processed_results = []
    seen_links = set()  # Track all unique links we've seen

    # Regular expression to identify markdown links
    # This matches exactly [text](url) format
    link_pattern = re.compile(r"\[(.*?)\]\((.*?)\)")

    # First pass: collect and mark the first occurrence of each link
    link_first_occurrence = {}  # Maps link to (result_index, line_index)

    for result_idx, result in enumerate(results):
        if not hasattr(result, "markdown") or not result.markdown:
            continue

        lines = result.markdown.split("\n")

        for line_idx, line in enumerate(lines):
            # Find all markdown links in this line
            matches = link_pattern.findall(line)

            for match in matches:
                link_text, link_url = match
                link_key = f"[{link_text}]({link_url})"

                # If this is the first time we're seeing this link
                if link_key not in seen_links:
                    seen_links.add(link_key)
                    link_first_occurrence[link_key] = (result_idx, line_idx)

    # Second pass: keep only the first occurrence of each link
    for result_idx, result in enumerate(results):
        if not hasattr(result, "markdown") or not result.markdown:
            processed_results.append(result)
            continue

        lines = result.markdown.split("\n")
        final_lines = []

        for line_idx, line in enumerate(lines):
            # Check if line contains links
            matches = link_pattern.findall(line)

            if not matches:
                # No links, keep the line
                final_lines.append(line)
                continue

            # If line contains only a single link and nothing else
            if len(line.strip()) == len(f"[{matches[0][0]}]({matches[0][1]})"):
                link_key = f"[{matches[0][0]}]({matches[0][1]})"

                # Only keep if this is the first occurrence
                if link_first_occurrence.get(link_key) == (result_idx, line_idx):
                    final_lines.append(line)
            else:
                # Line contains links but also other content
                # Keep line but potentially remove duplicate links
                modified_line = line
                for match in matches:
                    link_text, link_url = match
                    link_key = f"[{link_text}]({link_url})"

                    # If this isn't the first occurrence, remove the link
                    if link_first_occurrence.get(link_key) != (result_idx, line_idx):
                        modified_line = modified_line.replace(
                            f"[{link_text}]({link_url})", link_text
                        )

                final_lines.append(modified_line)

        # Update the markdown content
        result.markdown = "\n".join(final_lines)
        processed_results.append(result)

    return processed_results


def process_markdown_results(results):
    """
    Process all crawled results with various cleaning operations.

    This function acts as an orchestrator for different markdown cleaning operations.
    Currently, it only removes redundant markdown links, but is designed to be
    extended with additional cleaning operations in the future.

    Args:
        results (list): List of crawler result objects

    Returns:
        list: Processed results with all cleaning operations applied
    """
    # Remove redundant markdown links
    processed_results = remove_redundant_markdown_links(results)

    # Future cleaning operations can be added here
    # processed_results = another_cleaning_function(processed_results)

    return processed_results
