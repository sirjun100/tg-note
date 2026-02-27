#!/bin/bash
# Intelligent Joplin Librarian — Setup Script
# Creates a venv, installs deps, and sets up .env from template.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()     { echo -e "${RED}[ERR]${NC} $1"; }

echo "🤖 Intelligent Joplin Librarian — Setup"
echo "========================================"

# 1. Python check
if ! command -v python3 &>/dev/null; then
    err "Python 3 not found. Install Python 3.10+."
    exit 1
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
info "Python $PY_VER found"

# 2. Virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    info "Created virtual environment"
else
    warn "venv/ already exists — reusing"
fi
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip -q
pip install -r requirements.txt -q
info "Runtime dependencies installed"

if [ -f "requirements-dev.txt" ]; then
    pip install -r requirements-dev.txt -q
    info "Dev dependencies installed"
fi

# 4. Environment file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        info "Created .env from .env.example — edit it with your keys"
    else
        warn ".env.example not found — create .env manually"
    fi
else
    info ".env already exists"
fi

echo
echo "=========================================="
echo "  Setup complete!"
echo "=========================================="
echo
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Start Joplin with Web Clipper enabled"
echo "  3. source venv/bin/activate"
echo "  4. python main.py"
echo
