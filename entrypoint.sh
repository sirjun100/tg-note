#!/bin/bash
set -e

JOPLIN_PROFILE="${JOPLIN_PROFILE:-/app/data/joplin}"
mkdir -p "$JOPLIN_PROFILE"

# Configure Joplin API on port 41184 (localhost only — bot is in the same container)
joplin config api.port 41184 --profile "$JOPLIN_PROFILE" 2>/dev/null || true

# Start Joplin server in background
joplin server start --profile "$JOPLIN_PROFILE" &

# Wait for the API to be ready (up to 30 seconds)
echo "Waiting for Joplin API on localhost:41184..."
for i in $(seq 1 30); do
    if python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:41184/ping', timeout=2)" 2>/dev/null; then
        echo "Joplin API ready"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "WARNING: Joplin API did not become ready in 30s, starting bot anyway"
    fi
    sleep 1
done

# Start the bot (replaces this shell process)
exec python main.py
