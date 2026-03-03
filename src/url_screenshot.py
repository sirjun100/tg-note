"""
Capture a webpage URL as an image for attaching to notes.

Uses an external screenshot API (default: PageShot, no API key).
Returns a data URL (data:image/png;base64,...) or None on failure.
"""

from __future__ import annotations

import base64
import logging

import httpx

logger = logging.getLogger(__name__)

# PageShot: free, no API key, 30 req/min per IP
_PAGESHOT_URL = "https://pageshot.site/v1/screenshot"
_TIMEOUT = 25.0


async def capture_url_screenshot(url: str) -> str | None:
    """
    Capture a webpage at the given URL as a PNG image.

    Returns a data URL (data:image/png;base64,...) or None if capture fails.
    """
    if not url or not url.strip():
        return None
    url = url.strip()

    payload = {
        "url": url,
        "width": 1280,
        "height": 720,
        "full_page": False,
        "format": "png",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(_PAGESHOT_URL, json=payload)
            resp.raise_for_status()
            content_type = (resp.headers.get("content-type") or "").lower()
            if "image" not in content_type:
                logger.warning("Screenshot API returned non-image: %s", content_type[:50])
                return None
            raw = resp.content
    except (httpx.HTTPError, Exception) as exc:
        logger.warning("URL screenshot failed for %s: %s", url[:60], exc)
        return None

    if not raw:
        return None
    b64 = base64.standard_b64encode(raw).decode("ascii")
    mime = "image/png"
    if "jpeg" in content_type or "jpg" in content_type:
        mime = "image/jpeg"
    elif "webp" in content_type:
        mime = "image/webp"
    data_url = f"data:{mime};base64,{b64}"
    logger.info("Captured screenshot for URL (len=%d)", len(raw))
    return data_url
