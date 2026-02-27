FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed (e.g., for building python packages)
# RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for data persistence
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOGS_DB_PATH=/app/data/bot_logs.db
ENV STATE_DB_PATH=/app/data/conversation_state.db

# Expose health check port (fly.io uses 8080)
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]
