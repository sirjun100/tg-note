-- Database schema for Telegram-Joplin Bot Logging
-- SQLite database for storing conversations, LLM interactions, and decisions

-- Telegram messages table
CREATE TABLE IF NOT EXISTS telegram_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message_text TEXT NOT NULL,
    response_text TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    message_type TEXT DEFAULT 'user'  -- 'user' or 'system'
);

-- LLM interactions table
CREATE TABLE IF NOT EXISTS llm_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    model TEXT NOT NULL,
    temperature REAL,
    max_tokens INTEGER,
    confidence_score REAL,
    processing_time REAL,  -- in seconds
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Decision logging table
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    telegram_message_id INTEGER,
    llm_interaction_id INTEGER,
    status TEXT NOT NULL,  -- 'SUCCESS', 'NEED_INFO', 'ERROR'
    folder_chosen TEXT,
    note_title TEXT,
    note_body TEXT,
    tags TEXT,  -- JSON array of tags
    joplin_note_id TEXT,
    error_message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (telegram_message_id) REFERENCES telegram_messages(id),
    FOREIGN KEY (llm_interaction_id) REFERENCES llm_interactions(id)
);

-- System logs table for debugging
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,  -- 'DEBUG', 'INFO', 'WARNING', 'ERROR'
    module TEXT NOT NULL,
    message TEXT NOT NULL,
    extra_data TEXT,  -- JSON for additional context
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_telegram_messages_user_id ON telegram_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_telegram_messages_timestamp ON telegram_messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_llm_interactions_timestamp ON llm_interactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_decisions_user_id ON decisions(user_id);
CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON decisions(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);

-- Retention view: messages older than 30 days
CREATE VIEW IF NOT EXISTS old_messages AS
SELECT id FROM telegram_messages
WHERE timestamp < datetime('now', '-30 days');

-- Retention view: interactions older than 30 days
CREATE VIEW IF NOT EXISTS old_interactions AS
SELECT id FROM llm_interactions
WHERE timestamp < datetime('now', '-30 days');

-- Retention view: decisions older than 30 days
CREATE VIEW IF NOT EXISTS old_decisions AS
SELECT id FROM decisions
WHERE timestamp < datetime('now', '-30 days');

-- Retention view: logs older than 30 days
CREATE VIEW IF NOT EXISTS old_logs AS
SELECT id FROM system_logs
WHERE timestamp < datetime('now', '-30 days');