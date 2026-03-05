"""
Test suite for timezone_utils module.

Covers timezone retrieval, fallback behavior, timezone-aware datetime creation,
and date formatting across timezone boundaries.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytz

from src import timezone_utils
from src.timezone_utils import (
    clear_timezone_cache,
    format_date_for_user,
    get_current_date_str,
    get_user_timezone,
    get_user_timezone_aware_now,
)


class TestGetUserTimezone(unittest.TestCase):
    """Test get_user_timezone function."""

    def setUp(self):
        """Clear cache before each test."""
        clear_timezone_cache()

    def tearDown(self):
        """Clear cache after each test."""
        clear_timezone_cache()

    def test_returns_default_when_no_logging_service(self):
        """Should return US/Eastern when logging_service is None."""
        tz = get_user_timezone(123, None)
        self.assertEqual(tz, "US/Eastern")

    def test_returns_configured_timezone(self):
        """Should return timezone from report configuration."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = {
            "timezone": "Europe/London"
        }

        tz = get_user_timezone(123, mock_logging)
        self.assertEqual(tz, "Europe/London")

    def test_returns_default_when_no_config(self):
        """Should return US/Eastern when user has no configuration."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = None

        tz = get_user_timezone(123, mock_logging)
        self.assertEqual(tz, "US/Eastern")

    def test_returns_default_when_timezone_missing(self):
        """Should return US/Eastern when timezone key missing from config."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = {
            "enabled": True
        }

        tz = get_user_timezone(123, mock_logging)
        self.assertEqual(tz, "US/Eastern")

    def test_returns_default_for_invalid_timezone(self):
        """Should return US/Eastern when timezone string is invalid."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = {
            "timezone": "Invalid/Timezone"
        }

        tz = get_user_timezone(123, mock_logging)
        self.assertEqual(tz, "US/Eastern")

    def test_caches_timezone_lookup(self):
        """Should cache timezone lookups to avoid repeated DB queries."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = {
            "timezone": "Asia/Tokyo"
        }

        # First call
        tz1 = get_user_timezone(123, mock_logging)
        self.assertEqual(tz1, "Asia/Tokyo")

        # Second call should use cache and not call get_report_configuration
        mock_logging.get_report_configuration.reset_mock()
        tz2 = get_user_timezone(123, mock_logging)
        self.assertEqual(tz2, "Asia/Tokyo")
        mock_logging.get_report_configuration.assert_not_called()


class TestGetUserTimezoneAwareNow(unittest.TestCase):
    """Test get_user_timezone_aware_now function."""

    def setUp(self):
        """Clear cache before each test."""
        clear_timezone_cache()

    def tearDown(self):
        """Clear cache after each test."""
        clear_timezone_cache()

    def test_returns_timezone_aware_datetime(self):
        """Should return timezone-aware datetime object."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = {
            "timezone": "US/Eastern"
        }

        now = get_user_timezone_aware_now(123, mock_logging)
        self.assertIsNotNone(now.tzinfo)
        self.assertEqual(str(now.tzinfo), "US/Eastern")

    def test_returns_correct_time_in_user_timezone(self):
        """Should return time in user's timezone, not UTC."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = {
            "timezone": "US/Pacific"
        }

        now = get_user_timezone_aware_now(123, mock_logging)

        # US/Pacific should be behind UTC
        utc_now = datetime.now(tz=pytz.UTC)
        # Convert to Pacific
        pacific_now = utc_now.astimezone(pytz.timezone("US/Pacific"))

        # Hours should be within 1 of each other (allowing for test timing)
        self.assertAlmostEqual(now.hour, pacific_now.hour, delta=1)

    def test_handles_default_timezone(self):
        """Should handle default timezone when none configured."""
        now = get_user_timezone_aware_now(123, None)
        self.assertIsNotNone(now.tzinfo)


