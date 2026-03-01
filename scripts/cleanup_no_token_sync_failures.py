#!/usr/bin/env python3
"""
One-off cleanup: remove task_sync_history rows that were logged as "failed"
only because the user had no Google token (BF-001). Those are not real sync
attempts and should not appear in sync status.

Run from project root so .env is loaded:
  python scripts/cleanup_no_token_sync_failures.py

On Fly.io (use sh -c so cd runs in a shell):
  fly ssh console -C "sh -c 'cd /app && python scripts/cleanup_no_token_sync_failures.py'"
"""

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
os.chdir(_REPO_ROOT)


def main() -> None:
    from src.settings import get_settings
    from src.logging_service import LoggingService

    settings = get_settings()
    db_path = settings.database.logs_db_path
    logging_service = LoggingService(db_path=db_path)

    deleted = logging_service.delete_failed_syncs_no_token()
    print(f"Deleted {deleted} false 'no token' failed sync row(s) from task_sync_history.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
