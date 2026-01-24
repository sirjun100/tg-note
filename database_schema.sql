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

-- Google OAuth tokens table
CREATE TABLE IF NOT EXISTS google_tokens (
    user_id TEXT PRIMARY KEY,
    token_data TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Retention view: logs older than 30 days
CREATE VIEW IF NOT EXISTS old_logs AS
SELECT id FROM system_logs
WHERE timestamp < datetime('now', '-30 days');

-- Google Tasks Configuration table
CREATE TABLE IF NOT EXISTS google_tasks_config (
    user_id INTEGER PRIMARY KEY,
    enabled BOOLEAN DEFAULT TRUE,
    auto_create_tasks BOOLEAN DEFAULT TRUE,
    task_list_id TEXT,
    task_list_name TEXT,
    include_only_tagged BOOLEAN DEFAULT FALSE,
    task_creation_tags TEXT,  -- JSON array of tags that trigger task creation
    privacy_mode BOOLEAN DEFAULT FALSE,  -- If true, don't create tasks for sensitive notes
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Task links between Joplin notes and Google Tasks
CREATE TABLE IF NOT EXISTS task_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    joplin_note_id TEXT NOT NULL,
    google_task_id TEXT NOT NULL,
    google_task_list_id TEXT NOT NULL,
    joplin_note_title TEXT,
    google_task_title TEXT,
    synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_sync DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES google_tokens(user_id),
    UNIQUE(user_id, joplin_note_id, google_task_id)
);

-- Task synchronization history
CREATE TABLE IF NOT EXISTS task_sync_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    task_link_id INTEGER,
    google_task_id TEXT,
    action TEXT NOT NULL,  -- 'created', 'updated', 'completed', 'deleted'
    old_status TEXT,
    new_status TEXT,
    sync_direction TEXT,  -- 'joplin_to_google', 'google_to_joplin', 'manual'
    sync_result TEXT,  -- 'success', 'failed', 'partial'
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES google_tokens(user_id),
    FOREIGN KEY (task_link_id) REFERENCES task_links(id)
);

-- Indexes for task tables
CREATE INDEX IF NOT EXISTS idx_task_links_user_id ON task_links(user_id);
CREATE INDEX IF NOT EXISTS idx_task_links_joplin_note ON task_links(joplin_note_id);
CREATE INDEX IF NOT EXISTS idx_task_links_google_task ON task_links(google_task_id);
CREATE INDEX IF NOT EXISTS idx_task_sync_user_id ON task_sync_history(user_id);
CREATE INDEX IF NOT EXISTS idx_task_sync_timestamp ON task_sync_history(created_at);
CREATE INDEX IF NOT EXISTS idx_google_tasks_config_user ON google_tasks_config(user_id);

-- Tag creation history for audit trail
CREATE TABLE IF NOT EXISTS tag_creation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    joplin_note_id TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    is_new_tag BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);

-- Indexes for tag creation history
CREATE INDEX IF NOT EXISTS idx_tag_creation_user_date ON tag_creation_history(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_tag_creation_note ON tag_creation_history(joplin_note_id);
CREATE INDEX IF NOT EXISTS idx_tag_creation_is_new ON tag_creation_history(is_new_tag);