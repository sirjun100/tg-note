# Intelligent Joplin Librarian

A Telegram bot that intelligently creates notes in Joplin using AI.

## Quick Setup

### Automated Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd telegram-joplin
   ```

2. **Run the automated setup**
   ```bash
   ./setup.sh
   ```

    This will:
    - Create a Python virtual environment
    - Install all required dependencies
    - Set up configuration files
    - Create helper scripts (including start.sh for easy launching)

3. **Configure your API keys**
   The setup script creates a `.env` file pre-configured for DeepSeek. Edit it with your credentials:
   ```bash
   # Edit the created .env file with your actual keys:
   # - DEEPSEEK_API_KEY (get from https://platform.deepseek.com/)
   # - TELEGRAM_BOT_TOKEN (get from @BotFather)
   # - ALLOWED_TELEGRAM_USER_IDS (your Telegram user ID)
   ```
   Or copy the example: `cp .env.example .env`

4. **Start Joplin**
   Make sure Joplin is running with Web Clipper enabled (default port 41184)

5. **Test the setup** (optional but recommended)
   ```bash
   source activate.sh  # Activate virtual environment
   python test_setup.py
   ```

6. **Run the bot**
    ```bash
    ./start.sh
    ```

    Or manually:
    ```bash
    source activate.sh
    python main.py
    ```

### Manual Setup

If you prefer manual setup:

1. **Install Python 3.8+**
2. **Clone this repository**
3. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Run setup**: `python setup_env.py`
5. **Configure `.env` file**
   ```bash
   cp .env.example .env
   # Edit .env with your DeepSeek API key and Telegram credentials
   ```
6. **Start Joplin with Web Clipper**
7. **Test setup**: `python test_setup.py`
8. **Run the bot**: `python main.py`

## Features

- 🤖 **AI-powered note creation** from natural language
- 📝 **Automatic categorization** and tagging
- 💬 **Interactive clarification** when needed
- 🔒 **Secure whitelist-based access** control
- 📚 **Integration with Joplin's folder structure**
- 📊 **Decision logging** for transparency
- 🛠️ **Easy setup** with automated scripts
- 🐍 **Python virtual environment** support
- 🧠 **Multiple LLM support** (OpenAI, Ollama, DeepSeek)
- 🔄 **Provider abstraction** for easy extension

## Requirements

- **Python 3.8+**
- **Joplin** with Web Clipper enabled (default port 41184)
- **Telegram Bot API token** (get from @BotFather)
- **LLM Provider**: Choose one:
  - **OpenAI API key** (for GPT models)
  - **Ollama** running locally (for local models)
  - **DeepSeek API key** (for DeepSeek models)

## Joplin Setup

**CRITICAL**: You must configure Joplin Web Clipper authentication:

1. **Open Joplin** desktop application
2. **Navigate to** `Tools → Options → Web Clipper`
3. **Generate** or set an authorization token
4. **Copy the token** to your `.env` file:
   ```bash
   JOPLIN_WEB_CLIPPER_TOKEN=your_generated_token_here
   ```

**Important**: Joplin uses the token as a query parameter (`?token=...`), not an Authorization header. Without this token, all API requests will fail with **403 Forbidden** errors.

## Architecture

- **Telegram Orchestrator**: Main bot logic and conversation handling
- **LLM Orchestrator**: AI processing with structured outputs using Pydantic
- **LLM Providers**: Abstraction layer supporting OpenAI, Ollama, and DeepSeek
- **Joplin Client**: REST API integration for notes and tags
- **State Manager**: SQLite-based conversation persistence
- **Security Utils**: Access control and comprehensive error handling

## Project Structure

```
telegram-joplin/
├── src/                          # Source code
│   ├── joplin_client.py         # Joplin API client
│   ├── llm_orchestrator.py      # AI processing
│   ├── state_manager.py         # Conversation state
│   ├── security_utils.py        # Security & validation
│   └── telegram_orchestrator.py # Main bot logic
├── project-management/          # Project management docs
├── requirements.txt             # Python dependencies
├── setup.sh                     # Automated setup script
├── setup_env.py                # Python setup script
├── config.py                    # Configuration management
├── main.py                      # Application entry point
└── README.md                    # This file
```

## Development

See the `project-management/` directory for sprint planning and backlog management.