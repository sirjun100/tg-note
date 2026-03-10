"""
Voice message handler: transcribe with OpenAI Whisper, route through note/task pipeline.

DEF-032 — Sprint 19.
"""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, MessageHandler, filters

from src.security_utils import check_whitelist, format_error_message

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)

_MAX_VOICE_BYTES = 25 * 1024 * 1024  # Whisper API limit: 25 MB


async def _transcribe_voice(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str | None:
    """
    Transcribe audio bytes using OpenAI Whisper.
    Returns the transcribed text, or None on failure.
    """
    try:
        import openai

        from config import OPENAI_API_KEY

        client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "voice.ogg"  # Whisper needs a filename with extension
        transcript = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text",
        )
        return transcript.strip() if isinstance(transcript, str) else None
    except Exception as exc:
        logger.warning("Whisper transcription failed: %s", exc)
        return None


async def _handle_voice(
    orch: TelegramOrchestrator, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Transcribe a voice (or audio) message and route through the note/task pipeline."""
    user = update.effective_user
    message = update.message
    if not user or not message:
        return

    user_id = user.id
    if not check_whitelist(user_id):
        await message.reply_text("❌ Sorry, you're not authorized to use this bot.")
        return

    # Support both voice notes and audio files
    audio = message.voice or message.audio
    if not audio:
        return

    file_size = getattr(audio, "file_size", None)
    if file_size and file_size > _MAX_VOICE_BYTES:
        size_mb = file_size / (1024 * 1024)
        await message.reply_text(
            format_error_message(
                f"Audio file is too large ({size_mb:.1f} MB). Maximum is 25 MB."
            )
        )
        return

    import contextlib
    with contextlib.suppress(Exception):
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

    status_msg = await message.reply_text("🎙️ Transcribing voice message...")

    try:
        voice_file = await audio.get_file()
        audio_bytes = bytes(await voice_file.download_as_bytearray())
    except Exception as exc:
        logger.warning("Failed to download voice file: %s", exc)
        await status_msg.edit_text(
            format_error_message("Could not download the voice message. Please try again.")
        )
        return

    transcript = await _transcribe_voice(audio_bytes)
    if not transcript:
        await status_msg.edit_text(
            format_error_message(
                "Could not transcribe the voice message. "
                "Please ensure the audio is clear and try again."
            )
        )
        return

    logger.info("Voice transcription: user=%d length=%d chars", user_id, len(transcript))
    await status_msg.edit_text(f"🎙️ *Transcribed:*\n_{transcript}_", parse_mode="Markdown")

    # Route transcribed text through the same pipeline as plain text messages
    from src.handlers.core import _route_plain_message

    handled = await _route_plain_message(
        orch=orch,
        user_id=user_id,
        text=transcript,
        message=message,
        telegram_message_id=message.message_id,
        context=context,
    )

    if not handled:
        await message.reply_text(
            format_error_message(
                "Could not process the transcribed message. "
                "Joplin may be unavailable — try again in a moment."
            )
        )


def register_voice_handlers(application: object, orch: TelegramOrchestrator) -> None:
    """Register voice and audio message handlers."""
    handler_func = _handle_voice

    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await handler_func(orch, update, context)

    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handler))  # type: ignore[attr-defined]
    logger.info("Voice handlers registered")
