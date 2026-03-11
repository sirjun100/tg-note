"""Tests for OCR service (FR-030)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.ocr_service import (
    OCRUnprocessableImageError,
    _is_transient_http_error,
    _mask_api_key,
    check_gemini_api_key_available,
    extract_text_from_image,
)


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


def test_mask_api_key():
    """Mask shows first 4 and last 4 chars, hides middle."""
    assert _mask_api_key("AIzaSyB1234567890abcdefghijk") == "AIza...hijk"
    assert _mask_api_key("short") == "(too short or empty)"
    assert _mask_api_key("") == "(too short or empty)"
    assert _mask_api_key("123456789012") == "1234...9012"


# ---------------------------------------------------------------------------
# T-011: OCRUnprocessableImageError propagates correctly (US-046)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_raises_unprocessable_on_400_unable_to_process():
    """Gemini 400 'Unable to process input image' raises OCRUnprocessableImageError."""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Unable to process input image: corrupt or unsupported format"
    mock_resp.raise_for_status = MagicMock()

    with (
        patch("src.ocr_service.get_settings") as mock_settings,
        patch("src.ocr_service.httpx.AsyncClient") as mock_client,
    ):
        mock_settings.return_value = type("Settings", (), {"google": type("G", (), {"gemini_api_key": "key123"})()})()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

        with pytest.raises(OCRUnprocessableImageError):
            await extract_text_from_image(b"bad_image_bytes")


@pytest.mark.asyncio
async def test_photo_handler_catches_unprocessable_and_sends_user_message():
    """_handle_photo sends friendly error message when OCRUnprocessableImageError is raised."""
    from src.handlers import photo as photo_module

    _TEST_IMAGE_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100

    orch = MagicMock()
    orch.logging_service = MagicMock()
    orch.state_manager = MagicMock()

    user = MagicMock()
    user.id = 12345
    photo_file = AsyncMock()
    photo_file.download_as_bytearray = AsyncMock(return_value=bytearray(_TEST_IMAGE_BYTES))
    photo = MagicMock()
    photo.get_file = AsyncMock(return_value=photo_file)
    message = AsyncMock()
    message.photo = [photo]
    message.caption = None
    status_msg = AsyncMock()
    message.reply_text = AsyncMock(return_value=status_msg)
    status_msg.edit_text = AsyncMock()
    update = MagicMock()
    update.effective_user = user
    update.message = message

    with (
        patch("src.handlers.photo.check_whitelist", return_value=True),
        patch("src.ocr_service.extract_text_from_image", new_callable=AsyncMock, side_effect=OCRUnprocessableImageError()),
    ):
        await photo_module._handle_photo(orch, update, MagicMock())

    edit_calls = [c[0][0] for c in status_msg.edit_text.call_args_list]
    assert any("unable to process" in t.lower() or "different photo" in t.lower() for t in edit_calls)


# ---------------------------------------------------------------------------
# T-013: Retry on transient failures (US-047)
# ---------------------------------------------------------------------------

def test_is_transient_http_error_timeout():
    exc = httpx.TimeoutException("timeout", request=MagicMock())
    assert _is_transient_http_error(exc) is True


def test_is_transient_http_error_connect_error():
    exc = httpx.ConnectError("connection refused", request=MagicMock())
    assert _is_transient_http_error(exc) is True


def test_is_transient_http_error_500():
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    exc = httpx.HTTPStatusError("503", request=MagicMock(), response=mock_resp)
    assert _is_transient_http_error(exc) is True


def test_is_transient_http_error_400_not_transient():
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    exc = httpx.HTTPStatusError("400", request=MagicMock(), response=mock_resp)
    assert _is_transient_http_error(exc) is False


@pytest.mark.asyncio
async def test_extract_retries_on_timeout_then_succeeds():
    """On transient timeout, OCR retries and returns result on second attempt."""
    good_resp = MagicMock()
    good_resp.status_code = 200
    good_resp.raise_for_status = MagicMock()
    good_resp.json = MagicMock(return_value={
        "candidates": [{"content": {"parts": [
            {"text": '{"text":"hi","type":"document","summary":"s","suggested_title":"t","structured_data":null}'}
        ]}}]
    })

    call_count = 0

    async def _post_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.TimeoutException("timeout", request=MagicMock())
        return good_resp

    with (
        patch("src.ocr_service.get_settings") as mock_settings,
        patch("src.ocr_service.httpx.AsyncClient") as mock_client,
        patch("src.ocr_service.asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_settings.return_value = type("Settings", (), {"google": type("G", (), {"gemini_api_key": "key123"})()})()
        mock_client.return_value.__aenter__.return_value.post = _post_side_effect

        result = await extract_text_from_image(b"fake_bytes")

    assert result is not None
    assert result["text"] == "hi"
    assert call_count == 2  # failed once, succeeded on retry


def test_gemini_api_key_available_when_configured():
    """
    Verify GEMINI_API_KEY is resolvable from settings or env.
    Run locally with .env containing GEMINI_API_KEY to verify production config.
    Skips when key not set (e.g. CI); passes and prints masked key when configured.
    """
    from src.settings import get_settings

    get_settings.cache_clear()
    available, masked_repr = check_gemini_api_key_available()
    if not available:
        pytest.skip(
            "GEMINI_API_KEY not set. Add to .env or: fly secrets set GEMINI_API_KEY=..."
        )
    assert "..." in masked_repr or len(masked_repr) > 8
    print(f"\n✓ GEMINI_API_KEY resolved: {masked_repr}")
