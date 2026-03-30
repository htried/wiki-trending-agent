"""Build reader-facing Wikipedia URLs from project + page title."""

from __future__ import annotations

from urllib.parse import quote


def article_url_from_project(project: str, page_title: str) -> str:
    """Map e.g. en.wikipedia + Palm_Sunday -> https://en.wikipedia.org/wiki/Palm_Sunday"""
    if "." in project and project.endswith("wikipedia"):
        subdomain = project.split(".", 1)[0]
        host = f"{subdomain}.wikipedia.org"
    else:
        host = "en.wikipedia.org"

    segment = page_title.replace(" ", "_")
    encoded = quote(segment, safe="/_:()'%,-.!~*")  # keep common title punctuation unescaped
    return f"https://{host}/wiki/{encoded}"
