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
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


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

    def log_telegram_message(self, message: TelegramMessage) -> int:
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

    def log_llm_interaction(self, interaction: LLMInteraction) -> int:
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

    def log_decision(self, decision: Decision) -> int:
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