#!/usr/bin/env python3
"""
Custom markdown generator for handling websites where crawl4ai's
built-in generators fail.
"""

import re
from bs4 import BeautifulSoup
from typing import Optional, Set


class CustomMarkdownGenerator:
    """Custom markdown generator using BeautifulSoup for HTML parsing."""

    def __init__(self):
        self.name = "custom_markdown"

    def generate_markdown(self, html: str, base_url: str = "") -> str:
        """
        Generate markdown from HTML using BeautifulSoup.

        Args:
            html: Raw HTML content
            base_url: Base URL for the page (optional)

        Returns:
            Markdown formatted string
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            content_parts = []
            seen_content = set()  # Track seen content to avoid duplicates

            # Extract title
            title = soup.find("title")
            if title and title.get_text().strip():
                title_text = title.get_text().strip()
                content_parts.append(f"# {title_text}")
                seen_content.add(self._normalize_text(title_text))

            # Extract meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                desc_text = meta_desc.get("content").strip()
                content_parts.append(f"*{desc_text}*")
                seen_content.add(self._normalize_text(desc_text))

            # Extract main content
            main_content = self._extract_main_content(soup, seen_content)
            if main_content:
                content_parts.extend(main_content)

            # Join all parts
            markdown = "\n\n".join(filter(None, content_parts))

            # Clean up extra whitespace
            markdown = re.sub(r"\n{3,}", "\n\n", markdown)
            markdown = markdown.strip()

            # Final deduplication pass on the complete markdown
            markdown = self._remove_duplicate_paragraphs(markdown)

            return markdown if markdown else "No content extracted"

        except Exception as e:
            return f"Error generating markdown: {str(e)}"

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison by removing extra whitespace and
        converting to lowercase."""
        # Remove extra whitespace and normalize
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        return normalized

    def _remove_duplicate_paragraphs(self, markdown: str) -> str:
        """Remove duplicate paragraphs from the final markdown."""
        if not markdown:
            return markdown

        # Split into paragraphs (double newline separated)
        paragraphs = markdown.split("\n\n")
        seen_paragraphs = set()
        unique_paragraphs = []

        for paragraph in paragraphs:
            if not paragraph.strip():
                continue

            # Normalize for comparison
            normalized = self._normalize_text(paragraph)

            # Skip if we've seen this paragraph before
            if normalized in seen_paragraphs:
                continue

            # Check for substantial similarity with existing paragraphs
            is_duplicate = False
            for seen in seen_paragraphs:
                if len(normalized) > 20 and len(seen) > 20:
                    if (
                        normalized in seen
                        or seen in normalized
                        or self._calculate_similarity(normalized, seen) > 0.85
                    ):
                        is_duplicate = True
                        break

            if not is_duplicate:
                unique_paragraphs.append(paragraph)
                seen_paragraphs.add(normalized)

        return "\n\n".join(unique_paragraphs)

    def _extract_main_content(
        self, soup: BeautifulSoup, seen_content: Set[str]
    ) -> list:
        """Extract main content elements from the soup."""
        content_parts = []

        # Try to find main content area
        main_selectors = [
            "main",
            '[role="main"]',
            ".main-content",
            ".content",
            "#content",
            ".post-content",
            "article",
        ]

        main_container = None
        for selector in main_selectors:
            main_container = soup.select_one(selector)
            if main_container:
                break

        # If no main container found, use body
        if not main_container:
            main_container = soup.find("body")

        if not main_container:
            return content_parts

        # Extract content in order, avoiding duplicates
        processed_elements = set()
        for element in main_container.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "blockquote", "div"]
        ):
            # Skip if we've already processed this element
            element_id = id(element)
            if element_id in processed_elements:
                continue

            text = self._process_element(element, seen_content)
            if text:
                content_parts.append(text)
                processed_elements.add(element_id)

        return content_parts

    def _process_element(self, element, seen_content: Set[str]) -> Optional[str]:
        """Process individual HTML elements into markdown."""
        tag_name = element.name.lower()
        text = element.get_text().strip()

        if not text or len(text) < 3:
            return None

        # Normalize text for comparison
        normalized_text = self._normalize_text(text)

        # Check for exact duplicate content
        if normalized_text in seen_content:
            return None

        # Check for similar content using multiple methods
        if self._is_duplicate_content(normalized_text, seen_content):
            return None

        # Skip elements that are likely navigation or footer
        classes = element.get("class", [])
        if any(
            cls in ["nav", "navigation", "menu", "footer", "header", "sidebar"]
            for cls in classes
        ):
            return None

        # Process based on tag type
        result = None
        if tag_name == "h1":
            result = f"# {text}"
        elif tag_name == "h2":
            result = f"## {text}"
        elif tag_name == "h3":
            result = f"### {text}"
        elif tag_name == "h4":
            result = f"#### {text}"
        elif tag_name == "h5":
            result = f"##### {text}"
        elif tag_name == "h6":
            result = f"###### {text}"
        elif tag_name == "p":
            result = text
        elif tag_name in ["ul", "ol"]:
            result = self._process_list(element)
        elif tag_name == "blockquote":
            result = f"> {text}"
        elif tag_name == "div":
            # Only include divs with substantial content
            if len(text) > 50 and not self._is_likely_navigation(element):
                result = text

        # Add to seen content if we're returning it
        if result:
            seen_content.add(normalized_text)

        return result

    def _is_duplicate_content(
        self, normalized_text: str, seen_content: Set[str]
    ) -> bool:
        """Check if content is a duplicate using multiple methods."""
        # Method 1: Check if this text is contained in any seen content
        for seen in seen_content:
            if len(normalized_text) > 20 and len(seen) > 20:
                # Check if one is contained in the other
                if normalized_text in seen or seen in normalized_text:
                    return True

                # Check word-based similarity
                if self._calculate_similarity(normalized_text, seen) > 0.8:
                    return True

        return False

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts based on word overlap."""
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        # Jaccard similarity
        return len(intersection) / len(union) if union else 0.0

    def _process_list(self, list_element) -> str:
        """Process ul/ol elements into markdown lists."""
        items = []
        for li in list_element.find_all("li", recursive=False):
            text = li.get_text().strip()
            if text:
                items.append(f"- {text}")

        return "\n".join(items) if items else ""

    def _is_likely_navigation(self, element) -> bool:
        """Check if element is likely navigation/menu content."""
        classes = element.get("class", [])
        ids = element.get("id", "")

        nav_indicators = [
            "nav",
            "navigation",
            "menu",
            "header",
            "footer",
            "sidebar",
            "breadcrumb",
            "pagination",
        ]

        return any(
            indicator in " ".join(classes).lower() or indicator in ids.lower()
            for indicator in nav_indicators
        )


def create_custom_markdown_generator():
    """Factory function to create a custom markdown generator."""
    return CustomMarkdownGenerator()
