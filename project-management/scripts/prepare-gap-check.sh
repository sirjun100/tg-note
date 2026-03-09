#!/bin/bash
# Prepare Documentation-Code Consistency Check
# Lists files changed since last commit (or in staging) and outputs a reminder for the AI.
# Run from project root. Does not invoke AI; provides context for manual or AI-assisted gap check.

set -e

# Colors
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Run from git root (or PROJECT_ROOT when MCP runs from different cwd)
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$GIT_ROOT" ] && [ -n "$PROJECT_ROOT" ]; then
    GIT_ROOT="$PROJECT_ROOT"
fi
if [ -z "$GIT_ROOT" ]; then
    echo "Not a git repository. Run from project root."
    exit 1
fi
cd "$GIT_ROOT"

echo ""
echo -e "${BLUE}=== Documentation-Code Consistency Check Reminder ===${NC}"
echo ""
echo "Before committing, run the Documentation-Code Consistency Check."
echo "See: project-management/processes/doc-code-consistency-process.md"
echo ""

# Get changed files (staged + unstaged, vs HEAD)
CHANGED_FILES=$(git diff --name-only HEAD 2>/dev/null || true)
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || true)

if [ -n "$CHANGED_FILES" ] || [ -n "$STAGED_FILES" ]; then
    echo -e "${YELLOW}Changed files (for gap check context):${NC}"
    echo "$CHANGED_FILES" "$STAGED_FILES" | tr ' ' '\n' | sort -u | grep -v '^$' | while read -r f; do
        echo "  - $f"
    done
    echo ""
    # Check if both code and docs changed
    CODE_PATTERN='\.(sh|py|js|ts|yaml|json)$|^\.cursorrules$|^\.github/|^\.agent/|^\.claudecode/'
    DOC_PATTERN='\.(md)$|^project-management/'
    HAS_CODE=$(echo "$CHANGED_FILES" "$STAGED_FILES" | tr ' ' '\n' | grep -E "$CODE_PATTERN" | head -1)
    HAS_DOCS=$(echo "$CHANGED_FILES" "$STAGED_FILES" | tr ' ' '\n' | grep -E "$DOC_PATTERN" | head -1)
    if [ -n "$HAS_CODE" ] && [ -n "$HAS_DOCS" ]; then
        echo -e "${YELLOW}Both code and documentation changed. Gap check recommended.${NC}"
    fi
else
    echo "No uncommitted changes."
fi

echo ""
echo "To generate a gap report, ask the AI:"
echo '  "Generate a Documentation-Code Consistency Check report for my changes."'
echo ""
