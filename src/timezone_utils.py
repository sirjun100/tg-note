"""
Timezone utilities for timezone-aware datetime operations.

Provides centralized timezone handling based on user configuration,
with fallback to US/Eastern for users without a configured timezone.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import pytz

if TYPE_CHECKING:
    from src.logging_service import LoggingService

logger = logging.getLogger(__name__)

# Cache timezone lookups to minimize database queries (5-minute TTL)
_TIMEZONE_CACHE: dict[int, tuple[str, float]] = {}
_CACHE_TTL = 300  # 5 minutes

DEFAULT_TIMEZONE = "US/Eastern"


def get_user_timezone(user_id: int, logging_service: LoggingService | None) -> str:
    """
    Get user's configured timezone, with fallback to US/Eastern.

    Caches timezone lookups for 5 minutes to minimize DB queries.

    Args:
        user_id: Telegram user ID
        logging_service: LoggingService instance for getting report configuration

    Returns:
        Timezone string (e.g., "US/Eastern", "Europe/London")
    """
    # Check cache first
    if user_id in _TIMEZONE_CACHE:
        tz_str, cached_at = _TIMEZONE_CACHE[user_id]
        if datetime.now().timestamp() - cached_at < _CACHE_TTL:
            return tz_str

    if not logging_service:
        return DEFAULT_TIMEZONE

    try:
        # Get timezone from report configuration
        cfg = logging_service.get_report_configuration(user_id)
        if cfg and cfg.get("timezone"):
            tz_str = cfg.get("timezone")
            # Validate timezone
            try:
                pytz.timezone(tz_str)
                # Cache the result
                _TIMEZONE_CACHE[user_id] = (tz_str, datetime.now().timestamp())
                return tz_str
            except Exception as exc:
                logger.warning(
                    "Invalid timezone '%s' for user %d: %s. Using default %s",
                    tz_str, user_id, exc, DEFAULT_TIMEZONE
                )
    except Exception as exc:
        logger.warning("Failed to get timezone for user %d: %s. Using default %s", user_id, exc, DEFAULT_TIMEZONE)

    # Cache the fallback result
    _TIMEZONE_CACHE[user_id] = (DEFAULT_TIMEZONE, datetime.now().timestamp())
    return DEFAULT_TIMEZONE


def get_user_timezone_aware_now(user_id: int, logging_service: LoggingService | None) -> datetime:
    """
    Get current datetime in user's timezone.

    Args:
        user_id: Telegram user ID
        logging_service: LoggingService instance

    Returns:
        Timezone-aware datetime object in user's timezone
    """
    tz_str = get_user_timezone(user_id, logging_service)
    try:
        tz = pytz.timezone(tz_str)
        # Create a timezone-aware datetime in the user's timezone
        return datetime.now(tz=tz)
    except Exception as exc:
        logger.error("Failed to create timezone-aware datetime for user %d: %s", user_id, exc)
        # Fallback to UTC
        return datetime.now(tz=pytz.UTC)


def format_date_for_user(user_id: int, logging_service: LoggingService | None, dt: datetime) -> str:
    """
    Format datetime as YYYY-MM-DD in user's timezone.

    Handles both naive and timezone-aware datetime objects.

    Args:
        user_id: Telegram user ID
        logging_service: LoggingService instance
        dt: Datetime to format (naive or timezone-aware)

    Returns:
        Date string in format YYYY-MM-DD
    """
    tz_str = get_user_timezone(user_id, logging_service)
    try:
        tz = pytz.timezone(tz_str)

        # Convert to user's timezone if needed
        if dt.tzinfo is None:
            # Assume UTC if naive
            dt_aware = pytz.UTC.localize(dt)
        else:
            dt_aware = dt

        dt_in_tz = dt_aware.astimezone(tz)
        return dt_in_tz.strftime("%Y-%m-%d")
    except Exception as exc:
        logger.error("Failed to format date for user %d: %s", user_id, exc)
        # Fallback to ISO format
        return dt.strftime("%Y-%m-%d") if dt else ""


def get_current_date_str(user_id: int, logging_service: LoggingService | None) -> str:
    """
    Get current date string in user's timezone.

    Args:
        user_id: Telegram user ID
        logging_service: LoggingService instance

    Returns:
        Date string in format YYYY-MM-DD
    """
    now = get_user_timezone_aware_now(user_id, logging_service)
    return now.strftime("%Y-%m-%d")


def clear_timezone_cache(user_id: int | None = None) -> None:
    """
    Clear timezone cache for a user or all users.

    Useful for testing or when user configuration changes.

    Args:
        user_id: User ID to clear, or None to clear all
    """
    if user_id is None:
        _TIMEZONE_CACHE.clear()
    elif user_id in _TIMEZONE_CACHE:
        del _TIMEZONE_CACHE[user_id]
