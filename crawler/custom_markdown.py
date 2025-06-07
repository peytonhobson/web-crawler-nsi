#!/usr/bin/env python3
"""
Custom markdown generator for handling websites where crawl4ai's
built-in generators fail.
"""

import re
from bs4 import BeautifulSoup
from typing import Optional


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

            # Extract title
            title = soup.find("title")
            if title and title.get_text().strip():
                content_parts.append(f"# {title.get_text().strip()}")

            # Extract meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                content_parts.append(f"*{meta_desc.get('content').strip()}*")

            # Extract main content
            main_content = self._extract_main_content(soup)
            if main_content:
                content_parts.extend(main_content)

            # Join all parts
            markdown = "\n\n".join(filter(None, content_parts))

            # Clean up extra whitespace
            markdown = re.sub(r"\n{3,}", "\n\n", markdown)
            markdown = markdown.strip()

            return markdown if markdown else "No content extracted"

        except Exception as e:
            return f"Error generating markdown: {str(e)}"

    def _extract_main_content(self, soup: BeautifulSoup) -> list:
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

        # Extract content in order
        for element in main_container.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "blockquote", "div"]
        ):
            text = self._process_element(element)
            if text:
                content_parts.append(text)

        return content_parts

    def _process_element(self, element) -> Optional[str]:
        """Process individual HTML elements into markdown."""
        tag_name = element.name.lower()
        text = element.get_text().strip()

        if not text or len(text) < 3:
            return None

        # Skip elements that are likely navigation or footer
        classes = element.get("class", [])
        if any(
            cls in ["nav", "navigation", "menu", "footer", "header", "sidebar"]
            for cls in classes
        ):
            return None

        # Process based on tag type
        if tag_name == "h1":
            return f"# {text}"
        elif tag_name == "h2":
            return f"## {text}"
        elif tag_name == "h3":
            return f"### {text}"
        elif tag_name == "h4":
            return f"#### {text}"
        elif tag_name == "h5":
            return f"##### {text}"
        elif tag_name == "h6":
            return f"###### {text}"
        elif tag_name == "p":
            return text
        elif tag_name in ["ul", "ol"]:
            return self._process_list(element)
        elif tag_name == "blockquote":
            return f"> {text}"
        elif tag_name == "div":
            # Only include divs with substantial content
            if len(text) > 50 and not self._is_likely_navigation(element):
                return text

        return None

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
