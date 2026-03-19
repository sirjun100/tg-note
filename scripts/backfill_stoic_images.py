#!/usr/bin/env python3
"""
Backfill Stoic reflection images for existing notes in Joplin.

Finds notes in the Stoic Journal folder and, for each note missing the Stoic image marker,
generates a symbolic image (Gemini) and embeds it near the top of the note.

Usage:
  python scripts/backfill_stoic_images.py --limit 10
  python scripts/backfill_stoic_images.py --dry-run
  python scripts/backfill_stoic_images.py --since-days 30

Notes:
  - Requires GEMINI_API_KEY for image generation.
  - Designed to be safe: use --dry-run first to preview what would change.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import logging
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

STOIC_JOURNAL_PATH = ["01 - Areas", "📓 Journaling", "Stoic Journal"]
STOIC_IMAGE_MARKER = "<!-- stoic-image -->"

# Allow importing from src when run as script
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Optional: ensure cwd is repo root for .env
os.chdir(_REPO_ROOT)


def _embed_stoic_image_in_body(note_body: str, resource_id: str) -> str:
    if not note_body:
        return note_body
    if STOIC_IMAGE_MARKER in note_body:
        return note_body
    image_block = f"{STOIC_IMAGE_MARKER}\n\n![Stoic reflection](:/{resource_id})"
    lines = note_body.split("\n", 2)
    if lines and lines[0].lstrip().startswith("#"):
        head = lines[0]
        rest = "\n".join(lines[1:]) if len(lines) > 1 else ""
        rest = rest.lstrip("\n")
        return f"{head}\n\n{image_block}\n\n{rest}".rstrip() + "\n"
    return f"{image_block}\n\n{note_body}".rstrip() + "\n"


def _infer_mode_from_body(note_body: str) -> str:
    body = note_body or ""
    if "### 🌙 Evening" in body and "### 🌞 Morning" in body:
        # Prefer the most recent section as "mode"; evening usually appended later.
        return "evening"
    if "### 🌙 Evening" in body:
        return "evening"
    return "morning"


def _extract_reflection_snippet(note_body: str, max_chars: int = 1200) -> str:
    """Extract a concise snippet from the reflection for prompting."""
    body = (note_body or "").strip()
    # Prefer content under morning/evening headings if present
    m = re.search(r"(### 🌞 Morning[\s\S]*?)(?=\n### 🌙 Evening|$)", body)
    e = re.search(r"(### 🌙 Evening[\s\S]*$)", body)
    if e:
        snippet = e.group(1).strip()
    elif m:
        snippet = m.group(1).strip()
    else:
        snippet = body
    return snippet[:max_chars]


async def _run(limit: int, since_days: int | None, dry_run: bool, sleep_ms: int) -> int:
    from src.joplin_client import JoplinClient
    from src.settings import get_settings
    from src.stoic_image import generate_stoic_image

    settings = get_settings()
    # Support env var override used by local scripts
    token = os.getenv("JOPLIN_TOKEN") or settings.joplin.token
    client = JoplinClient(base_url=settings.joplin.url, token=token, settings=settings.joplin)

    folder_id = await client.get_or_create_folder_by_path(STOIC_JOURNAL_PATH)
    notes = await client.get_notes_in_folder(folder_id)

    # Filter to daily reflections only (skip weekly review, etc.)
    items: list[dict[str, Any]] = []
    cutoff_ms: int | None = None
    if since_days is not None:
        cutoff_dt = datetime.now(UTC) - timedelta(days=since_days)
        cutoff_ms = int(cutoff_dt.timestamp() * 1000)

    for n in notes:
        title = (n.get("title") or "").strip()
        if "Daily Stoic Reflection" not in title:
            continue
        # since-days uses updated_time (available in folder listing)
        if cutoff_ms is not None:
            updated_ms = int(n.get("updated_time") or 0)
            if updated_ms and updated_ms < cutoff_ms:
                continue
        items.append(n)

    # Oldest first so you can stop early without starving older notes
    items.sort(key=lambda x: int(x.get("updated_time") or 0))

    changed = 0
    scanned = 0
    for n in items:
        if limit and changed >= limit:
            break
        note_id = n.get("id")
        if not note_id:
            continue
        scanned += 1
        full = await client.get_note(note_id)
        body = (full.get("body") or "").strip()
        if not body or STOIC_IMAGE_MARKER in body:
            continue

        mode = _infer_mode_from_body(body)
        snippet = _extract_reflection_snippet(body)
        logger.info("Generating image for %s (%s)", (full.get("title") or note_id)[:80], mode)

        if dry_run:
            changed += 1
            continue

        data_url, reason = await generate_stoic_image(mode, snippet)
        if not data_url or "," not in data_url:
            logger.warning("Skipping %s: %s", note_id[:12], reason or "no image")
            continue

        header, b64_data = data_url.split(",", 1)
        mime = "image/png"
        if "image/" in header:
            mime = header.split(":", 1)[1].split(";", 1)[0].strip()
        image_bytes = base64.b64decode(b64_data)
        resource = await client.create_resource(
            image_bytes, filename=f"stoic_backfill_{mode}.png", mime_type=mime
        )
        resource_id = resource.get("id")
        if not resource_id:
            logger.warning("Failed to create resource for %s", note_id[:12])
            continue

        new_body = _embed_stoic_image_in_body(body, resource_id)
        await client.update_note(note_id, {"body": new_body})
        changed += 1

        if sleep_ms > 0:
            await asyncio.sleep(sleep_ms / 1000.0)

    logger.info("Scanned %d stoic notes; updated %d", scanned, changed)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Max notes to update (0 = no limit).")
    parser.add_argument("--since-days", type=int, default=None, help="Only notes updated within last N days.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write; only count notes needing backfill.")
    parser.add_argument("--sleep-ms", type=int, default=250, help="Delay between notes to reduce rate-limits.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        updated = asyncio.run(_run(args.limit, args.since_days, args.dry_run, args.sleep_ms))
    except ModuleNotFoundError as exc:
        missing = getattr(exc, "name", None) or "a dependency"
        print(
            f"❌ Missing dependency: {missing}\n\n"
            "Run this script using the project's virtualenv, for example:\n"
            "  ./venv/bin/python scripts/backfill_stoic_images.py --dry-run\n"
        )
        raise
    except Exception as exc:
        msg = str(exc)
        if "Joplin authentication failed" in msg or "403" in msg:
            print(
                "❌ Joplin authentication failed.\n\n"
                "Set your token via env var, for example:\n"
                "  export JOPLIN_TOKEN='...'\n"
                "Then run:\n"
                "  ./venv/bin/python scripts/backfill_stoic_images.py --dry-run\n"
            )
        raise
    if args.dry_run:
        print(f"Would update {updated} note(s).")
    else:
        print(f"Updated {updated} note(s).")


if __name__ == "__main__":
    main()

