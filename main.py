#!/usr/bin/env python3
"""
Intelligent Joplin Librarian - Main Entry Point
Telegram bot that creates Joplin notes using AI.
"""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.health_server import start_health_server
from src.telegram_orchestrator import main

if __name__ == "__main__":
    # Start health check server for fly.io (listens on PORT, default 8080)
    if os.environ.get("PORT"):
        start_health_server()
    main()