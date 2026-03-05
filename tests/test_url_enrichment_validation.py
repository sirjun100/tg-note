"""
Test suite for URL content validation (BF-007).

Covers: Error page detection, domain mismatch detection, validation pipeline.
"""

from __future__ import annotations

import unittest

from src.url_enrichment import (
    _check_domain_mismatch,
    _is_error_page,
)


class TestIsErrorPage(unittest.TestCase):
    """Test _is_error_page error detection."""

    def test_detect_404_in_text(self):
        """Detect 404 error in page text."""
        html = "<html><body>404 Not Found</body></html>"
        title = "Error"
        is_error, reason = _is_error_page(html, title, "https://example.com/missing")
        self.assertTrue(is_error)
        self.assertIn("404", reason)

    def test_detect_403_forbidden(self):
        """Detect 403 Forbidden error."""
        html = "<html><body>403 Forbidden - Access Denied</body></html>"
        title = "Forbidden"
        is_error, reason = _is_error_page(html, title, "https://example.com")
        self.assertTrue(is_error)
        self.assertIn("403", reason)

    def test_detect_not_available(self):
        """Detect 'Content not available' messages."""
        html = "<html><body>This content is not available</body></html>"
        title = "Unavailable"
        is_error, reason = _is_error_page(html, title, "https://example.com")
        self.assertTrue(is_error)
        self.assertIn("not available", reason.lower())

    def test_detect_geo_blocked(self):
        """Detect geo-blocked content."""
        html = "<html><body>This video is geo-blocked in your region</body></html>"
        title = "Video"
        is_error, reason = _is_error_page(html, title, "https://youtube.com/watch?v=abc")
        self.assertTrue(is_error)
        self.assertIn("geo", reason.lower())

    def test_detect_login_required(self):
        """Detect login required pages."""
        html = "<html><body>Sign in required to view this content</body></html>"
        title = "Sign In"
        is_error, reason = _is_error_page(html, title, "https://example.com")
        self.assertTrue(is_error)
        self.assertIn("login", reason.lower())

    def test_detect_paywall(self):
        """Detect paywall/subscription messages."""
        html = "<html><body>This article is behind a paywall. Subscribe to read.</body></html>"
        title = "Article"
        is_error, reason = _is_error_page(html, title, "https://example.com")
        self.assertTrue(is_error)
        self.assertIn("paywall", reason.lower())

    def test_detect_video_not_available(self):
        """Detect YouTube video not available."""
        html = "<html><body>Video not available</body></html>"
        title = "Not Available"
        is_error, reason = _is_error_page(html, title, "https://youtube.com/watch?v=xyz")
        self.assertTrue(is_error)
        self.assertIn("not available", reason.lower())

    def test_detect_youtube_error_domain(self):
        """Detect YouTube error domain (dws.youtube)."""
        html = "<html><body>Error</body></html>"
        title = "Error"
        is_error, reason = _is_error_page(html, title, "https://dws.youtube.com/error")
        self.assertTrue(is_error)
        self.assertIn("youtube", reason.lower())

    def test_detect_server_error(self):
        """Detect 500 server error."""
        html = "<html><body>Internal Server Error</body></html>"
        title = "500 Error"
        is_error, reason = _is_error_page(html, title, "https://example.com")
        self.assertTrue(is_error)
        self.assertIn("500", reason)

    def test_normal_page_not_error(self):
        """Normal page content is not detected as error."""
        html = "<html><body>This is a normal article about programming best practices.</body></html>"
        title = "Best Practices"
        is_error, reason = _is_error_page(html, title, "https://example.com/article")
        self.assertFalse(is_error)
        self.assertEqual(reason, "")

    def test_empty_html_not_error(self):
        """Empty HTML is not detected as error."""
        is_error, reason = _is_error_page("", "Title", "https://example.com")
        self.assertFalse(is_error)
        self.assertEqual(reason, "")

    def test_error_in_title(self):
        """Detect error keywords in page title."""
        html = "<html><body>Some content</body></html>"
        title = "404 Not Found"
        is_error, reason = _is_error_page(html, title, "https://example.com")
        self.assertTrue(is_error)
        self.assertIn("404", reason)

    def test_case_insensitive_detection(self):
        """Error detection is case-insensitive."""
        html = "<html><body>NOT FOUND - PAGE DOES NOT EXIST</body></html>"
        title = ""
        is_error, reason = _is_error_page(html, title, "https://example.com")
        self.assertTrue(is_error)


