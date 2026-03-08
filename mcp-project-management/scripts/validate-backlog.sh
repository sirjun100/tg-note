#!/bin/bash
# Backlog Validation Script
# Validates backlog structure, file naming, and cross-references

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default paths (can be overridden) - run from project root
BACKLOG_DIR="${1:-project-management/backlog}"
USER_STORIES_DIR="${BACKLOG_DIR}/user-stories"
DEFECTS_DIR="${BACKLOG_DIR}/defects"
TECH_DEBT_DIR="${BACKLOG_DIR}/technical-debt"
RETROSPECTIVE_IMPROVEMENTS_DIR="${BACKLOG_DIR}/retrospective-improvements"
PRODUCT_BACKLOG="${BACKLOG_DIR}/product-backlog.md"

echo "Validating backlog structure..."
echo "----------------------------------------"

ERRORS=0
WARNINGS=0

# Check if directories exist
if [ ! -d "$BACKLOG_DIR" ]; then
    echo -e "${RED}✗ Backlog directory not found: $BACKLOG_DIR${NC}"
    echo "  Create it with: mkdir -p $BACKLOG_DIR/{user-stories,defects}"
    ((ERRORS++))
    exit 1
fi

if [ ! -d "$USER_STORIES_DIR" ]; then
    echo -e "${YELLOW}⚠ User stories directory not found: $USER_STORIES_DIR${NC}"
    ((WARNINGS++))
fi

if [ ! -d "$DEFECTS_DIR" ]; then
    echo -e "${YELLOW}⚠ Defects directory not found: $DEFECTS_DIR${NC}"
    ((WARNINGS++))
fi

if [ ! -d "$TECH_DEBT_DIR" ]; then
    echo -e "${YELLOW}⚠ Technical debt directory not found: $TECH_DEBT_DIR${NC}"
    ((WARNINGS++))
fi

if [ ! -d "$RETROSPECTIVE_IMPROVEMENTS_DIR" ]; then
    echo -e "${YELLOW}⚠ Retrospective improvements directory not found: $RETROSPECTIVE_IMPROVEMENTS_DIR${NC}"
    ((WARNINGS++))
fi

# Check for product backlog file
if [ ! -f "$PRODUCT_BACKLOG" ]; then
    echo -e "${YELLOW}⚠ Product backlog file not found: $PRODUCT_BACKLOG${NC}"
    ((WARNINGS++))
else
    echo -e "${GREEN}✓ Product backlog file found${NC}"
fi

# Validate file naming conventions
echo ""
echo "Checking file naming conventions..."

