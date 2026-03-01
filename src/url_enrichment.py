"""
URL enrichment helpers for note creation.

Extracts text and metadata from URLs so the LLM can generate
better tags and richer note bodies.
"""

from __future__ import annotations

import html
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(r"(https?://[^\s<>()]+)", re.IGNORECASE)


def extract_urls(text: str) -> List[str]:
    """Extract HTTP(S) URLs from user text."""
    if not text:
        return []
    urls = [m.group(1).rstrip(".,);]") for m in URL_PATTERN.finditer(text)]
    seen = set()
    deduped: List[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def _extract_meta(html_text: str, names: List[str]) -> Optional[str]:
    for name in names:
        pattern = (
            rf'<meta[^>]+(?:name|property)=["\']{re.escape(name)}["\'][^>]*content=["\'](.*?)["\']'
        )
        m = re.search(pattern, html_text, re.IGNORECASE | re.DOTALL)
        if m:
            value = html.unescape(m.group(1)).strip()
            if value:
                return value
    return None


def _extract_text(html_text: str, max_chars: int = 4000) -> str:
    clean = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", " ", html_text, flags=re.IGNORECASE)
    clean = re.sub(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:max_chars]


def _classify_url_type(url: str, title: str, extracted_text: str) -> str:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    haystack = f"{host} {path} {title.lower()} {extracted_text[:500].lower()}"

    if any(x in haystack for x in ["youtube.com", "youtu.be", "vimeo", "watch?v=", "/video/", "podcast", "spotify.com/show"]):
        return "media"
    if any(x in haystack for x in ["docs.", "/docs", "tutorial", "guide", "how to", "playbook", "checklist", "framework"]):
        return "actionable"
    return "knowledge"


def _template_for_url_type(url_type: str) -> Dict[str, str]:
    if url_type == "media":
        return {
            "template_id": "1",
            "template_name": "Quick Capture",
            "instructions": (
                "Use Template 1 - Quick Capture with sections: "
                "'Source', 'Why this matters', 'Key points'. "
                "Keep concise and practical."
            ),
        }
    if url_type == "actionable":
        return {
            "template_id": "3",
            "template_name": "Action-Oriented",
            "instructions": (
                "Use Template 3 - Action-Oriented with sections: "
                "'Source', 'What I learned', 'Actions to test', 'Decision'. "
                "Include actionable checkboxes when relevant."
            ),
        }
    return {
        "template_id": "2",
        "template_name": "Knowledge Enrichment",
        "instructions": (
            "Use Template 2 - Knowledge Enrichment with sections: "
            "'Source Metadata', 'Executive Summary', 'Main Ideas', "
            "'Notable Excerpts', 'My Context'."
        ),
    }


async def fetch_url_context(url: str) -> Dict[str, Any]:
    """
    Fetch and parse URL metadata/content for LLM enrichment.

    Returns a dict safe to pass into LLM context.
    """
    result: Dict[str, Any] = {
        "url": url,
        "final_url": url,
        "domain": urlparse(url).netloc.lower(),
        "title": "",
        "description": "",
        "author": "",
        "published_at": "",
        "content_type": "knowledge",
        "template_id": "2",
        "template_name": "Knowledge Enrichment",
        "template_instructions": "",
        "extracted_text": "",
        "error": "",
    }

    try:
        timeout = httpx.Timeout(12.0, connect=6.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            final_url = str(resp.url)
            html_text = resp.text[:300_000]

        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
        title = html.unescape(title_match.group(1)).strip() if title_match else ""
        if not title:
            title = _extract_meta(html_text, ["og:title", "twitter:title"]) or ""

        description = _extract_meta(
            html_text,
            ["description", "og:description", "twitter:description"],
        ) or ""
        author = _extract_meta(html_text, ["author", "article:author", "og:article:author"]) or ""
        published = _extract_meta(
            html_text,
            ["article:published_time", "publish_date", "date", "dc.date"],
        ) or ""
        extracted_text = _extract_text(html_text)

        content_type = _classify_url_type(final_url, title, extracted_text)
        template = _template_for_url_type(content_type)

        result.update(
            {
                "final_url": final_url,
                "domain": urlparse(final_url).netloc.lower(),
                "title": title,
                "description": description,
                "author": author,
                "published_at": published,
                "content_type": content_type,
                "template_id": template["template_id"],
                "template_name": template["template_name"],
                "template_instructions": template["instructions"],
                "extracted_text": extracted_text,
            }
        )
    except Exception as exc:
        logger.warning("Failed to fetch URL context for %s: %s", url, exc)
        result["error"] = str(exc)

    return result