class TestFormatDateForUser(unittest.TestCase):
    """Test format_date_for_user function."""

    def setUp(self):
        """Clear cache before each test."""
        clear_timezone_cache()

    def tearDown(self):
        """Clear cache after each test."""
        clear_timezone_cache()

    def test_formats_as_yyyy_mm_dd(self):
        """Should format date as YYYY-MM-DD."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = {
            "timezone": "UTC"
        }

        dt = datetime(2025, 3, 15, 10, 30, 0, tzinfo=pytz.UTC)
        formatted = format_date_for_user(123, mock_logging, dt)
        self.assertEqual(formatted, "2025-03-15")

    def test_converts_to_user_timezone(self):
        """Should convert to user's timezone before formatting."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = {
            "timezone": "US/Eastern"
        }

        # Create a UTC datetime at 11:30 PM UTC on March 15
        dt_utc = datetime(2025, 3, 15, 23, 30, 0, tzinfo=pytz.UTC)
        formatted = format_date_for_user(123, mock_logging, dt_utc)

        # US/Eastern is UTC-4 (EDT), so 11:30 PM UTC is 7:30 PM EDT on same day
        self.assertEqual(formatted, "2025-03-15")

    def test_handles_naive_datetime(self):
        """Should handle naive datetime by assuming UTC."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = {
            "timezone": "UTC"
        }

        dt = datetime(2025, 3, 15, 10, 30, 0)  # naive
        formatted = format_date_for_user(123, mock_logging, dt)
        self.assertEqual(formatted, "2025-03-15")

    def test_timezone_boundary_case(self):
        """Should handle midnight boundary when crossing timezones."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = {
            "timezone": "US/Eastern"
        }

        # Create a UTC datetime at 7:30 AM UTC on March 16
        # In US/Eastern (EDT, UTC-4), this is 3:30 AM on March 16
        dt_utc = datetime(2025, 3, 16, 7, 30, 0, tzinfo=pytz.UTC)
        formatted = format_date_for_user(123, mock_logging, dt_utc)
        self.assertEqual(formatted, "2025-03-16")

        # Create a UTC datetime at 4:00 AM UTC on March 16
        # In US/Eastern (EDT, UTC-4), this is 12:00 AM (midnight) on March 16
        dt_utc = datetime(2025, 3, 16, 4, 0, 0, tzinfo=pytz.UTC)
        formatted = format_date_for_user(123, mock_logging, dt_utc)
        self.assertEqual(formatted, "2025-03-16")

        # Create a UTC datetime at 3:59 AM UTC on March 16
        # In US/Eastern (EDT, UTC-4), this is 11:59 PM on March 15
        dt_utc = datetime(2025, 3, 16, 3, 59, 0, tzinfo=pytz.UTC)
        formatted = format_date_for_user(123, mock_logging, dt_utc)
        self.assertEqual(formatted, "2025-03-15")


class TestGetCurrentDateStr(unittest.TestCase):
    """Test get_current_date_str function."""

    def setUp(self):
        """Clear cache before each test."""
        clear_timezone_cache()

    def tearDown(self):
        """Clear cache after each test."""
        clear_timezone_cache()

    def test_returns_date_string(self):
        """Should return current date as YYYY-MM-DD string."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = {
            "timezone": "UTC"
        }

        date_str = get_current_date_str(123, mock_logging)

        # Should be a valid date string
        self.assertRegex(date_str, r'^\d{4}-\d{2}-\d{2}$')

    def test_uses_user_timezone(self):
        """Should use user's timezone for current date."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = {
            "timezone": "US/Eastern"
        }

        date_str = get_current_date_str(123, mock_logging)

        # Should return today's date in US/Eastern timezone
        eastern = pytz.timezone("US/Eastern")
        today_eastern = datetime.now(tz=eastern).strftime("%Y-%m-%d")

        self.assertEqual(date_str, today_eastern)


class TestClearTimezoneCache(unittest.TestCase):
    """Test clear_timezone_cache function."""

    def setUp(self):
        """Clear cache before each test."""
        clear_timezone_cache()

    def test_clears_specific_user_cache(self):
        """Should clear cache for specific user."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = {
            "timezone": "US/Eastern"
        }

        # Populate cache
        tz1 = get_user_timezone(123, mock_logging)
        self.assertEqual(tz1, "US/Eastern")

        # Clear specific user
        clear_timezone_cache(123)

        # Should call get_report_configuration again
        mock_logging.get_report_configuration.reset_mock()
        mock_logging.get_report_configuration.return_value = {
            "timezone": "Europe/London"
        }
        tz2 = get_user_timezone(123, mock_logging)
        self.assertEqual(tz2, "Europe/London")
        mock_logging.get_report_configuration.assert_called_once()

    def test_clears_all_cache(self):
        """Should clear cache for all users when user_id is None."""
        mock_logging = MagicMock()
        mock_logging.get_report_configuration.return_value = {
            "timezone": "US/Eastern"
        }

        # Populate cache for multiple users
        get_user_timezone(123, mock_logging)
        get_user_timezone(456, mock_logging)

        # Clear all
        clear_timezone_cache(None)

        # Cache should be empty
        self.assertEqual(len(timezone_utils._TIMEZONE_CACHE), 0)


if __name__ == "__main__":
    unittest.main()
