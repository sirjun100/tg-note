#!/usr/bin/env python3
"""
Migrate project-management from FR/BF schema to MCP US/DEF schema.
- FR-N → US-N, features/ → user-stories/
- BF-N → DEF-N, bugs/ → defects/
- Update all cross-references
"""

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PM = ROOT / "project-management"
BACKLOG = PM / "backlog"
FEATURES = BACKLOG / "features"
BUGS = BACKLOG / "bugs"
USER_STORIES = BACKLOG / "user-stories"
DEFECTS = BACKLOG / "defects"
TECH_DEBT = BACKLOG / "technical-debt"
RETROSPECTIVE = BACKLOG / "retrospective-improvements"


def migrate_content(content: str, fr_to_us: bool) -> str:
    """Replace FR/BF with US/DEF in content. Replace both for cross-refs."""
    content = re.sub(r'\bFR-(\d+)\b', r'US-\1', content)
    content = re.sub(r'\bBF-(\d+)\b', r'DEF-\1', content)
    content = content.replace("features/", "user-stories/")
    content = content.replace("bugs/", "defects/")
    if fr_to_us:
        content = content.replace("Feature Request:", "User Story:")
        content = re.sub(r'# Feature Request: (US-\d+)', r'# User Story: \1', content)
    else:
        content = content.replace("Bug Fix:", "Defect:")
        content = re.sub(r'# Bug Fix: (DEF-\d+)', r'# Defect: \1', content)
    return content


def main():
    print("Creating directories...")
    USER_STORIES.mkdir(parents=True, exist_ok=True)
    DEFECTS.mkdir(parents=True, exist_ok=True)
    TECH_DEBT.mkdir(parents=True, exist_ok=True)
    RETROSPECTIVE.mkdir(parents=True, exist_ok=True)

    print("Migrating features → user-stories...")
    for f in sorted(FEATURES.glob("FR-*.md")):
        m = re.match(r"FR-(\d+)-(.*)\.md$", f.name)
        if m:
            n, slug = m.group(1), m.group(2)
            new_name = f"US-{int(n):03d}-{slug}.md"
            dest = USER_STORIES / new_name
            content = f.read_text(encoding="utf-8")
            content = migrate_content(content, fr_to_us=True)
            dest.write_text(content, encoding="utf-8")
            print(f"  {f.name} → {new_name}")

    print("Migrating bugs → defects...")
    for f in sorted(BUGS.glob("BF-*.md")):
        m = re.match(r"BF-(\d+)-(.*)\.md$", f.name)
        if m:
            n, slug = m.group(1), m.group(2)
            new_name = f"DEF-{int(n):03d}-{slug}.md"
            dest = DEFECTS / new_name
            content = f.read_text(encoding="utf-8")
            content = migrate_content(content, fr_to_us=False)
            dest.write_text(content, encoding="utf-8")
            print(f"  {f.name} → {new_name}")

    print("Updating product-backlog.md...")
    pb = BACKLOG / "product-backlog.md"
    content = pb.read_text(encoding="utf-8")
    content = content.replace("## Feature Requests", "## User Stories")
    content = content.replace("## Bug Fixes", "## Defects")
    content = content.replace("## Technical Debt\n\n| ID |", "## Technical Debt\n\n| ID |")
    content = re.sub(r'\[FR-(\d+)\]\(features/FR-(\d+)-([^)]+)\)', r'[US-\1](user-stories/US-\2-\3)', content)
    content = re.sub(r'\[BF-(\d+)\]\(bugs/BF-(\d+)-([^)]+)\)', r'[DEF-\1](defects/DEF-\2-\3)', content)
    content = re.sub(r'\bFR-(\d+)\b', r'US-\1', content)
    content = re.sub(r'\bBF-(\d+)\b', r'DEF-\1', content)
    content = content.replace("(FR-XXX for features, BF-XXX for bugs)", "(US-XXX for user stories, DEF-XXX for defects)")
    content = content.replace("`[FR-001](features/FR-001-feature-name.md)`", "`[US-001](user-stories/US-001-feature-name.md)`")
    # Add empty Technical Debt section if missing
    if "## Technical Debt" not in content:
        content = content.replace(
            "## Status Values",
            "## Technical Debt\n\n| ID | Title | Priority | Points | Status | Sprint | Created | Updated |\n|----|-------|----------|--------|--------|--------|---------|--------|\n\n## Status Values",
        )
    pb.write_text(content, encoding="utf-8")

    print("Updating sprints, docs, and other files...")
    def replace_in_file(path: Path) -> bool:
        if not path.suffix == ".md":
            return False
        # Skip backlog/features and backlog/bugs (we'll delete them)
        rel = path.relative_to(PM)
        if str(rel).startswith("backlog/features") or str(rel).startswith("backlog/bugs"):
            return False
        content = path.read_text(encoding="utf-8")
        new_content = re.sub(r"\bFR-(\d+)\b", r"US-\1", content)
        new_content = re.sub(r"\bBF-(\d+)\b", r"DEF-\1", new_content)
        new_content = new_content.replace("features/", "user-stories/")
        new_content = new_content.replace("bugs/", "defects/")
        if new_content != content:
            path.write_text(new_content, encoding="utf-8")
            return True
        return False

    updated = 0
    for f in PM.rglob("*.md"):
        if replace_in_file(f):
            updated += 1
            print(f"  Updated: {f.relative_to(PM)}")

    print(f"Removing old features/ and bugs/...")
    if FEATURES.exists():
        shutil.rmtree(FEATURES)
        print("  Removed backlog/features/")
    if BUGS.exists():
        shutil.rmtree(BUGS)
        print("  Removed backlog/bugs/")

    print("Done.")


if __name__ == "__main__":
    main()
