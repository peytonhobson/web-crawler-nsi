from urllib.parse import urlparse
import re


def sanitize_filename(url):
    """Convert URL path to a valid filename."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    # If path is empty (homepage), use 'home'
    if not path:
        return "home"

    # Replace invalid filename characters with underscores
    path = re.sub(r'[\\/*?:"<>|]', "_", path)
    # Replace slashes with underscores
    path = path.replace("/", "_")
    # Limit filename length
    if len(path) > 100:
        path = path[:100]

    return path
