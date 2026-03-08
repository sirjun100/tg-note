#!/bin/bash
# Generate Release Notes Draft
# Parses recent commits for US-XXX, DEF-XXX, and TD-XXX patterns.
# Run from project root.
#
# Usage:
#   ./project-management/scripts/generate-release-notes-draft.sh [N]     # Print draft to stdout
#   ./project-management/scripts/generate-release-notes-draft.sh --auto [N]  # Append to RELEASE_NOTES.md
#   ./project-management/scripts/generate-release-notes-draft.sh -a [N]     # Same as --auto
#   ./project-management/scripts/generate-release-notes-draft.sh --dry-run [N]  # Show what --auto would write
#
#   N = number of commits to scan (default: 20)

set -e

GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$GIT_ROOT" ]; then
    echo "Not a git repository. Run from project root."
    exit 1
fi
cd "$GIT_ROOT"

AUTO=0
DRY_RUN=0
N=20

# Parse args
for arg in "$@"; do
    case "$arg" in
        --auto|-a) AUTO=1 ;;
        --dry-run) DRY_RUN=1 ;;
        [0-9]*)    N="$arg" ;;
    esac
done

LOG=$(git log -n "$N" --pretty=format:"%s" 2>/dev/null || true)
RELEASE_NOTES="RELEASE_NOTES.md"
TODAY=$(date +%Y-%m-%d)

# Build output
OUTPUT=""
OUTPUT="${OUTPUT}## ${TODAY}
"
OUTPUT="${OUTPUT}
### New Features
"
echo "$LOG" | grep -oE 'US-[0-9]+' | sort -u | while read -r id; do
    FILE=$(find project-management/backlog/user-stories -name "${id}-*.md" 2>/dev/null | head -1)
    if [ -n "$FILE" ]; then
        echo "- **${id}** — [${id}](${FILE})"
    else
        echo "- **${id}** — [${id}](project-management/backlog/user-stories/)"
    fi
done | while read -r line; do OUTPUT="${OUTPUT}${line}
"; done

# Capture FR output (subshell doesn't persist)
FR_LINES=$(echo "$LOG" | grep -oE 'US-[0-9]+' | sort -u | while read -r id; do
    FILE=$(find project-management/backlog/user-stories -name "${id}-*.md" 2>/dev/null | head -1)
    if [ -n "$FILE" ]; then
        echo "- **${id}** — [${id}](${FILE})"
    else
        echo "- **${id}** — [${id}](project-management/backlog/user-stories/)"
    fi
done)
BF_LINES=$(echo "$LOG" | grep -oE 'DEF-[0-9]+' | sort -u | while read -r id; do
    FILE=$(find project-management/backlog/defects -name "${id}-*.md" 2>/dev/null | head -1)
    if [ -n "$FILE" ]; then
        echo "- **${id}** — [${id}](${FILE})"
    else
        echo "- **${id}** — [${id}](project-management/backlog/defects/)"
    fi
done)
TD_LINES=$(echo "$LOG" | grep -oE 'TD-[0-9]+' | sort -u | while read -r id; do
    FILE=$(find project-management/backlog/technical-debt -name "${id}-*.md" 2>/dev/null | head -1)
    if [ -n "$FILE" ]; then
        echo "- **${id}** — [${id}](${FILE})"
    else
        echo "- **${id}** — [${id}](project-management/backlog/technical-debt/)"
    fi
done)

# Build full output
{
    echo "## ${TODAY}"
    echo ""
    echo "### New Features"
    echo "$FR_LINES"
    echo ""
    echo "### Defect Fixes"
    echo "$BF_LINES"
    echo ""
    if [ -n "$TD_LINES" ]; then
        echo "### Technical Debt"
        echo "$TD_LINES"
        echo ""
    fi
    echo "### Breaking Changes"
    echo "- (none this release)"
    echo ""
    echo "### Migration Notes"
    echo "- (none this release)"
} > /tmp/release-notes-draft.$$

if [ "$DRY_RUN" = "1" ]; then
    echo "=== Dry run: would append the following to $RELEASE_NOTES ==="
    cat /tmp/release-notes-draft.$$
    rm -f /tmp/release-notes-draft.$$
    exit 0
fi

if [ "$AUTO" = "1" ]; then
    # Append to RELEASE_NOTES.md
    if [ ! -f "$RELEASE_NOTES" ]; then
        echo "# Release Notes" > "$RELEASE_NOTES"
        echo "" >> "$RELEASE_NOTES"
    fi
    echo "" >> "$RELEASE_NOTES"
    cat /tmp/release-notes-draft.$$ >> "$RELEASE_NOTES"
    echo "Appended release notes for ${TODAY} to ${RELEASE_NOTES}"
    rm -f /tmp/release-notes-draft.$$
else
    cat /tmp/release-notes-draft.$$
    rm -f /tmp/release-notes-draft.$$
fi
