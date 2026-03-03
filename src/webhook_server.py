"""
Lightweight async HTTP server for Telegram webhooks + Fly.io health checks.

Handles two routes on a single port (default 8080):
  GET  /health   → 200 OK  (Fly.io health check)
  POST /webhook  → 200 OK  (Telegram update, forwarded to PTB Application)

Runs in the same asyncio event loop as python-telegram-bot, so no
thread-safety issues when calling ``app.process_update()``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram.ext import Application

logger = logging.getLogger(__name__)

_READ_TIMEOUT = 15  # seconds per read
_MAX_BODY = 1 * 1024 * 1024  # 1 MB — Telegram updates are small


async def _read_request(reader: asyncio.StreamReader):
    """Parse an HTTP/1.x request into (method, path, headers, body)."""
    request_line = await asyncio.wait_for(reader.readline(), timeout=_READ_TIMEOUT)
    if not request_line:
        return None, None, {}, b""

    parts = request_line.decode("utf-8", errors="replace").strip().split(" ", 2)
    if len(parts) < 2:
        return None, None, {}, b""
    method, path = parts[0], parts[1]

    headers: dict[str, str] = {}
    while True:
        line = await asyncio.wait_for(reader.readline(), timeout=_READ_TIMEOUT)
        if line in (b"\r\n", b"\n", b""):
            break
        decoded = line.decode("utf-8", errors="replace").strip()
        if ":" in decoded:
            key, value = decoded.split(":", 1)
            headers[key.strip().lower()] = value.strip()

    body = b""
    content_length = int(headers.get("content-length", 0))
    if 0 < content_length <= _MAX_BODY:
        body = await asyncio.wait_for(reader.readexactly(content_length), timeout=_READ_TIMEOUT)

    return method, path, headers, body


def _http_response(status: int, body: bytes = b"") -> bytes:
    reason = {200: "OK", 404: "Not Found", 405: "Method Not Allowed", 403: "Forbidden"}.get(status, "")
    header = (
        f"HTTP/1.1 {status} {reason}\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    )
    return header.encode() + body


class WebhookServer:
    """Async TCP server that bridges Fly.io health checks and Telegram webhooks."""

    def __init__(
        self,
        ptb_app: Application,
        port: int = 8080,
        webhook_path: str = "/webhook",
        secret_token: str | None = None,
    ) -> None:
        self.ptb_app = ptb_app
        self.port = port
        self.webhook_path = webhook_path
        self.secret_token = secret_token
        self._server: asyncio.AbstractServer | None = None

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            method, path, headers, body = await _read_request(reader)

            if method == "GET" and path in ("/health", "/"):
                writer.write(_http_response(200, b"OK"))

            elif method == "POST" and path == self.webhook_path:
                if self.secret_token:
                    token = headers.get("x-telegram-bot-api-secret-token", "")
                    if token != self.secret_token:
                        logger.warning("Webhook rejected: bad secret token")
                        writer.write(_http_response(403, b"Forbidden"))
                        await writer.drain()
                        return

                try:
                    from telegram import Update
                    data = json.loads(body)
                    update = Update.de_json(data, self.ptb_app.bot)
                    asyncio.create_task(self.ptb_app.process_update(update))
                except Exception:
                    logger.exception("Failed to process webhook update")

                writer.write(_http_response(200, b"OK"))

            else:
                writer.write(_http_response(404))

            await writer.drain()
        except (TimeoutError, ConnectionResetError):
            pass
        except Exception:
            logger.exception("Webhook connection error")
        finally:
            writer.close()

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "0.0.0.0", self.port)
        logger.info("Webhook server listening on 0.0.0.0:%d", self.port)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Webhook server stopped")