# Check user story files
if [ -d "$USER_STORIES_DIR" ]; then
    USER_STORY_FILES=$(find "$USER_STORIES_DIR" -name "*.md" 2>/dev/null || true)
    USER_STORY_COUNT=$(echo "$USER_STORY_FILES" | grep -v "^$" | wc -l || echo "0")
    
    if [ "$USER_STORY_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $USER_STORY_COUNT user story file(s)${NC}"
        
        # Check naming pattern (US-XXX-*.md)
        INVALID_NAMES=$(echo "$USER_STORY_FILES" | grep -v "US-[0-9]\+-" || true)
        if [ -n "$INVALID_NAMES" ]; then
            echo -e "${YELLOW}⚠ Some user story files don't follow US-XXX-name.md pattern:${NC}"
            echo "$INVALID_NAMES" | while read -r file; do
                echo "  - $file"
            done
            ((WARNINGS++))
        fi
    else
        echo -e "${YELLOW}⚠ No user story files found${NC}"
    fi
fi

# Check defect files
if [ -d "$DEFECTS_DIR" ]; then
    DEFECT_FILES=$(find "$DEFECTS_DIR" -name "*.md" 2>/dev/null || true)
    DEFECT_COUNT=$(echo "$DEFECT_FILES" | grep -v "^$" | wc -l || echo "0")
    
    if [ "$DEFECT_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $DEFECT_COUNT defect file(s)${NC}"
        
        # Check naming pattern (DEF-XXX-*.md)
        INVALID_NAMES=$(echo "$DEFECT_FILES" | grep -v "DEF-[0-9]\+-" || true)
        if [ -n "$INVALID_NAMES" ]; then
            echo -e "${YELLOW}⚠ Some defect files don't follow DEF-XXX-name.md pattern:${NC}"
            echo "$INVALID_NAMES" | while read -r file; do
                echo "  - $file"
            done
            ((WARNINGS++))
        fi
    else
        echo -e "${YELLOW}⚠ No defect files found${NC}"
    fi
fi

# Check technical debt files
if [ -d "$TECH_DEBT_DIR" ]; then
    TD_FILES=$(find "$TECH_DEBT_DIR" -name "*.md" 2>/dev/null || true)
    TD_COUNT=$(echo "$TD_FILES" | grep -v "^$" | wc -l 2>/dev/null | tr -d ' ' || echo "0")
    TD_COUNT=${TD_COUNT:-0}
    if [ "$TD_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $TD_COUNT technical debt file(s)${NC}"
        INVALID_NAMES=$(echo "$TD_FILES" | grep -v "TD-[0-9]\+-" || true)
        if [ -n "$INVALID_NAMES" ]; then
            echo -e "${YELLOW}⚠ Some technical debt files don't follow TD-XXX-name.md pattern:${NC}"
            echo "$INVALID_NAMES" | while read -r file; do
                echo "  - $file"
            done
            ((WARNINGS++))
        fi
    else
        echo -e "${GREEN}✓ Technical debt directory present (empty)${NC}"
    fi
fi

# Check retrospective improvement files (RI-XXX)
if [ -d "$RETROSPECTIVE_IMPROVEMENTS_DIR" ]; then
    RI_FILES=$(find "$RETROSPECTIVE_IMPROVEMENTS_DIR" -name "*.md" 2>/dev/null || true)
    RI_COUNT=$(echo "$RI_FILES" | grep -v "^$" | wc -l 2>/dev/null | tr -d ' ' || echo "0")
    RI_COUNT=${RI_COUNT:-0}
    if [ "$RI_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $RI_COUNT retrospective improvement file(s)${NC}"
        INVALID_NAMES=$(echo "$RI_FILES" | grep -v "RI-[0-9]\+-" || true)
        if [ -n "$INVALID_NAMES" ]; then
            echo -e "${YELLOW}⚠ Some retrospective improvement files don't follow RI-XXX-name.md pattern:${NC}"
            echo "$INVALID_NAMES" | while read -r file; do
                echo "  - $file"
            done
            ((WARNINGS++))
        fi
    else
        echo -e "${GREEN}✓ Retrospective improvements directory present (empty)${NC}"
    fi
fi

# Validate product backlog table
if [ -f "$PRODUCT_BACKLOG" ]; then
    echo ""
    echo "Checking product backlog table..."
    
    # Check for table structure
    if grep -q "| ID |" "$PRODUCT_BACKLOG"; then
        echo -e "${GREEN}✓ Product backlog table structure found${NC}"
    else
        echo -e "${YELLOW}⚠ Product backlog table structure may be missing${NC}"
        ((WARNINGS++))
    fi
    
    # Count entries
    FEATURE_ENTRIES=$(grep -c "\[US-" "$PRODUCT_BACKLOG" || echo "0")
    DEFECT_ENTRIES=$(grep -c "\[DEF-" "$PRODUCT_BACKLOG" || echo "0")
    TD_ENTRIES=$(grep -c "\[TD-" "$PRODUCT_BACKLOG" || echo "0")
    
    echo -e "${GREEN}✓ Found $FEATURE_ENTRIES user story entries${NC}"
    echo -e "${GREEN}✓ Found $DEFECT_ENTRIES defect entries${NC}"
    echo -e "${GREEN}✓ Found $TD_ENTRIES technical debt entries${NC}"
    
fi

# Run link checker (validates all project-management/ markdown by default)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CHECK_LINKS="$SCRIPT_DIR/check-links.sh"
PM_DIR="$(dirname "$BACKLOG_DIR")"
if [ -f "$CHECK_LINKS" ] && [ -d "$PROJECT_ROOT/$PM_DIR" ]; then
    echo ""
    (cd "$PROJECT_ROOT" && "$CHECK_LINKS" "$PM_DIR" ".") || ((ERRORS++))
fi

# Summary
echo ""
echo "----------------------------------------"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ Backlog validation passed!${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Backlog validation passed with $WARNINGS warning(s)${NC}"
    exit 0
else
    echo -e "${RED}✗ Backlog validation failed with $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    exit 1
fi
