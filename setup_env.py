#!/usr/bin/env python3
"""
Intelligent Joplin Librarian Setup Script
Handles environment setup, folder discovery, and initial configuration.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_python_version():
    """Check if Python 3.8+ is available"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    print("✅ Python version:", sys.version.split()[0])

def install_requirements():
    """Install required packages"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install requirements")
        sys.exit(1)

def create_env_file():
    """Create .env file template"""
    env_content = """# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# LLM Provider Selection
# Choose your preferred LLM provider: openai, ollama, deepseek
# DeepSeek is recommended for cost-effective, high-quality responses
LLM_PROVIDER=deepseek

# DeepSeek Configuration (Primary Recommendation)
# Get your API key from: https://platform.deepseek.com/
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_MODEL=deepseek-chat

# OpenAI Configuration (Alternative)
OPENAI_API_KEY=your_openai_api_key_here

# Ollama Configuration (for local/private LLMs)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Application Configuration
ALLOWED_TELEGRAM_USER_IDS=your_user_id_here
"""
    with open(".env", "w") as f:
        f.write(env_content)
    print("✅ Created .env template file")

def check_joplin_connection():
    """Check if Joplin is running and accessible"""
    import requests
    try:
        response = requests.get("http://localhost:41184/ping", timeout=5)
        if response.status_code == 200:
            print("✅ Joplin Web Clipper is running")
            return True
        else:
            print("❌ Joplin Web Clipper returned unexpected status:", response.status_code)
            return False
    except requests.RequestException as e:
        print("❌ Cannot connect to Joplin Web Clipper:", str(e))
        print("   Make sure Joplin is running with Web Clipper enabled")
        return False

def discover_joplin_folders():
    """Discover and map Joplin folders"""
    import requests

    try:
        # Get all folders
        response = requests.get("http://localhost:41184/folders")
        if response.status_code != 200:
            print("❌ Failed to fetch folders from Joplin")
            return {}

        folders = response.json()
        folder_map = {}

        # Look for common folder names (00-04 as mentioned in requirements)
        for folder in folders:
            title = folder.get('title', '').strip()
            if title in ['00-Inbox', '01-Projects', '02-Areas', '03-Resources', '04-Archive']:
                folder_map[title] = folder['id']
                print(f"✅ Found folder: {title} -> {folder['id']}")

        if folder_map:
            # Save to config
            config = {"joplin_folders": folder_map}
            with open("joplin_config.json", "w") as f:
                json.dump(config, f, indent=2)
            print("✅ Saved folder mapping to joplin_config.json")
        else:
            print("⚠️  No standard folders (00-04) found. You may need to create them in Joplin.")

        return folder_map

    except Exception as e:
        print("❌ Error discovering folders:", str(e))
        return {}

def create_log_note():
    """Create the AI-Decision-Log note in Joplin"""
    import requests

    try:
        # First, get or create the log folder
        response = requests.get("http://localhost:41184/folders")
        folders = response.json()

        log_folder_id = None
        for folder in folders:
            if folder['title'] == 'AI-Logs':
                log_folder_id = folder['id']
                break

        if not log_folder_id:
            # Create AI-Logs folder
            create_response = requests.post("http://localhost:41184/folders", json={
                "title": "AI-Logs",
                "parent_id": ""
            })
            if create_response.status_code == 200:
                log_folder_id = create_response.json()['id']
                print("✅ Created AI-Logs folder")
            else:
                print("❌ Failed to create AI-Logs folder")
                return False

        # Create the log note
        note_data = {
            "title": "AI-Decision-Log",
            "body": "# AI Decision Log\n\nThis note contains a log of all AI decisions made by the Intelligent Joplin Librarian.\n\n---\n\n",
            "parent_id": log_folder_id
        }

        response = requests.post("http://localhost:41184/notes", json=note_data)
        if response.status_code == 200:
            note_id = response.json()['id']
            print(f"✅ Created AI-Decision-Log note: {note_id}")

            # Save note ID to config
            if os.path.exists("joplin_config.json"):
                with open("joplin_config.json", "r") as f:
                    config = json.load(f)
            else:
                config = {}

            config["ai_decision_log_note_id"] = note_id
            with open("joplin_config.json", "w") as f:
                json.dump(config, f, indent=2)

            return True
        else:
            print("❌ Failed to create AI-Decision-Log note")
            return False

    except Exception as e:
        print("❌ Error creating log note:", str(e))
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Intelligent Joplin Librarian")
    print("=" * 50)

    check_python_version()
    print()

    print("📦 Installing requirements...")
    install_requirements()
    print()

    print("⚙️  Creating environment configuration...")
    create_env_file()
    print()

    print("🔍 Checking Joplin connection...")
    if not check_joplin_connection():
        print("⚠️  Joplin is not running. Please start Joplin and run this script again.")
        print("   Make sure Web Clipper is enabled in Joplin settings.")
        return
    print()

    print("📁 Discovering Joplin folders...")
    folder_map = discover_joplin_folders()
    print()

    print("📝 Creating AI-Decision-Log note...")
    create_log_note()
    print()

    print("✅ Setup completed!")
    print()
    print("Next steps:")
    print("1. Get a DeepSeek API key from https://platform.deepseek.com/")
    print("2. Edit the .env file with your credentials:")
    print("   - TELEGRAM_BOT_TOKEN (from @BotFather)")
    print("   - DEEPSEEK_API_KEY (your DeepSeek API key)")
    print("   - ALLOWED_TELEGRAM_USER_IDS (your Telegram user ID)")
    print()
    print("3. Test your setup:")
    print("   source activate.sh")
    print("   python test_setup.py")
    print()
    print("4. Run the bot:")
    print("   python main.py")
    print()
    print("5. Test with /start command in Telegram")
    print()
    print("💡 Tip: You can switch LLM providers anytime by changing LLM_PROVIDER in .env")
    print("   Options: deepseek (recommended), openai, ollama")
    print()
    print("For help, see README.md and LLM_GUIDE.md")

if __name__ == "__main__":
    main()