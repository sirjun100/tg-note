"""
Dream image generation using Google AI Studio (Gemini).

Generates a symbolic/surrealist image representing a dream for the dream journal.
Uses GEMINI_API_KEY; if missing or request fails, returns None.
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


async def generate_dream_image(dream_description: str, key_symbols: list[str]) -> str | None:
    """
    Generate a symbolic/surrealist image representing the dream.

    Returns a data URL (data:image/png;base64,...) or None if key is missing or generation fails.
    """
    settings = get_settings()
    api_key = settings.google.gemini_api_key
    if not api_key or not api_key.strip():
        logger.info("GEMINI_API_KEY not set; skipping dream image generation")
        return None

    symbols_str = ", ".join(key_symbols[:5]) if key_symbols else "dreamlike symbols"
    prompt = (
        f"Create a surrealist, symbolic dream image in the style of Salvador Dalí or René Magritte. "
        f"Dream elements: {dream_description[:400]}. "
        f"Key symbols to include: {symbols_str}. "
        "Style: Dreamlike, symbolic, rich colors, mysterious atmosphere. "
        "Do NOT include any text or words in the image."
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
                    logger.warning("Gemini rate limit (429); dream image skipped")
                    return None
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
                logger.warning("Gemini rate limit (429); dream image skipped")
                return None
            logger.warning("Dream image generation failed: %s", exc)
            return None
    else:
        if last_exc:
            logger.warning("Dream image generation failed: %s", last_exc)
        return None

    candidates = data.get("candidates") or []
    if not candidates:
        logger.warning("Gemini dream image response had no candidates")
        return None
    parts = candidates[0].get("content", {}).get("parts") or []
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if not inline:
            continue
        raw = inline.get("data")
        mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
        if raw:
            data_url = f"data:{mime};base64,{raw}"
            logger.info("Generated dream image")
            return data_url

    logger.warning("Gemini dream image response had no image part")
    return None
