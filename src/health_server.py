"""
Minimal HTTP server for fly.io health checks.
Runs in a background daemon thread so it doesn't block the main bot.
"""

import http.server
import logging
import os
import socket
import threading

logger = logging.getLogger(__name__)


def _create_handler():
    """Create a simple handler that returns 200 OK for /health."""

    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health" or self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            logger.debug(format % args)

    return HealthHandler


def start_health_server(port: int = None):
    """
    Start a minimal HTTP server for health checks in a daemon thread.
    Used by fly.io to verify the app is running.
    """
    port = port or int(os.environ.get("PORT", "8080"))
    handler = _create_handler()

    def serve():
        try:
            with http.server.HTTPServer(("", port), handler) as httpd:
                logger.info("Health check server listening on port %d", port)
                httpd.serve_forever()
        except OSError as e:
            if e.errno == 98:  # Address already in use
                logger.warning("Health check port %d already in use, skipping", port)
            else:
                logger.error("Health server failed: %s", e)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return thread
