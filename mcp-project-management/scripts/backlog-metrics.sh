#!/bin/bash
# Backlog Metrics Script
# Computes backlog health metrics: items by status, aging, velocity, cycle time, throughput.
# Supports aging thresholds per backlog-aging-standards.md.
# Run from project root.

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Aging thresholds (from backlog-aging-standards.md; override via env)
CRITICAL_DAYS="${BACKLOG_AGING_CRITICAL_DAYS:-3}"
HIGH_DAYS="${BACKLOG_AGING_HIGH_DAYS:-7}"
MEDIUM_DAYS="${BACKLOG_AGING_MEDIUM_DAYS:-14}"
LOW_DAYS="${BACKLOG_AGING_LOW_DAYS:-30}"
FAIL_CRITICAL="${BACKLOG_AGING_FAIL_CRITICAL:-0}"

# Parse args for --stats mode
STATS_MODE=0
BACKLOG_DIR=""
SPRINTS_DIR=""
for arg in "$@"; do
    case "$arg" in
        --stats|-s) STATS_MODE=1 ;;
        project-management/*) [ -z "$BACKLOG_DIR" ] && BACKLOG_DIR="$arg" || SPRINTS_DIR="$arg" ;;
    esac
done

# Default paths
BACKLOG_DIR="${BACKLOG_DIR:-project-management/backlog}"
PRODUCT_BACKLOG="${BACKLOG_DIR}/product-backlog.md"
SPRINTS_DIR="${SPRINTS_DIR:-project-management/sprints}"

# Run from project root
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$PROJECT_ROOT"

if [ ! -f "$PRODUCT_BACKLOG" ]; then
    echo "Product backlog not found: $PRODUCT_BACKLOG"
    exit 1
fi

if [ "$STATS_MODE" != "1" ]; then
    echo ""
    echo -e "${BLUE}=== Backlog Metrics ===${NC}"
    echo ""
fi

# Parse product backlog table rows (US-, DEF-, TD-)
# Exclude example/template sections
TABLE_ROWS=$(awk '/^## Example|^## Tips|^## Template|^## Status Values|^## Priority Levels|^## Notes|^## Backlog Statistics/ {exit} /\[(US|DEF|TD)-[0-9]+/ {print}' "$PRODUCT_BACKLOG" || true)

# Count by status and priority
NOT_STARTED=0
IN_PROGRESS=0
COMPLETED=0
CRITICAL_COUNT=0
HIGH_COUNT=0
MEDIUM_COUNT=0
LOW_COUNT=0
TOTAL_POINTS=0
COMPLETED_POINTS=0
AGING_ITEMS=""
AGING_ALERTS=""
CYCLE_TIMES=""

# Date parsing (macOS vs Linux)
date_epoch() {
    local d="$1"
    if date -j -f "%Y-%m-%d" "$d" +%s 2>/dev/null; then
        :
    else
        date -d "$d" +%s 2>/dev/null || echo "0"
    fi
}

TODAY=$(date +%Y-%m-%d)
TODAY_EPOCH=$(date_epoch "$TODAY")

while IFS= read -r line; do
    [ -z "$line" ] && continue
    STATUS=$(echo "$line" | grep -oE '(⭕|⏳|✅)' | head -1)
    POINTS=$(echo "$line" | grep -oE '\|\s*[0-9]+\s*\|' | tail -4 | head -1 | tr -d '| ' || echo "0")
    POINTS=${POINTS:-0}
    CREATED=$(echo "$line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | tail -2 | head -1)
    UPDATED=$(echo "$line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | tail -1)
    ID=$(echo "$line" | grep -oE '\[(US|DEF|TD)-[0-9]+\]' | head -1)

    # Priority (🔴 🟠 🟡 🟢)
    if echo "$line" | grep -q '🔴'; then
        PRIORITY="critical"
    elif echo "$line" | grep -q '🟠'; then
        PRIORITY="high"
    elif echo "$line" | grep -q '🟡'; then
        PRIORITY="medium"
    elif echo "$line" | grep -q '🟢'; then
        PRIORITY="low"
    else
        PRIORITY="medium"
    fi

    TOTAL_POINTS=$((TOTAL_POINTS + POINTS))

    # Count by priority
    case "$PRIORITY" in
        critical) CRITICAL_COUNT=$((CRITICAL_COUNT + 1)) ;;
        high)    HIGH_COUNT=$((HIGH_COUNT + 1)) ;;
        medium)  MEDIUM_COUNT=$((MEDIUM_COUNT + 1)) ;;
        low)     LOW_COUNT=$((LOW_COUNT + 1)) ;;
    esac

    case "$STATUS" in
        ⭕) NOT_STARTED=$((NOT_STARTED + 1))
            if [ -n "$CREATED" ]; then
                CREATED_EPOCH=$(date_epoch "$CREATED" 2>/dev/null || true)
                if [ -n "$CREATED_EPOCH" ]; then
                    DAYS=$(( (TODAY_EPOCH - CREATED_EPOCH) / 86400 ))
                    AGING_ITEMS="${AGING_ITEMS}${ID}: ${DAYS} days (${PRIORITY})
"
                    # Check thresholds
                    case "$PRIORITY" in
                        critical) [ "$DAYS" -gt "$CRITICAL_DAYS" ] && AGING_ALERTS="${AGING_ALERTS}${RED}ALERT${NC}: ${ID} Critical, ${DAYS} days (threshold: ${CRITICAL_DAYS})
" ;;
                        high)    [ "$DAYS" -gt "$HIGH_DAYS" ]    && AGING_ALERTS="${AGING_ALERTS}${YELLOW}ALERT${NC}: ${ID} High, ${DAYS} days (threshold: ${HIGH_DAYS})
" ;;
                        medium)  [ "$DAYS" -gt "$MEDIUM_DAYS" ]  && AGING_ALERTS="${AGING_ALERTS}${YELLOW}WARN${NC}: ${ID} Medium, ${DAYS} days (threshold: ${MEDIUM_DAYS})
" ;;
                        low)     [ "$DAYS" -gt "$LOW_DAYS" ]     && AGING_ALERTS="${AGING_ALERTS}Info: ${ID} Low, ${DAYS} days (threshold: ${LOW_DAYS})
" ;;
                    esac
                fi
            fi
            ;;
        ⏳) IN_PROGRESS=$((IN_PROGRESS + 1)) ;;
        ✅) COMPLETED=$((COMPLETED + 1))
            COMPLETED_POINTS=$((COMPLETED_POINTS + POINTS))
            if [ -n "$CREATED" ] && [ -n "$UPDATED" ]; then
                CREATED_EPOCH=$(date_epoch "$CREATED" 2>/dev/null || true)
                UPDATED_EPOCH=$(date_epoch "$UPDATED" 2>/dev/null || true)
                if [ -n "$CREATED_EPOCH" ] && [ -n "$UPDATED_EPOCH" ]; then
                    CYCLE_DAYS=$(( (UPDATED_EPOCH - CREATED_EPOCH) / 86400 ))
                    CYCLE_TIMES="${CYCLE_TIMES}${ID}: ${CYCLE_DAYS} days
"
                fi
            fi
            ;;
    esac
done <<< "$TABLE_ROWS"

# Fallback count if no rows parsed
if [ $NOT_STARTED -eq 0 ] && [ $IN_PROGRESS -eq 0 ] && [ $COMPLETED -eq 0 ]; then
    NOT_STARTED=$(grep -c "⭕" "$PRODUCT_BACKLOG" || echo "0")
    IN_PROGRESS=$(grep -c "⏳" "$PRODUCT_BACKLOG" || echo "0")
    COMPLETED=$(grep -c "✅" "$PRODUCT_BACKLOG" || echo "0")
fi

TOTAL=$((NOT_STARTED + IN_PROGRESS + COMPLETED))

# --stats mode: output markdown block for product-backlog.md
if [ "$STATS_MODE" = "1" ]; then
    echo "## Backlog Statistics"
    echo ""
    echo "**Total Items**: $TOTAL"
    echo "**By Status**:"
    echo "- ⭕ To Do: $NOT_STARTED"
    echo "- ⏳ In Progress: $IN_PROGRESS"
    echo "- ✅ Done: $COMPLETED"
    echo ""
    echo "**By Priority**:"
    echo "- 🔴 Critical: $CRITICAL_COUNT"
    echo "- 🟠 High: $HIGH_COUNT"
    echo "- 🟡 Medium: $MEDIUM_COUNT"
    echo "- 🟢 Low: $LOW_COUNT"
    echo ""
    echo "**Total Story Points**: $TOTAL_POINTS"
    exit 0
fi

echo -e "${GREEN}Items by Status${NC}"
echo "  Total: $TOTAL"
echo "  To Do: $NOT_STARTED"
echo "  In Progress: $IN_PROGRESS"
echo "  Done: $COMPLETED"
echo ""
echo -e "${GREEN}Story Points${NC}"
echo "  Total: $TOTAL_POINTS"
echo "  Completed: $COMPLETED_POINTS"
echo ""

# Aging (To Do items)
if [ -n "$AGING_ITEMS" ]; then
    echo -e "${GREEN}Aging (To Do items)${NC}"
    echo "$AGING_ITEMS" | while read -r item; do
        [ -z "$item" ] && continue
        echo "  $item"
    done
    echo ""
fi

# Aging alerts
if [ -n "$AGING_ALERTS" ]; then
    echo -e "${GREEN}Aging Thresholds${NC}"
    echo -e "$AGING_ALERTS" | while read -r item; do
        [ -z "$item" ] && continue
        echo "  $item"
    done
    echo ""
fi

# Cycle time (Done items)
if [ -n "$CYCLE_TIMES" ]; then
    echo -e "${GREEN}Cycle Time (Done items)${NC}"
    echo "$CYCLE_TIMES" | while read -r item; do
        [ -z "$item" ] && continue
        echo "  $item"
    done
    echo ""
fi

# Velocity and throughput from sprint files
if [ -d "$SPRINTS_DIR" ]; then
    LAST_SPRINT=$(ls -1 "$SPRINTS_DIR"/sprint-*.md 2>/dev/null | tail -1)
    if [ -n "$LAST_SPRINT" ]; then
        SPRINT_COMPLETED=$(grep -E "✅|Done" "$LAST_SPRINT" | grep -oE '[0-9]+ Points' | grep -oE '[0-9]+' | awk '{s+=$1} END {print s+0}')
        SPRINT_ITEMS=$(grep -cE '\[(US|DEF|TD)-[0-9]+\]' "$LAST_SPRINT" 2>/dev/null || echo "0")
        echo -e "${GREEN}Last Sprint${NC}"
        echo "  $(basename "$LAST_SPRINT" .md)"
        echo "  Done points: ${SPRINT_COMPLETED:-0}"
        echo "  Throughput (items): ${SPRINT_ITEMS:-0}"
        echo ""
    fi
fi

# Fail on Critical breach if configured
if [ "$FAIL_CRITICAL" = "1" ] && echo "$AGING_ALERTS" | grep -q "Critical"; then
    echo -e "${RED}Critical item(s) exceed aging threshold. Exiting with code 1.${NC}"
    exit 1
fi

echo -e "${BLUE}Tip: See project-management/processes/backlog-aging-standards.md for threshold config.${NC}"
echo ""
