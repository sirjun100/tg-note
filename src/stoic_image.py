"""
Stoic reflection image generation using Google AI Studio (Gemini).

Generates a tasteful symbolic image for a morning/evening Stoic reflection.
Returns a data URL (data:image/png;base64,...) on success; None otherwise.
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


def _build_prompt(mode: str, reflection_markdown: str) -> str:
    safe_mode = "morning" if mode == "morning" else "evening"
    snippet = (reflection_markdown or "").strip().replace("\n", " ")
    snippet = snippet[:600]
    return (
        "Create a calm, symbolic illustration inspired by this Stoic journal reflection. "
        f"Mode: {safe_mode}. "
        f"Reflection: {snippet}. "
        "Style: minimal ink / watercolor illustration, soft lighting, contemplative mood. "
        "No text, no letters, no watermarks. "
        "Avoid depicting real identifiable people, medical scenes, injuries, or explicit content."
    )


async def generate_stoic_image(mode: str, reflection_markdown: str) -> tuple[str | None, str | None]:
    """Return (data_url, reason). On success: (data_url, None)."""
    settings = get_settings()
    api_key = settings.google.gemini_api_key
    if not api_key or not api_key.strip():
        logger.info("GEMINI_API_KEY not set; skipping Stoic image generation")
        return None, "API key not set"

    prompt = _build_prompt(mode, reflection_markdown)
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
                return None, "rate limit (429)"
            exc_str = str(exc)
            return None, f"request failed: {exc_str[:60]}{'...' if len(exc_str) > 60 else ''}"
    else:
        exc_str = str(last_exc) if last_exc else "unknown error"
        return None, f"request failed: {exc_str[:60]}{'...' if len(exc_str) > 60 else ''}"

    candidates = data.get("candidates") or []
    if not candidates:
        return None, "no image in response"
    parts = candidates[0].get("content", {}).get("parts") or []
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if not inline:
            continue
        raw = inline.get("data")
        mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
        if raw:
            return f"data:{mime};base64,{raw}", None
    return None, "no image in response"

