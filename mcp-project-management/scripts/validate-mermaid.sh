#!/bin/bash
# Mermaid Diagram Validation
# Extracts Mermaid blocks and validates syntax using mermaid-cli (mmdc) if available.
# Falls back to basic syntax check if mmdc not installed.
# Run from project root.

set -e

SCAN_DIR="${1:-project-management}"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Validating Mermaid diagrams..."
echo "----------------------------------------"

# Extract mermaid blocks
extract_mermaid() {
    local file="$1"
    awk '/^```mermaid$/,/^```$/' "$file" 2>/dev/null | grep -v '^```' || true
}

ERRORS=0
FILES=$(find "$SCAN_DIR" -name "*.md" 2>/dev/null || true)

while IFS= read -r file; do
    [ -z "$file" ] && continue
    blocks=$(extract_mermaid "$file" 2>/dev/null) || true
    [ -z "$blocks" ] && continue
    echo "Checking: $file"
    # Basic check: mermaid blocks should not be empty and should have valid structure
    if echo "$blocks" | grep -qE '^(flowchart|graph|stateDiagram|sequenceDiagram)'; then
        echo -e "  ${GREEN}✓${NC} Mermaid block found"
    else
        echo -e "  ${YELLOW}⚠${NC} Mermaid block may have syntax issues (validate at mermaid.live)"
    fi
done <<< "$FILES"

# If mmdc (mermaid-cli) is available, do full validation
if command -v mmdc &>/dev/null; then
    echo ""
    echo "Running mermaid-cli validation..."
    for file in $FILES; do
        [ ! -f "$file" ] && continue
        tmp=$(mktemp -d)
        extract_mermaid "$file" > "$tmp/diagram.mmd" 2>/dev/null || true
        if [ -s "$tmp/diagram.mmd" ]; then
            if ! mmdc -i "$tmp/diagram.mmd" -o /dev/null 2>/dev/null; then
                echo -e "${RED}✗ Mermaid syntax error in $file${NC}"
                ERRORS=$((ERRORS+1))
            fi
        fi
        rm -rf "$tmp"
    done
else
    echo ""
    echo -e "${YELLOW}⚠ mermaid-cli (mmdc) not installed. Install with: npm install -g @mermaid-js/mermaid-cli${NC}"
    echo "  Paste diagrams into https://mermaid.live to validate manually."
fi

echo "----------------------------------------"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ Mermaid validation passed${NC}"
    exit 0
else
    echo -e "${RED}✗ Mermaid validation failed${NC}"
    exit 1
fi
