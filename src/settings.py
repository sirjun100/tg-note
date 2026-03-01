"""
Application settings using pydantic-settings.

Validates all configuration at startup with clear error messages.
Replaces the old config.py module.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_CONFIG = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore",
)


class TelegramSettings(BaseSettings):
    model_config = _ENV_CONFIG

    bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    allowed_user_ids: str = Field(default="", alias="ALLOWED_TELEGRAM_USER_IDS")

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @property
    def allowed_ids(self) -> List[int]:
        ids: List[int] = []
        for raw in self.allowed_user_ids.split(","):
            raw = raw.strip()
            if raw.isdigit():
                ids.append(int(raw))
        return ids


class JoplinSettings(BaseSettings):
    model_config = _ENV_CONFIG

    host: str = Field(default="localhost", alias="JOPLIN_WEB_CLIPPER_HOST")
    port: int = Field(default=41184, alias="JOPLIN_WEB_CLIPPER_PORT")
    token: Optional[str] = Field(default=None, alias="JOPLIN_WEB_CLIPPER_TOKEN")
    base_url: Optional[str] = Field(default=None, alias="JOPLIN_WEB_CLIPPER_BASE_URL")

    @property
    def url(self) -> str:
        if self.base_url:
            return self.base_url.rstrip("/")
        return f"http://{self.host}:{self.port}"


class LLMSettings(BaseSettings):
    model_config = _ENV_CONFIG

    provider: str = Field(default="deepseek", alias="LLM_PROVIDER")

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama2", alias="OLLAMA_MODEL")

    deepseek_api_key: Optional[str] = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")


class GoogleSettings(BaseSettings):
    model_config = _ENV_CONFIG

    client_id: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_ID")
    client_secret: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    redirect_uri: str = Field(
        default="urn:ietf:wg:oauth:2.0:oob",
        alias="GOOGLE_REDIRECT_URI",
    )
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)


class DatabaseSettings(BaseSettings):
    model_config = _ENV_CONFIG

    logs_db_path: str = Field(default="data/bot/bot_logs.db", alias="LOGS_DB_PATH")
    state_db_path: str = Field(default="data/bot/conversation_state.db", alias="STATE_DB_PATH")


class AppSettings(BaseSettings):
    """Root settings object — aggregates all subsections."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    debug: bool = Field(default=False, alias="DEBUG")

    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    joplin: JoplinSettings = Field(default_factory=JoplinSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    google: GoogleSettings = Field(default_factory=GoogleSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)


@lru_cache()
def get_settings() -> AppSettings:
    """Return a cached singleton of the application settings."""
    return AppSettings()
