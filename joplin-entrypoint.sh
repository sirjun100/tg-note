#!/bin/bash
# Set an internal port for Joplin to avoid conflict with socat on 0.0.0.0:41184
# Default is 41184. We'll move it to 41185.
joplin config api.port 41185 --profile /root/.config/joplin

# Start Joplin server in the background
joplin server start --profile /root/.config/joplin &

# Wait for the server to start
echo "Waiting for Joplin API to start on port 41185..."
sleep 5

# Use socat to forward traffic from 0.0.0.0:41184 to 127.0.0.1:41185
echo "Starting socat bridge from 0.0.0.0:41184 to 127.0.0.1:41185..."
socat TCP-LISTEN:41184,fork,reuseaddr TCP:127.0.0.1:41185
