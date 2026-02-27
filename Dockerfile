FROM python:3.11-slim

# Install Node.js 18 (for Joplin CLI) and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates make g++ socat \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Joplin CLI globally
RUN npm install -g joplin

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/bot /app/data/joplin

ENV PYTHONUNBUFFERED=1
ENV LOGS_DB_PATH=/app/data/bot/bot_logs.db
ENV STATE_DB_PATH=/app/data/bot/conversation_state.db
ENV JOPLIN_PROFILE=/app/data/joplin

EXPOSE 8080

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
