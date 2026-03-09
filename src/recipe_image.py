"""
Recipe image generation using Google AI Studio (Gemini).

Generates a single appetizing food image from the recipe title for use at the top of recipe notes.
Uses GEMINI_API_KEY from the environment; if missing or request fails, returns None.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from src.settings import get_settings

logger = logging.getLogger(__name__)

_GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_MAX_RETRIES_429 = 2
_RETRY_DELAY_SEC = 3.0


async def generate_recipe_image(recipe_title: str) -> tuple[str | None, str | None]:
    """
    Generate an appetizing food image for a recipe using Gemini image generation.

    Returns (data_url, error_reason). On success: (data_url, None).
    On failure: (None, human_readable_reason) for logging and user feedback.
    On 429 (rate limit), retries briefly then skips image so the note is still created.
    """
    settings = get_settings()
    api_key = settings.google.gemini_api_key
    if not api_key or not api_key.strip():
        logger.info("GEMINI_API_KEY not set; skipping recipe image generation for '%s'", recipe_title[:50])
        return None, "API key not set"

    prompt = (
        f"Appetizing, professional food photography of: {recipe_title}. "
        "Single dish, high quality, appetizing, no text or watermark."
    )
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
                        "Gemini rate limit (429); recipe image skipped for '%s'",
                        recipe_title[:50],
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
                    "Gemini rate limit (429); recipe image skipped for '%s'",
                    recipe_title[:50],
                )
                return None, "rate limit (429)"
            logger.warning("Gemini recipe image generation failed for '%s': %s", recipe_title[:50], exc)
            exc_str = str(exc)
            return None, f"request failed: {exc_str[:60]}{'...' if len(exc_str) > 60 else ''}"
    else:
        if last_exc:
            logger.warning("Gemini recipe image generation failed for '%s': %s", recipe_title[:50], last_exc)
        exc_str = str(last_exc) if last_exc else "unknown error"
        return None, f"request failed: {exc_str[:60]}{'...' if len(exc_str) > 60 else ''}"

    # Response: candidates[0].content.parts[] with inline_data.mime_type and inline_data.data (base64)
    candidates = data.get("candidates") or []
    if not candidates:
        logger.warning("Gemini image response had no candidates for '%s'", recipe_title[:50])
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
            logger.info("Generated recipe image for '%s'", recipe_title[:50])
            return data_url, None

    logger.warning("Gemini image response had no image part for '%s'", recipe_title[:50])
    return None, "no image in response"
