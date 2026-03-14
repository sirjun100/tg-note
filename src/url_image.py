"""
URL preview image generation using Gemini.

Generates an image from website-extracted metadata (title, description, content type,
extracted text) for use at the top of URL-based notes. Replaces the previous
screenshot-based flow.
Uses GEMINI_API_KEY from the environment; if missing or request fails, returns None.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from src.settings import get_settings

logger = logging.getLogger(__name__)

_GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_MAX_RETRIES_429 = 2
_RETRY_DELAY_SEC = 3.0
_GENERIC_SNIPPET_CHARS = 150


def _build_prompt(url_context: dict[str, Any], note_title: str | None) -> str:
    """Build image generation prompt from url_context and optional note title."""
    content_type = (url_context.get("content_type") or "knowledge").lower()

    if content_type == "recipe":
        title = (
            (note_title or "").strip()
            or (url_context.get("recipe_title") or "").strip()
            or (url_context.get("title") or "").strip()
        )
        if not title:
            title = "a recipe"
        return (
            f"Appetizing, professional food photography of: {title}. "
            "Single dish, high quality, appetizing, no text or watermark."
        )

    # Generic: knowledge, actionable, or other
    title = (url_context.get("title") or note_title or "").strip() or "a web page"
    desc = (url_context.get("description") or "").strip()
    extracted = (url_context.get("extracted_text") or "").strip()
    snippet = (desc or extracted)[:_GENERIC_SNIPPET_CHARS].strip()
    if snippet:
        snippet = snippet.replace("\n", " ").strip()
    if snippet:
        return (
            f"Professional, clean illustration or representative image for a web page about: {title}. "
            f"{snippet} "
            "No text or watermark, suitable as a note thumbnail."
        )
    return (
        f"Professional, clean illustration or representative image for a web page about: {title}. "
        "No text or watermark, suitable as a note thumbnail."
    )


async def _call_gemini_image(prompt: str, log_label: str) -> tuple[str | None, str | None]:
    """Call Gemini image API; returns (data_url, None) or (None, error_reason)."""
    settings = get_settings()
    api_key = settings.google.gemini_api_key
    if not api_key or not api_key.strip():
        logger.info("GEMINI_API_KEY not set; skipping URL image generation for '%s'", log_label[:50])
        return None, "API key not set"

    url = f"{_GEMINI_BASE}/models/{_GEMINI_IMAGE_MODEL}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "responseMimeType": "text/plain",
        },
    }

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES_429 + 1):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 429:
                    last_exc = httpx.HTTPStatusError(
                        "429 Too Many Requests (Gemini rate limit)",
                        request=resp.request,
                        response=resp,
                    )
                    if attempt < _MAX_RETRIES_429:
                        await asyncio.sleep(_RETRY_DELAY_SEC)
                        continue
                    logger.warning(
                        "Gemini rate limit (429); URL image skipped for '%s'",
                        log_label[:50],
                    )
                    return None, "rate limit (429)"
                resp.raise_for_status()
                data = resp.json()
                break
        except (httpx.HTTPError, Exception) as exc:
            last_exc = exc
            exc_resp = getattr(exc, "response", None)
            if exc_resp is not None and getattr(exc_resp, "status_code", None) == 429:
                if attempt < _MAX_RETRIES_429:
                    await asyncio.sleep(_RETRY_DELAY_SEC)
                    continue
                logger.warning(
                    "Gemini rate limit (429); URL image skipped for '%s'",
                    log_label[:50],
                )
                return None, "rate limit (429)"
            logger.warning("Gemini URL image generation failed for '%s': %s", log_label[:50], exc)
            exc_str = str(exc)
            return None, f"request failed: {exc_str[:60]}{'...' if len(exc_str) > 60 else ''}"
    else:
        if last_exc:
            logger.warning("Gemini URL image generation failed for '%s': %s", log_label[:50], last_exc)
        exc_str = str(last_exc) if last_exc else "unknown error"
        return None, f"request failed: {exc_str[:60]}{'...' if len(exc_str) > 60 else ''}"

    candidates = data.get("candidates") or []
    if not candidates:
        logger.warning("Gemini image response had no candidates for '%s'", log_label[:50])
        return None, "no image in response"
    parts = candidates[0].get("content", {}).get("parts") or []
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if not inline:
            continue
        raw = inline.get("data")
        mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
        if raw:
            data_url = f"data:{mime};base64,{raw}"
            logger.info("Generated URL image for '%s'", log_label[:50])
            return data_url, None

    logger.warning("Gemini image response had no image part for '%s'", log_label[:50])
    return None, "no image in response"


async def generate_url_image(
    url_context: dict[str, Any],
    note_title: str | None = None,
) -> tuple[str | None, str | None]:
    """
    Generate a preview image for a URL using Gemini, from website-extracted metadata.

    Uses title, description, content_type, and extracted_text from url_context to build
    the prompt. For recipes uses appetizing food-photo style; for other types uses a
    clean illustration/representative image style.

    Returns (data_url, None) on success, (None, human_readable_reason) on failure.
    """
    if not url_context:
        return None, "no URL context"
    prompt = _build_prompt(url_context, note_title)
    log_label = (
        (note_title or "").strip()
        or url_context.get("title")
        or url_context.get("url", "")[:60]
        or "url"
    )
    return await _call_gemini_image(prompt, str(log_label))
