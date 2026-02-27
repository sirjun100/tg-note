#!/usr/bin/env python3
"""
Intelligent Joplin Librarian — entry point.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.log_config import setup_logging
from src.settings import get_settings


def main() -> None:
    settings = get_settings()
    setup_logging(debug=settings.debug)

    # Health-check server for Fly.io
    if os.environ.get("PORT"):
        from src.health_server import start_health_server
        start_health_server()

    from src.telegram_orchestrator import main as run_bot
    run_bot()


if __name__ == "__main__":
    main()
