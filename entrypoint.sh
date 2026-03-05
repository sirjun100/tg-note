#!/bin/bash
set -e

JOPLIN_PROFILE="${JOPLIN_PROFILE:-/app/data/joplin}"

# Ensure all data directories exist (volume mount overrides Dockerfile mkdir)
mkdir -p "$JOPLIN_PROFILE"
mkdir -p /app/data/bot

# Configure Joplin API on port 41184 (localhost only — bot is in the same container)
joplin --profile "$JOPLIN_PROFILE" config api.port 41184 2>/dev/null || true
# Pin Joplin API token to the injected secret so it stays stable across restarts.
if [ -n "${JOPLIN_WEB_CLIPPER_TOKEN:-}" ]; then
    joplin --profile "$JOPLIN_PROFILE" config api.token "$JOPLIN_WEB_CLIPPER_TOKEN" 2>/dev/null || true
fi

# Start Joplin server in background (redirect output to avoid logging API token in request URLs)
joplin --profile "$JOPLIN_PROFILE" server start >/dev/null 2>&1 &

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

# Validate token alignment between Joplin profile and bot env.
# This prevents silent auth failures when one value is rotated without the other.
joplin_token="$(joplin --profile "$JOPLIN_PROFILE" config api.token 2>/dev/null | awk -F'= ' '/api.token/ {print $2}' | tr -d '\r\n')"
env_token="${JOPLIN_WEB_CLIPPER_TOKEN:-}"

if [ -z "$env_token" ]; then
    echo "WARNING: JOPLIN_WEB_CLIPPER_TOKEN is empty; Joplin API calls will fail."
elif [ -z "$joplin_token" ]; then
    echo "WARNING: Could not read api.token from Joplin profile; token mismatch checks skipped."
elif [ "$env_token" != "$joplin_token" ]; then
    echo "WARNING: Joplin token mismatch detected."
    echo "WARNING: env token starts with '${env_token:0:8}', profile token starts with '${joplin_token:0:8}'."
    echo "WARNING: Update Fly secret JOPLIN_WEB_CLIPPER_TOKEN to match 'joplin config api.token'."
fi

# Start the bot (replaces this shell process)
exec python main.py
