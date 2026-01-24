# Configuration file for Intelligent Joplin Librarian

# Load environment variables
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ALLOWED_TELEGRAM_USER_IDS = os.getenv('ALLOWED_TELEGRAM_USER_IDS', '').split(',')

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama2')

# DeepSeek Configuration
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')

# LLM Provider Selection
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'deepseek')  # Default to DeepSeek

# Joplin Configuration
JOPLIN_WEB_CLIPPER_PORT = int(os.getenv('JOPLIN_WEB_CLIPPER_PORT', 41184))
JOPLIN_WEB_CLIPPER_TOKEN = os.getenv('JOPLIN_WEB_CLIPPER_TOKEN')

# Application Settings
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'