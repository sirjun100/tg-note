"""
Telegram Orchestrator - Main Bot Logic
Coordinates all components to handle Telegram messages and create Joplin notes.
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from src.joplin_client import JoplinClient
from src.llm_orchestrator import LLMOrchestrator
from src.state_manager import StateManager
from src.logging_service import LoggingService, TelegramMessage, Decision
from src.security_utils import (
    check_whitelist, validate_message_text, ping_joplin_api,
    handle_api_error, format_error_message, format_success_message
)
from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

class TelegramOrchestrator:
    """Main orchestrator for the Telegram bot"""

    def __init__(self):
        self.joplin_client = JoplinClient()
        self.llm_orchestrator = LLMOrchestrator()
        self.state_manager = StateManager()
        self.logging_service = LoggingService()

        # Check Joplin connectivity on startup
        if not ping_joplin_api():
            logger.warning("Joplin API not accessible on startup")

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        user = update.effective_user
        if not user:
            return

        user_id = user.id

        # Check whitelist
        if not check_whitelist(user_id):
            await update.message.reply_text(
                "❌ Sorry, you're not authorized to use this bot."
            )
            return

        # Clear any existing state
        self.state_manager.clear_state(user_id)

        welcome_message = (
            "🤖 Welcome to the Intelligent Joplin Librarian!\n\n"
            "I can help you create notes in Joplin from your messages. "
            "Just send me what you'd like to note, and I'll figure out the details.\n\n"
            "If I need clarification, I'll ask questions. You can also reply to my questions.\n\n"
            "Commands:\n"
            "/start - Show this message\n"
            "/status - Check bot status"
        )

        await update.message.reply_text(welcome_message)
        logger.info(f"Started conversation with user {user_id}")

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        # Check Joplin connectivity
        joplin_ok = ping_joplin_api()

        status_msg = "🤖 Bot Status:\n\n"
        status_msg += f"Joplin API: {'✅ Connected' if joplin_ok else '❌ Not accessible'}\n"

        # Check if user has pending state
        has_pending = self.state_manager.has_pending_state(user.id)
        status_msg += f"Pending clarification: {'✅ Yes' if has_pending else '❌ No'}\n"

        if not joplin_ok:
            status_msg += "\n⚠️ Make sure Joplin is running with Web Clipper enabled."

        await update.message.reply_text(status_msg)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages"""
        user = update.effective_user
        message = update.message

        if not user or not message or not message.text:
            return

        user_id = user.id
        text = message.text.strip()

        # Check whitelist
        if not check_whitelist(user_id):
            await message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        # Validate message
        validated_text = validate_message_text(text)
        if not validated_text:
            await message.reply_text("❌ Please send a valid message.")
            return

        try:
            logger.info(f"📨 Processing message from user {user_id}: '{validated_text[:50]}{'...' if len(validated_text) > 50 else ''}'")

            # Log the incoming message
            telegram_msg = TelegramMessage(user_id=user_id, message_text=validated_text)
            telegram_message_id = self.logging_service.log_telegram_message(telegram_msg)

            # Check if user has pending state (previous clarification)
            pending_state = self.state_manager.get_state(user_id)

            if pending_state:
                logger.info(f"🔄 Handling clarification reply for user {user_id}")
                # This is a reply to a clarification question
                await self._handle_clarification_reply(user_id, validated_text, message)
            else:
                logger.info(f"🆕 Processing new request for user {user_id}")
                # This is a new request
                await self._handle_new_request(user_id, validated_text, message, telegram_message_id)

        except Exception as e:
            logger.error(f"Error handling message from user {user_id}: {e}")
            error_msg = handle_api_error(e, "message handling")
            await message.reply_text(format_error_message(error_msg))

    async def _handle_new_request(self, user_id: int, text: str, message, telegram_message_id: int) -> None:
        """Handle a new note creation request"""
        # Check Joplin connectivity
        if not ping_joplin_api():
            await message.reply_text(
                "❌ I'm ready, but Joplin isn't accessible on your computer. "
                "Please make sure Joplin is running with Web Clipper enabled."
            )
            return

        # Get existing tags for context
        existing_tags = []
        try:
            tags = self.joplin_client.fetch_tags()
            existing_tags = [tag.get('title', '') for tag in tags if tag.get('title')]
        except Exception as e:
            logger.warning(f"Failed to fetch tags for context: {e}")

        # Get folders for context
        folders = self.joplin_client.get_folders()

        # Process with LLM
        context = {"existing_tags": existing_tags, "folders": folders}
        llm_response = self.llm_orchestrator.process_message(text, context)

        await self._process_llm_response(user_id, llm_response, message, telegram_message_id)

    async def _handle_clarification_reply(self, user_id: int, text: str, message) -> None:
        """Handle reply to clarification question"""
        # Get pending state
        state = self.state_manager.get_state(user_id)
        if not state:
            await message.reply_text("❌ No pending clarification found. Please start a new request.")
            return

        # Combine with original message
        original_message = state.get('original_message', '')
        combined_message = f"{original_message}\n\nClarification: {text}"

        # Get existing tags
        existing_tags = state.get('existing_tags', [])

        # Get folders for context
        folders = self.joplin_client.get_folders()

        # Process combined message
        context = {"existing_tags": existing_tags, "folders": folders}
        llm_response = self.llm_orchestrator.process_message(combined_message, context)

        await self._process_llm_response(user_id, llm_response, message, clear_state=True)

    async def _process_llm_response(self, user_id: int, llm_response, message, telegram_message_id: Optional[int] = None, clear_state: bool = False) -> None:
        """Process the LLM response and take appropriate action"""
        if llm_response.status == "SUCCESS" and llm_response.note:
            # Create the note in Joplin
            note_id = await self._create_note_in_joplin(llm_response.note)

            if note_id:
                # Log the decision
                try:
                    self.joplin_client.append_log(llm_response.log_entry)
                except Exception as e:
                    logger.warning(f"Failed to append to log: {e}")

                # Log to database
                decision = Decision(
                    user_id=user_id,
                    telegram_message_id=telegram_message_id,
                    status=llm_response.status,
                    folder_chosen=llm_response.note.get('parent_id'),
                    note_title=llm_response.note.get('title'),
                    note_body=llm_response.note.get('body'),
                    tags=llm_response.note.get('tags', []),
                    joplin_note_id=note_id
                )
                self.logging_service.log_decision(decision)

                # Clear state and respond
                if clear_state:
                    self.state_manager.clear_state(user_id)

                # Get folder name for response
                folder_id = llm_response.note.get('parent_id')
                folder = self.joplin_client.get_folder(folder_id) if folder_id else None
                folder_name = folder.get('title', 'Unknown') if folder else 'Unknown'

                response_msg = format_success_message(
                    f"Note created: '{llm_response.note['title']}' in folder '{folder_name}'"
                )
                await message.reply_text(response_msg)

            else:
                await message.reply_text(
                    format_error_message("Failed to create note in Joplin. Please try again.")
                )

        elif llm_response.status == "NEED_INFO" and llm_response.question:
            # Store context and ask for clarification
            state = {
                'original_message': message.text,
                'existing_tags': llm_response.note.get('existing_tags', []) if llm_response.note else [],
                'llm_response': llm_response.dict()
            }

            self.state_manager.update_state(user_id, state)
            await message.reply_text(f"🤔 {llm_response.question}")

        else:
            # Unexpected response
            logger.error(f"Unexpected LLM response: {llm_response}")
            await message.reply_text(
                format_error_message("I had trouble understanding your request. Please try rephrasing.")
            )

    async def _create_note_in_joplin(self, note_data: Dict[str, Any]) -> Optional[str]:
        """Create a note in Joplin with the provided data"""
        try:
            logger.info(f"📝 Creating note in Joplin: '{note_data.get('title', 'Untitled')}'")

            # Validate note data
            from src.security_utils import validate_note_data
            errors = validate_note_data(note_data)
            if errors:
                logger.error(f"❌ Note validation failed: {errors}")
                return None

            # Create the note
            logger.debug(f"📁 Creating note in folder: {note_data['parent_id']}")

            note_id = self.joplin_client.create_note(
                folder_id=note_data['parent_id'],
                title=note_data['title'],
                body=note_data['body']
            )

            if not note_id:
                logger.error("❌ Failed to create note - no ID returned")
                return None

            logger.info(f"✅ Note created successfully with ID: {note_id}")

            # Apply tags if provided
            tags = note_data.get('tags', [])
            if tags:
                logger.debug(f"🏷️ Applying tags: {tags}")
                self.joplin_client.apply_tags(note_id, tags)
                logger.info(f"✅ Applied {len(tags)} tag(s) to note")

            return note_id

        except Exception as e:
            logger.error(f"💥 Error creating note in Joplin: {e}")
            logger.debug(f"Note data: {note_data}", exc_info=True)
            return None

def main():
    """Main function to run the bot"""
    # Set up logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    # Check token
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return

    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Create orchestrator
    orchestrator = TelegramOrchestrator()

    # Add handlers
    application.add_handler(CommandHandler("start", orchestrator.handle_start))
    application.add_handler(CommandHandler("status", orchestrator.handle_status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, orchestrator.handle_message))

    # Start the bot
    logger.info("Starting Telegram bot...")
    application.run_polling()

if __name__ == "__main__":
    main()