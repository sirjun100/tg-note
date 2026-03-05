"""
OCR service using Gemini 1.5 Flash for image text extraction.

Extracts text from photos (whiteboards, documents, screenshots, handwritten notes)
and returns structured data including type classification and suggested title.
Uses GEMINI_API_KEY; if missing or request fails, returns None.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os

import httpx

from src.settings import get_settings

logger = logging.getLogger(__name__)

_GEMINI_OCR_MODEL = "gemini-1.5-flash"
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_MAX_RETRIES_429 = 2
_RETRY_DELAY_SEC = 3.0

_OCR_PROMPT = """Extract all text from this image.

Return a JSON object with:
- "text": The extracted text, preserving structure where possible
- "type": One of "document", "whiteboard", "handwritten", "screenshot", "receipt", "business_card", "other"
- "summary": A one-line summary of what this image contains
- "suggested_title": A good title for a note about this content
- "structured_data": Optional dict with extracted fields (e.g. merchant/amount/date for receipts, name/email/phone for business cards)

If no text is visible, return {"text": "", "type": "image", "summary": "Image with no text", "suggested_title": "Photo capture", "structured_data": null}"""


async def extract_text_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict | None:
    """
    Extract text and classify image content using Gemini 1.5 Flash.

    Returns dict with keys: text, type, summary, suggested_title, structured_data.
    Returns None if GEMINI_API_KEY is missing or request fails.
    """
    settings = get_settings()
    api_key = settings.google.gemini_api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        logger.info("GEMINI_API_KEY not set; skipping OCR")
        return None

    b64 = base64.b64encode(image_bytes).decode("ascii")
    url = f"{_GEMINI_BASE}/models/{_GEMINI_OCR_MODEL}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": _OCR_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES_429 + 1):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
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
                    logger.warning("Gemini rate limit (429); OCR skipped")
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
                logger.warning("Gemini rate limit (429); OCR skipped")
                return None
            logger.warning("OCR failed: %s", exc)
            return None
    else:
        if last_exc:
            logger.warning("OCR failed: %s", last_exc)
        return None

    candidates = data.get("candidates") or []
    if not candidates:
        logger.warning("Gemini OCR response had no candidates")
        return None
    parts = candidates[0].get("content", {}).get("parts") or []
    if not parts:
        return None
    raw_text = parts[0].get("text", "")
    if not raw_text.strip():
        return {"text": "", "type": "image", "summary": "Image with no text", "suggested_title": "Photo capture", "structured_data": None}

    try:
        result = json.loads(raw_text)
        if not isinstance(result, dict):
            return {"text": raw_text, "type": "other", "summary": "Extracted text", "suggested_title": "Photo capture", "structured_data": None}
        result.setdefault("text", "")
        result.setdefault("type", "other")
        result.setdefault("summary", "")
        result.setdefault("suggested_title", "Photo capture")
        result.setdefault("structured_data", None)
        return result
    except json.JSONDecodeError:
        return {"text": raw_text, "type": "other", "summary": "Extracted text", "suggested_title": "Photo capture", "structured_data": None}
