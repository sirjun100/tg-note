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

    source activate.sh
    python main.py
    ```

## Docker Setup

### Prerequisites
- Docker and Docker Compose installed

### Running with Docker

1. **Configure Environment**
   Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

2. **Build and Run**
   ```bash
   docker-compose up -d --build
   ```

3. **View Logs**
   ```bash
   docker-compose logs -f
   ```

4. **Stop the Container**
   ```bash
   docker-compose down
   ```

### Data Persistence
The Docker container is configured to persist data in the `./data` directory. This includes:
- `bot_logs.db`: Database for logs, decisions, and Google Tasks tokens.
- `conversation_state.db`: Database for user conversation states.

Ensure you do not delete the `./data` directory if you want to keep your bot's history and authorization.

## Synology / Headless Deployment

If you want to run the bot 24/7 on a Synology NAS or any remote server, you can use the built-in Joplin CLI service to handle synchronization with Dropbox.

### Running Headless

1.  **Start Services**
    ```bash
    docker-compose up -d --build
    ```

2.  **Authorize Dropbox (One-time setup)**
    Run the following command to link your Dropbox account:
    ```bash
    docker exec -it joplin-cli joplin config sync.target 7
    docker exec -it joplin-cli joplin sync
    ```
    Follow the URL provided in the terminal, authorize on Dropbox, and paste the code back into the terminal.

3.  **Configure API Token**
    Once syncing is working, you need to get the API token from the headless Joplin instance:
    ```bash
    docker exec -it joplin-cli joplin server stop # Required to edit config
    # The token is usually generated automatically or can be set
    docker exec -it joplin-cli joplin server start
    ```
    Alternatively, check the logs or the `joplin-data` folder for the token and update your `.env` file's `JOPLIN_WEB_CLIPPER_TOKEN`.

4.  **Restart**
    ```bash
    docker-compose restart telegram-joplin
    ```

## Fly.io Deployment

Deploy the bot and Joplin to [Fly.io](https://fly.io) for a fully cloud-hosted setup. Both apps run in the same organization and communicate via Fly's private network (`*.internal`).

### Prerequisites

- [flyctl](https://fly.io/docs/hands-on/install-flyctl/) installed and logged in (`fly auth login`)
- A Fly.io account

### 1. Deploy Joplin First

Create the Joplin app, add a volume, then deploy:

```bash
fly launch -c fly.joplin.toml --no-deploy
fly volumes create joplin_data --region lax --size 1 -a joplin
fly deploy -c fly.joplin.toml
```

### 2. Create Bot App and Volume

```bash
fly launch --no-deploy
fly volumes create telegram_joplin_data --region lax --size 1 -a telegram-joplin
```

Use the same region (e.g. `lax`, `iad`, `ams`) for both apps so they can communicate via Fly's private network. Edit `primary_region` in both `fly.toml` and `fly.joplin.toml` if you use a different region.

### 3. One-Time Joplin Setup (Sync & Token)

Configure sync (e.g. Dropbox) and get the Web Clipper token:

```bash
# Connect to Joplin container
fly ssh console -a joplin

# Configure sync (example: Dropbox)
joplin config sync.target 7
joplin sync
# Follow the URL, authorize, paste the code back

# Get the API token for the bot
joplin config api.token
# Copy the token - you'll set it as a secret for telegram-joplin

exit
```

### 4. Set Secrets

```bash
fly secrets set \
  TELEGRAM_BOT_TOKEN=your_bot_token \
  ALLOWED_TELEGRAM_USER_IDS=your_telegram_user_id \
  DEEPSEEK_API_KEY=your_deepseek_key \
  JOPLIN_WEB_CLIPPER_TOKEN=your_joplin_token \
  -a telegram-joplin
```

### 5. Deploy

```bash
fly deploy -a telegram-joplin
```

### 6. Optional: Joplin Internal-Only

To remove Joplin's public URL (bot connects via private network):

```bash
fly ips release -a joplin
```

### Updating

```bash
fly deploy -c fly.joplin.toml -a joplin      # Update Joplin
fly deploy -a telegram-joplin                 # Update bot
```

### Data Persistence

- **Joplin**: Notes and sync data in `joplin_data` volume
- **Bot**: Logs and conversation state in `telegram_joplin_data` volume

## Google Tasks Integration (Optional)

The bot can automatically create Google Tasks from AI-identified action items in your notes.

### Setup Steps

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one

2. **Enable Google Tasks API**
   - Go to "APIs & Services" → "Library"
   - Search for "Google Tasks API"
   - Click "Enable"

3. **Create OAuth2 Credentials**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth 2.0 Client IDs"
   - Choose "Desktop application"
   - Download the JSON file or copy Client ID and Secret

4. **Configure Environment**
   Add to your `.env` file:
   ```env
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```

5. **Authorize Access**
   - The bot will provide an OAuth2 authorization link
   - Follow the link and grant permissions for Google Tasks
   - Copy the authorization code back to the bot

### Features

- Automatic task creation from notes containing action items
- Bidirectional sync between Joplin notes and Google Tasks
- Customizable task lists and due dates
- Privacy controls for task data

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