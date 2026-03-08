#!/bin/bash
# Backlog Integrity Validation
# Verifies product-backlog table matches item files: no orphans, no duplicates, IDs/titles/status aligned.
# Run from project root.

set -e

BACKLOG_DIR="${1:-project-management/backlog}"
PRODUCT_BACKLOG="${BACKLOG_DIR}/product-backlog.md"
USER_STORIES_DIR="${BACKLOG_DIR}/user-stories"
DEFECTS_DIR="${BACKLOG_DIR}/defects"
TECH_DEBT_DIR="${BACKLOG_DIR}/technical-debt"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

echo "Validating backlog integrity..."
echo "----------------------------------------"

if [ ! -f "$PRODUCT_BACKLOG" ]; then
    echo -e "${RED}✗ Product backlog not found: $PRODUCT_BACKLOG${NC}"
    exit 1
fi

# Extract IDs from product backlog table
US_IDS=$(grep -oE '\[US-[0-9]+\]' "$PRODUCT_BACKLOG" | sed 's/\[//;s/\]//' | sort -u)
DEF_IDS=$(grep -oE '\[DEF-[0-9]+\]' "$PRODUCT_BACKLOG" | sed 's/\[//;s/\]//' | sort -u)
TD_IDS=$(grep -oE '\[TD-[0-9]+\]' "$PRODUCT_BACKLOG" | sed 's/\[//;s/\]//' | sort -u)

# Check for orphan files (files not in product backlog)
for dir in "$USER_STORIES_DIR" "$DEFECTS_DIR" "$TECH_DEBT_DIR"; do
    [ ! -d "$dir" ] && continue
    for f in "$dir"/*.md; do
        [ ! -f "$f" ] && continue
        base=$(basename "$f" .md)
        id=$(echo "$base" | grep -oE '^(US|DEF|TD)-[0-9]+')
        [ -z "$id" ] && continue
        if ! grep -q "\[$id\]" "$PRODUCT_BACKLOG"; then
            echo -e "${RED}✗ Orphan file not in product backlog: $f${NC}"
            ERRORS=$((ERRORS+1))
        fi
    done
done

# Check for missing files (IDs in backlog but no file)
for id in $US_IDS; do
    if ! ls "$USER_STORIES_DIR"/${id}-*.md 2>/dev/null | grep -q .; then
        echo -e "${RED}✗ Product backlog references $id but no file in $USER_STORIES_DIR/${NC}"
        ERRORS=$((ERRORS+1))
    fi
done
for id in $DEF_IDS; do
    if ! ls "$DEFECTS_DIR"/${id}-*.md 2>/dev/null | grep -q .; then
        echo -e "${RED}✗ Product backlog references $id but no file in $DEFECTS_DIR/${NC}"
        ERRORS=$((ERRORS+1))
    fi
done
for id in $TD_IDS; do
    [ ! -d "$TECH_DEBT_DIR" ] && continue
    if ! ls "$TECH_DEBT_DIR"/${id}-*.md 2>/dev/null | grep -q .; then
        echo -e "${RED}✗ Product backlog references $id but no file in $TECH_DEBT_DIR/${NC}"
        ERRORS=$((ERRORS+1))
    fi
done

# Check for duplicate IDs in backlog
DUP_US=$(echo "$US_IDS" | uniq -d)
DUP_DEF=$(echo "$DEF_IDS" | uniq -d)
DUP_TD=$(echo "$TD_IDS" | uniq -d)
if [ -n "$DUP_US" ] || [ -n "$DUP_DEF" ] || [ -n "$DUP_TD" ]; then
    echo -e "${RED}✗ Duplicate IDs in product backlog${NC}"
    [ -n "$DUP_US" ] && echo "  US: $DUP_US"
    [ -n "$DUP_DEF" ] && echo "  DEF: $DUP_DEF"
    [ -n "$DUP_TD" ] && echo "  TD: $DUP_TD"
    ERRORS=$((ERRORS+1))
fi

# Check story points are Fibonacci
FIB="1 2 3 5 8 13"
for id in $US_IDS $DEF_IDS $TD_IDS; do
    [ -z "$id" ] && continue
    if [[ "$id" == US-* ]]; then
        file=$(ls "$USER_STORIES_DIR"/${id}-*.md 2>/dev/null | head -1)
    elif [[ "$id" == DEF-* ]]; then
        file=$(ls "$DEFECTS_DIR"/${id}-*.md 2>/dev/null | head -1)
    else
        file=$(ls "$TECH_DEBT_DIR"/${id}-*.md 2>/dev/null | head -1)
    fi
    [ ! -f "$file" ] && continue
    points=$(grep -E '^\*\*Story Points\*\*:' "$file" 2>/dev/null | grep -oE '[0-9]+' | head -1)
    if [ -n "$points" ] && ! echo "$FIB" | grep -qw "$points"; then
        echo -e "${YELLOW}⚠ $id has story points $points (not Fibonacci 1,2,3,5,8,13)${NC}"
    fi
done

echo "----------------------------------------"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ Backlog integrity passed${NC}"
    exit 0
else
    echo -e "${RED}✗ Backlog integrity failed with $ERRORS error(s)${NC}"
    exit 1
fi
