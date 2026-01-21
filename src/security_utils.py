"""
Security and Error Handling Utilities
Provides authentication, validation, and error management functions.
"""

import logging
from typing import List, Optional, Dict
from config import ALLOWED_TELEGRAM_USER_IDS

logger = logging.getLogger(__name__)

def check_whitelist(user_id: int) -> bool:
    """
    Check if a Telegram user ID is in the allowed list

    Args:
        user_id: Telegram user ID to check

    Returns:
        True if user is allowed, False otherwise
    """
    if not ALLOWED_TELEGRAM_USER_IDS:
        logger.warning("No allowed user IDs configured. Allowing all users.")
        return True

    # Convert to list of ints, filtering out empty strings
    allowed_ids = []
    for id_str in ALLOWED_TELEGRAM_USER_IDS:
        id_str = id_str.strip()
        if id_str:
            try:
                allowed_ids.append(int(id_str))
            except ValueError:
                logger.warning(f"Invalid user ID in config: {id_str}")

    is_allowed = user_id in allowed_ids

    if is_allowed:
        logger.info(f"User {user_id} is whitelisted")
    else:
        logger.warning(f"User {user_id} is not whitelisted. Access denied.")

    return is_allowed

def validate_message_text(text: str) -> Optional[str]:
    """
    Validate incoming message text

    Args:
        text: Message text to validate

    Returns:
        Validated text or None if invalid
    """
    if not text:
        return None

    text = text.strip()
    if not text:
        return None

    # Check length (Telegram limit is 4096, but be reasonable)
    if len(text) > 10000:
        logger.warning(f"Message too long: {len(text)} characters")
        return None

    return text

def ping_joplin_api(base_url: str = "http://localhost:41184") -> bool:
    """
    Check if Joplin Web Clipper API is accessible

    Args:
        base_url: Joplin API base URL

    Returns:
        True if API is reachable, False otherwise
    """
    import requests

    try:
        response = requests.get(f"{base_url}/ping", timeout=5)
        is_up = response.status_code == 200

        if is_up:
            logger.debug("Joplin API is accessible")
        else:
            logger.warning(f"Joplin API returned status {response.status_code}")

        return is_up

    except requests.RequestException as e:
        logger.error(f"Joplin API connection failed: {e}")
        return False

def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent issues

    Args:
        text: Input text to sanitize

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove potentially problematic characters
    # Keep basic punctuation but remove control characters
    import re
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

    # Limit length to prevent abuse
    max_length = 5000
    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text.strip()

def log_user_action(user_id: int, action: str, details: Optional[Dict] = None):
    """
    Log user actions for audit purposes

    Args:
        user_id: Telegram user ID
        action: Action performed
        details: Additional details
    """
    details_str = f" - {details}" if details else ""
    logger.info(f"User {user_id}: {action}{details_str}")

def handle_api_error(error: Exception, context: str = "") -> str:
    """
    Handle API errors and return user-friendly messages

    Args:
        error: The exception that occurred
        context: Additional context about where the error occurred

    Returns:
        User-friendly error message
    """
    error_type = type(error).__name__

    if "OpenAI" in error_type:
        return "I'm having trouble with the AI service right now. Please try again in a moment."

    elif "RequestException" in str(error):
        if "Joplin" in context:
            return "I can't connect to your Joplin notes right now. Please make sure Joplin is running and try again."
        else:
            return "I'm having trouble connecting to external services. Please try again."

    elif "ValidationError" in error_type:
        return "There was an issue processing your request. Please rephrase and try again."

    elif "Timeout" in str(error):
        return "The request took too long. Please try again."

    else:
        logger.error(f"Unhandled error in {context}: {error}")
        return "Something went wrong. Please try again or contact support if the problem persists."

def validate_note_data(note_data: Dict) -> List[str]:
    """
    Validate note data before sending to Joplin

    Args:
        note_data: Note data to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if not note_data.get('title'):
        errors.append("Note title is required")

    if not note_data.get('body'):
        errors.append("Note body is required")

    if not note_data.get('parent_id'):
        errors.append("Parent folder ID is required")

    title = note_data.get('title', '')
    if len(title) > 100:
        errors.append("Note title is too long (max 100 characters)")

    if len(note_data.get('body', '')) > 100000:
        errors.append("Note body is too long (max 100,000 characters)")

    return errors

def format_error_message(error: str) -> str:
    """
    Format error messages for Telegram

    Args:
        error: Error message to format

    Returns:
        Formatted message
    """
    return f"❌ {error}"

def format_success_message(message: str) -> str:
    """
    Format success messages for Telegram

    Args:
        message: Success message to format

    Returns:
        Formatted message
    """
    return f"✅ {message}"