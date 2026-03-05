"""Tests for OCR service (FR-030)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ocr_service import extract_text_from_image


@pytest.mark.asyncio
async def test_extract_returns_none_when_no_api_key():
    with patch("src.ocr_service.get_settings") as mock_settings:
        mock_settings.return_value = type("Settings", (), {"google": type("G", (), {"gemini_api_key": ""})()})()
        result = await extract_text_from_image(b"fake_image_bytes")
    assert result is None


@pytest.mark.asyncio
async def test_extract_returns_fallback_on_empty_text():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(
        return_value={
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": ""}],
                    }
                }
            ]
        }
    )

    with (
        patch("src.ocr_service.get_settings") as mock_settings,
        patch("src.ocr_service.httpx.AsyncClient") as mock_client,
    ):
        mock_settings.return_value = type("Settings", (), {"google": type("G", (), {"gemini_api_key": "key123"})()})()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

        result = await extract_text_from_image(b"fake_bytes")

    assert result is not None
    assert result["text"] == ""
    assert result["type"] == "image"
    assert result["summary"] == "Image with no text"
    assert result["suggested_title"] == "Photo capture"


@pytest.mark.asyncio
async def test_extract_parses_valid_json_response():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(
        return_value={
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"text": "Hello world", "type": "document", "summary": "A doc", "suggested_title": "My Doc", "structured_data": null}',
                            }
                        ],
                    }
                }
            ]
        }
    )

    with (
        patch("src.ocr_service.get_settings") as mock_settings,
        patch("src.ocr_service.httpx.AsyncClient") as mock_client,
    ):
        mock_settings.return_value = type("Settings", (), {"google": type("G", (), {"gemini_api_key": "key123"})()})()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

        result = await extract_text_from_image(b"fake_bytes")

    assert result is not None
    assert result["text"] == "Hello world"
    assert result["type"] == "document"
    assert result["summary"] == "A doc"
    assert result["suggested_title"] == "My Doc"
    assert result["structured_data"] is None
