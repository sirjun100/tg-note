#!/usr/bin/env python3
"""
Inspect the "03 - Resources" folder in Joplin: list subfolders and note counts.

Run from project root (so .env and Joplin URL are found). On Fly.io:
  fly ssh console -C "cd /app && python scripts/inspect_resources_folder.py"

Usage:
  python scripts/inspect_resources_folder.py
"""

import asyncio
import os
import sys

# Allow importing from src when run as script
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Optional: ensure cwd is repo root for .env
os.chdir(_REPO_ROOT)


async def main() -> None:
    from src.settings import get_settings
    from src.joplin_client import JoplinClient

    settings = get_settings()
    client = JoplinClient(settings=settings.joplin)

    try:
        folders = await client.get_folders()
    except Exception as e:
        print(f"Failed to fetch folders: {e}", file=sys.stderr)
        sys.exit(1)

    # Find Resources folder (common names)
    candidates = ["03 - Resources", "03 - resources", "Resources", "resources"]
    resources_folder = None
    for title in candidates:
        for f in folders:
            if f.get("title") == title:
                resources_folder = f
                break
        if resources_folder:
            break

    if not resources_folder:
        print("No '03 - Resources' (or 'Resources') folder found.")
        print("Top-level folders present:")
        roots = [f for f in folders if not f.get("parent_id")]
        for f in sorted(roots, key=lambda x: (x.get("title") or "")):
            print(f"  - {f.get('title')}")
        return

    rid = resources_folder["id"]
    title = resources_folder["title"]

    # Child folders (direct children of Resources)
    children = [f for f in folders if f.get("parent_id") == rid]
    # Notes directly in Resources folder
    notes_in_root = await client.get_notes_in_folder(rid)

    # Build tree with note counts
    lines = [f"\n📁 {title}\n"]
    lines.append(f"   (notes in root: {len(notes_in_root)})\n")

    for sub in sorted(children, key=lambda x: (x.get("title") or "")):
        sub_notes = await client.get_notes_in_folder(sub["id"])
        lines.append(f"   ├── {sub['title']}  ({len(sub_notes)} notes)")
    if children:
        lines.append("")

    # List note titles in root (first 20)
    if notes_in_root:
        lines.append("   Notes in root:")
        for n in notes_in_root[:20]:
            t = (n.get("title") or "(no title)")[:60]
            lines.append(f"      • {t}")
        if len(notes_in_root) > 20:
            lines.append(f"      … and {len(notes_in_root) - 20} more")

    print("\n".join(lines))


if __name__ == "__main__":
    asyncio.run(main())
