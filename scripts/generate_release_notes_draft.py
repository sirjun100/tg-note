#!/usr/bin/env python3
"""
Generate a draft release notes section from recent git commits.

Parses commit messages for BF-XXX and FR-XXX patterns and outputs a markdown
draft. Run from project root:

  python scripts/generate_release_notes_draft.py
  python scripts/generate_release_notes_draft.py --since 2026-03-01
  python scripts/generate_release_notes_draft.py --commits 10

Usage:
  Copy the output into RELEASE_NOTES.md and edit for clarity.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG_BUGS = os.path.join(_REPO_ROOT, "project-management", "backlog", "bugs")
BACKLOG_FEATURES = os.path.join(_REPO_ROOT, "project-management", "backlog", "features")

# Match BF-XXX or FR-XXX in commit messages
ID_PATTERN = re.compile(r"\b(BF-\d{3}|FR-\d{3})\b", re.IGNORECASE)


def find_backlog_path(item_id: str) -> str | None:
    """Return relative path to backlog file for BF-XXX or FR-XXX."""
    id_upper = item_id.upper()
    prefix, num = id_upper.split("-", 1)
    folder = BACKLOG_BUGS if prefix == "BF" else BACKLOG_FEATURES
    if not os.path.isdir(folder):
        return None
    prefix_folder = "bugs" if prefix == "BF" else "features"
    for name in os.listdir(folder):
        if name.upper().startswith(f"{id_upper}-") and name.endswith(".md"):
            return f"project-management/backlog/{prefix_folder}/{name}"
    return None


def get_commits(since: str | None = None, count: int = 20) -> list[tuple[str, str]]:
    """Return list of (hash, subject) for recent commits on main."""
    cmd = ["git", "log", "--oneline", f"-n{count}", "main"]
    if since:
        cmd.extend(["--since", since])
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=_REPO_ROOT)
    if result.returncode != 0:
        return []
    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split(" ", 1)
        if len(parts) == 2:
            commits.append((parts[0], parts[1]))
    return commits


def extract_ids_from_commits(commits: list[tuple[str, str]]) -> tuple[set[str], set[str]]:
    """Extract BF-XXX and FR-XXX from commit messages. Returns (bugs, features)."""
    bugs: set[str] = set()
    features: set[str] = set()
    for _hash, subject in commits:
        for m in ID_PATTERN.finditer(subject):
            id_upper = m.group(1).upper()
            if id_upper.startswith("BF-"):
                bugs.add(id_upper)
            elif id_upper.startswith("FR-"):
                features.add(id_upper)
    return bugs, features


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate release notes draft from git commits")
    parser.add_argument("--since", help="Only commits since date (e.g. 2026-03-01)")
    parser.add_argument("--commits", type=int, default=15, help="Number of commits to scan (default: 15)")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Release date for section header")
    args = parser.parse_args()

    os.chdir(_REPO_ROOT)
    commits = get_commits(since=args.since, count=args.commits)
    bugs, features = extract_ids_from_commits(commits)

    # Build title from commit message; prefer "ID: Title" or "ID — Title" pattern
    def title_for_id(item_id: str, commits: list[tuple[str, str]]) -> str:
        id_upper = item_id.upper()
        for _hash, subject in commits:
            if id_upper not in subject.upper():
                continue
            # Try "BF-018: Fix weekly report" or "BF-018; BF-019: Fix X; Split Y"
            for sep in ("; ", " — ", ": "):
                if sep in subject:
                    for part in subject.split(sep):
                        if id_upper in part.upper() and ":" in part:
                            after_colon = part.split(":", 1)[-1].strip()
                            if after_colon:
                                return after_colon[:60]
                        elif part.strip().upper().startswith(id_upper):
                            rest = part.split(":", 1)[-1].strip() if ":" in part else part.strip()
                            if rest:
                                return rest[:60]
            # Fallback: use part after first ": "
            if ": " in subject:
                return subject.split(": ", 1)[-1].split(";")[0].strip()[:60]
            return subject[:60]
        return item_id

    lines = [
        f"## {args.date}",
        "",
        "### New Features",
    ]
    for fid in sorted(features):
        path = find_backlog_path(fid)
        title = title_for_id(fid, commits)
        link = f"[{fid}]({path})" if path else fid
        lines.append(f"- **{title}** — (edit description). {link}")
    if not features:
        lines.append("- (none this release)")
    lines.extend(["", "### Bug Fixes"])
    for bid in sorted(bugs):
        path = find_backlog_path(bid)
        title = title_for_id(bid, commits)
        link = f"[{bid}]({path})" if path else bid
        lines.append(f"- **{title}** — (edit description). {link}")
    if not bugs:
        lines.append("- (none this release)")
    lines.extend([
        "",
        "### Breaking Changes",
        "- (none this release)",
        "",
        "### Migration Notes",
        "- (none this release)",
        "",
    ])
    print("\n".join(lines))


if __name__ == "__main__":
    main()
    sys.exit(0)
