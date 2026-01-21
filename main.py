#!/usr/bin/env python3
"""
Intelligent Joplin Librarian - Main Entry Point
Telegram bot that creates Joplin notes using AI.
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.telegram_orchestrator import main

if __name__ == "__main__":
    main()