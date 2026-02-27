"""
Backward-compatible config shim.

Existing modules that `from config import X` will continue to work.
All values are now sourced from pydantic-settings (src.settings).

This file will be removed once all modules are migrated.
"""

from src.settings import get_settings as _get_settings

_s = _get_settings()

# Telegram
TELEGRAM_BOT_TOKEN = _s.telegram.bot_token
ALLOWED_TELEGRAM_USER_IDS = _s.telegram.allowed_user_ids.split(",")

# OpenAI
OPENAI_API_KEY = _s.llm.openai_api_key

# Ollama
OLLAMA_BASE_URL = _s.llm.ollama_base_url
OLLAMA_MODEL = _s.llm.ollama_model

# DeepSeek
DEEPSEEK_API_KEY = _s.llm.deepseek_api_key
DEEPSEEK_MODEL = _s.llm.deepseek_model

# LLM Provider
LLM_PROVIDER = _s.llm.provider

# Joplin
JOPLIN_WEB_CLIPPER_HOST = _s.joplin.host
JOPLIN_WEB_CLIPPER_PORT = _s.joplin.port
JOPLIN_WEB_CLIPPER_TOKEN = _s.joplin.token
JOPLIN_WEB_CLIPPER_BASE_URL = _s.joplin.base_url

# Application
DEBUG = _s.debug

# Database
LOGS_DB_PATH = _s.database.logs_db_path
STATE_DB_PATH = _s.database.state_db_path