class TestCheckDomainMismatch(unittest.TestCase):
    """Test _check_domain_mismatch domain redirect validation."""

    def test_same_domain_valid(self):
        """Same domain is valid."""
        valid, error = _check_domain_mismatch(
            "https://example.com/page1",
            "https://example.com/page2"
        )
        self.assertTrue(valid)
        self.assertEqual(error, "")

    def test_www_variant_valid(self):
        """www and non-www variants are treated as same domain."""
        valid, error = _check_domain_mismatch(
            "https://example.com/page",
            "https://www.example.com/page"
        )
        self.assertTrue(valid)
        self.assertEqual(error, "")

    def test_subdomain_variant_valid(self):
        """Different subdomains of same domain are valid."""
        valid, error = _check_domain_mismatch(
            "https://api.example.com/page",
            "https://www.example.com/page"
        )
        self.assertTrue(valid)
        self.assertEqual(error, "")

    def test_youtube_youtu_be_redirect_valid(self):
        """YouTube to youtu.be redirect is valid."""
        valid, error = _check_domain_mismatch(
            "https://youtube.com/watch?v=abc",
            "https://youtu.be/abc"
        )
        self.assertTrue(valid)
        self.assertEqual(error, "")

    def test_youtu_be_youtube_redirect_valid(self):
        """youtu.be to YouTube redirect is valid."""
        valid, error = _check_domain_mismatch(
            "https://youtu.be/abc",
            "https://youtube.com/watch?v=abc"
        )
        self.assertTrue(valid)
        self.assertEqual(error, "")

    def test_youtube_mobile_redirect_valid(self):
        """YouTube to mobile YouTube redirect is valid."""
        valid, error = _check_domain_mismatch(
            "https://youtube.com/watch?v=abc",
            "https://m.youtube.com/watch?v=abc"
        )
        self.assertTrue(valid)
        self.assertEqual(error, "")

    def test_twitter_x_redirect_valid(self):
        """Twitter to X redirect is valid."""
        valid, error = _check_domain_mismatch(
            "https://twitter.com/user",
            "https://x.com/user"
        )
        self.assertTrue(valid)
        self.assertEqual(error, "")

    def test_reddit_old_redirect_valid(self):
        """reddit.com to old.reddit.com redirect is valid."""
        valid, error = _check_domain_mismatch(
            "https://reddit.com/r/python",
            "https://old.reddit.com/r/python"
        )
        self.assertTrue(valid)
        self.assertEqual(error, "")

    def test_suspicious_redirect_invalid(self):
        """Redirect from YouTube to unrelated domain is suspicious."""
        valid, error = _check_domain_mismatch(
            "https://youtube.com/watch?v=abc",
            "https://ads.com/scam"
        )
        self.assertFalse(valid)
        self.assertIn("Suspicious", error)
        self.assertIn("youtube.com", error)
        self.assertIn("ads.com", error)

    def test_redirect_to_different_domain_invalid(self):
        """Redirect to completely different domain is suspicious."""
        valid, error = _check_domain_mismatch(
            "https://example.com/article",
            "https://malware-site.com/download"
        )
        self.assertFalse(valid)
        self.assertIn("Suspicious", error)

    def test_case_insensitive_domain_matching(self):
        """Domain matching is case-insensitive."""
        valid, error = _check_domain_mismatch(
            "https://EXAMPLE.COM/page",
            "https://example.com/page"
        )
        self.assertTrue(valid)
        self.assertEqual(error, "")

    def test_instagram_redirect_valid(self):
        """instagram.com to www.instagram.com redirect is valid."""
        valid, error = _check_domain_mismatch(
            "https://instagram.com/user",
            "https://www.instagram.com/user"
        )
        self.assertTrue(valid)
        self.assertEqual(error, "")


class TestValidationPipelineIntegration(unittest.TestCase):
    """Test integration with fetch_url_context (indirect testing)."""

    def test_error_page_function_chain(self):
        """Error detection functions can be chained."""
        # Test that both functions return proper tuple format
        html_error = "<html><body>404 Not Found</body></html>"
        is_error, reason = _is_error_page(html_error, "Error", "https://example.com")
        self.assertIsInstance(is_error, bool)
        self.assertIsInstance(reason, str)

        # Domain mismatch
        valid, error = _check_domain_mismatch(
            "https://youtube.com/watch?v=abc",
            "https://ads.com/bad"
        )
        self.assertIsInstance(valid, bool)
        self.assertIsInstance(error, str)

    def test_error_detection_comprehensiveness(self):
        """Test multiple error types are covered."""
        test_cases = [
            ("<body>404 Not Found</body>", "404 error"),
            ("<body>403 Forbidden</body>", "403 error"),
            ("<body>Geo-blocked content</body>", "Geo-block"),
            ("<body>Sign in required</body>", "Login"),
            ("<body>Behind paywall</body>", "Paywall"),
        ]

        for html, description in test_cases:
            is_error, reason = _is_error_page(html, "", "https://example.com")
            self.assertTrue(is_error, f"Should detect {description}")
            self.assertTrue(len(reason) > 0, f"Should provide reason for {description}")


if __name__ == "__main__":
    unittest.main()
