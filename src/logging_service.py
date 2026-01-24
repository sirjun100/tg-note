"""
Logging Service for Telegram-Joplin Bot

Provides SQLite database logging for:
- Telegram conversations
- LLM interactions
- Decision processes
- System debugging

Uses SQLite for simplicity and reliability.
"""

import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TelegramMessage:
    id: Optional[int] = None
    user_id: int = 0
    message_text: str = ""
    response_text: Optional[str] = None
    timestamp: Optional[datetime] = None
    message_type: str = "user"


@dataclass
class LLMInteraction:
    id: Optional[int] = None
    prompt: str = ""
    response: str = ""
    model: str = ""
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None
    timestamp: Optional[datetime] = None


@dataclass
class Decision:
    id: Optional[int] = None
    user_id: int = 0
    telegram_message_id: Optional[int] = None
    llm_interaction_id: Optional[int] = None
    status: str = ""
    folder_chosen: Optional[str] = None
    note_title: Optional[str] = None
    note_body: Optional[str] = None
    tags: Optional[List[str]] = None
    joplin_note_id: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None


class LoggingService:
    def __init__(self, db_path: str = "bot_logs.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database with schema"""
        with sqlite3.connect(self.db_path) as conn:
            with open('database_schema.sql', 'r') as f:
                schema = f.read()
            conn.executescript(schema)
            conn.commit()

    def _dict_factory(self, cursor, row):
        """Convert row to dict"""
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def log_telegram_message(self, message: TelegramMessage) -> Optional[int]:
        """Log a Telegram message"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO telegram_messages (user_id, message_text, response_text, message_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                message.user_id,
                message.message_text,
                message.response_text,
                message.message_type,
                message.timestamp or datetime.now()
            ))
            conn.commit()
            return cursor.lastrowid

    def log_llm_interaction(self, interaction: LLMInteraction) -> Optional[int]:
        """Log an LLM interaction"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO llm_interactions (prompt, response, model, temperature, max_tokens, confidence_score, processing_time, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                interaction.prompt,
                interaction.response,
                interaction.model,
                interaction.temperature,
                interaction.max_tokens,
                interaction.confidence_score,
                interaction.processing_time,
                interaction.timestamp or datetime.now()
            ))
            conn.commit()
            return cursor.lastrowid

    def log_decision(self, decision: Decision) -> Optional[int]:
        """Log a decision process"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO decisions (user_id, telegram_message_id, llm_interaction_id, status, folder_chosen, note_title, note_body, tags, joplin_note_id, error_message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                decision.user_id,
                decision.telegram_message_id,
                decision.llm_interaction_id,
                decision.status,
                decision.folder_chosen,
                decision.note_title,
                decision.note_body,
                json.dumps(decision.tags) if decision.tags else None,
                decision.joplin_note_id,
                decision.error_message,
                decision.timestamp or datetime.now()
            ))
            conn.commit()
            return cursor.lastrowid

    def log_system_event(self, level: str, module: str, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log a system event"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO system_logs (level, module, message, extra_data, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                level,
                module,
                message,
                json.dumps(extra_data) if extra_data else None,
                datetime.now()
            ))
            conn.commit()

    def get_recent_messages(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM telegram_messages
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (user_id, limit))
            return cursor.fetchall()

    def get_decisions_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get decisions by status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM decisions
                WHERE status = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (status, limit))
            return cursor.fetchall()

    def get_llm_interactions_by_model(self, model: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get LLM interactions by model"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM llm_interactions
                WHERE model = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (model, limit))
            return cursor.fetchall()

    def cleanup_old_data(self, days: int = 30):
        """Clean up data older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Delete old messages
            cursor.execute('DELETE FROM telegram_messages WHERE timestamp < ?', (cutoff_date,))
            deleted_messages = cursor.rowcount

            # Delete old interactions
            cursor.execute('DELETE FROM llm_interactions WHERE timestamp < ?', (cutoff_date,))
            deleted_interactions = cursor.rowcount

            # Delete old decisions
            cursor.execute('DELETE FROM decisions WHERE timestamp < ?', (cutoff_date,))
            deleted_decisions = cursor.rowcount

            # Delete old logs
            cursor.execute('DELETE FROM system_logs WHERE timestamp < ?', (cutoff_date,))
            deleted_logs = cursor.rowcount

            conn.commit()

            self.log_system_event('INFO', 'cleanup', f'Cleaned up old data: {deleted_messages} messages, {deleted_interactions} interactions, {deleted_decisions} decisions, {deleted_logs} logs')

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            stats = {}
            tables = ['telegram_messages', 'llm_interactions', 'decisions', 'system_logs']

            for table in tables:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                stats[table] = cursor.fetchone()[0]

            return stats

    def save_google_token(self, user_id: str, token: Dict[str, Any]):
        """Save Google OAuth token for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO google_tokens (user_id, token_data, updated_at)
                VALUES (?, ?, ?)
            ''', (
                user_id,
                json.dumps(token),
                datetime.now()
            ))
            conn.commit()

    def load_google_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Load Google OAuth token for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute('''
                SELECT token_data FROM google_tokens
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
            ''', (user_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row['token_data'])
            return None

    def delete_google_token(self, user_id: str):
        """Delete Google OAuth token for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM google_tokens WHERE user_id = ?', (user_id,))
            conn.commit()

    # Google Tasks Configuration Methods

    def save_google_tasks_config(self, user_id: int, config: Dict[str, Any]):
        """Save Google Tasks configuration for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO google_tasks_config
                (user_id, enabled, auto_create_tasks, task_list_id, task_list_name,
                 include_only_tagged, task_creation_tags, privacy_mode, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                config.get('enabled', True),
                config.get('auto_create_tasks', True),
                config.get('task_list_id'),
                config.get('task_list_name'),
                config.get('include_only_tagged', False),
                json.dumps(config.get('task_creation_tags', [])),
                config.get('privacy_mode', False),
                datetime.now()
            ))
            conn.commit()

    def get_google_tasks_config(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get Google Tasks configuration for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM google_tasks_config WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                row['task_creation_tags'] = json.loads(row.get('task_creation_tags', '[]'))
                return row
            return None

    def delete_google_tasks_config(self, user_id: int):
        """Delete Google Tasks configuration for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM google_tasks_config WHERE user_id = ?', (user_id,))
            conn.commit()

    # Task Link Methods

    def create_task_link(self, user_id: int, joplin_note_id: str, google_task_id: str,
                        google_task_list_id: str, joplin_note_title: str,
                        google_task_title: str) -> Optional[int]:
        """Create a link between a Joplin note and Google Task"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO task_links
                    (user_id, joplin_note_id, google_task_id, google_task_list_id,
                     joplin_note_title, google_task_title)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, joplin_note_id, google_task_id, google_task_list_id,
                      joplin_note_title, google_task_title))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # Link already exists
                return None

    def get_task_link(self, user_id: int, joplin_note_id: str) -> Optional[Dict[str, Any]]:
        """Get task link for a Joplin note"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM task_links
                WHERE user_id = ? AND joplin_note_id = ?
            ''', (user_id, joplin_note_id))
            return cursor.fetchone()

    def get_all_task_links(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all task links for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM task_links
                WHERE user_id = ?
                ORDER BY synced_at DESC
            ''', (user_id,))
            return cursor.fetchall()

    def update_task_link_sync(self, task_link_id: int, new_sync_time: datetime = None):
        """Update last sync time for a task link"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            sync_time = new_sync_time or datetime.now()
            cursor.execute('''
                UPDATE task_links
                SET last_sync = ?
                WHERE id = ?
            ''', (sync_time, task_link_id))
            conn.commit()

    def delete_task_link(self, task_link_id: int):
        """Delete a task link"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM task_links WHERE id = ?', (task_link_id,))
            conn.commit()

    # Task Sync History Methods

    def log_task_sync(self, user_id: int, task_link_id: Optional[int], google_task_id: str,
                     action: str, old_status: Optional[str], new_status: Optional[str],
                     sync_direction: str, sync_result: str, error_message: Optional[str] = None):
        """Log a task synchronization event"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO task_sync_history
                (user_id, task_link_id, google_task_id, action, old_status, new_status,
                 sync_direction, sync_result, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, task_link_id, google_task_id, action, old_status, new_status,
                  sync_direction, sync_result, error_message))
            conn.commit()

    def get_sync_history(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get task synchronization history for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM task_sync_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            return cursor.fetchall()

    def get_failed_syncs(self, user_id: int) -> List[Dict[str, Any]]:
        """Get failed task synchronization attempts"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM task_sync_history
                WHERE user_id = ? AND sync_result = 'failed'
                ORDER BY created_at DESC
            ''', (user_id,))
            return cursor.fetchall()

    def log_tag_creation(self, user_id: int, note_id: str, tag_name: str, is_new: bool = False):
        """Log tag creation or application to database for audit trail

        Args:
            user_id: Telegram user ID
            note_id: Joplin note ID the tag was applied to
            tag_name: Name of the tag
            is_new: True if tag was newly created, False if it was existing
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO tag_creation_history
                    (user_id, joplin_note_id, tag_name, is_new_tag, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, note_id, tag_name, is_new))
                conn.commit()
                logger.debug(f"Logged tag creation: user={user_id}, note={note_id}, tag={tag_name}, is_new={is_new}")
        except Exception as e:
            logger.error(f"Failed to log tag creation: {e}")