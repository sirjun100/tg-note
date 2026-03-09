# Defect: DEF-007 - URL Screenshots: No Validation That Content Matches the URL

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 5
**Created**: 2026-03-04
**Updated**: 2026-03-06
**Assigned Sprint**: Sprint 13

## Description

When a user pastes a URL (e.g., a YouTube link, news article, etc.), the bot fetches the page and takes a screenshot. However, **there is no validation to ensure the screenshot shows actual content from that website**. If the server returns an error page (404, 403, 500, geo-blocked, language-specific error, etc.), the bot still captures and stores a screenshot of the error page instead of rejecting it.

### Real-World Example

1. User pastes: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
2. YouTube server returns a 200 OK with HTML that says (in German): "Dieses Video ist in Ihrem Land nicht verfügbar" (Video not available in your country)
3. Bot takes a screenshot of the German error page
4. Bot saves the note with an error screenshot, not the actual video
5. User's note is polluted with a useless screenshot

## Steps to Reproduce

1. Find a YouTube video that is geo-blocked or restricted in your region
2. Paste the URL to the bot: `/note https://www.youtube.com/watch?v=...`
3. Bot fetches the page (gets 200 OK)
4. Server returns German error page or similar
5. Bot takes screenshot of error page
6. Note is saved with error screenshot instead of being rejected

## Expected Behavior

The bot should validate that:
1. **Status code is 2xx** (already done with `resp.raise_for_status()`)
2. **The page title/content indicates success**, not an error
   - Check for common error indicators: "not available", "error", "404", "403", "blocked", "restricted", "inaccessible"
   - Check for language mismatch (if title is in German but URL is YouTube, might be error)
3. **The domain in the final URL matches the expected domain** (after redirects)
4. **The page has meaningful content**, not just error messages
5. **If validation fails**, set `skip_screenshot = True` and mark the note with a warning, or abort the note creation entirely

## Root Cause

`src/url_enrichment.py:fetch_url_context()` lines 294-359:

Currently only checks:
- HTTP status (raise_for_status)
- Cloudflare challenge pages (`_is_challenge_page()`)

**Missing checks:**
- Error page detection (404, 500, "not found", "unavailable", etc.)
- Content validation (does the page actually have the expected content type?)
- Domain mismatch detection (did we get redirected to a completely different domain?)
- Language-based error detection (error messages in unexpected languages)

```python
async def fetch_url_context(url: str) -> dict[str, Any]:
    # ...
    resp = await client.get(url)
    resp.raise_for_status()  # ✅ Catches HTTP error codes
    final_url = str(resp.url)
    html_text = resp.text[:300_000]

    # ✅ Detects Cloudflare challenges
    if _is_challenge_page(html_text, title):
        result["skip_screenshot"] = True

    # ❌ Missing: validation that content actually matches the URL
    # ❌ Missing: error page detection
    # ❌ Missing: domain mismatch detection
```

## Proposed Solution

### 1. Add error page detection function

```python
def _is_error_page(html_text: str, title: str, url: str) -> bool:
    """
    Detect error pages that return 200 OK but show error content.
    Examples:
    - YouTube: "Video not available in your country"
    - Generic: 404, 403, 500, "Page not found", "Access denied"
    - Paywalls: "Sign in", "Subscribe", "Premium only"
    """
    text_lower = html_text[:100_000].lower()
    title_lower = (title or "").lower()

    error_indicators = [
        "not found",
        "404",
        "403 forbidden",
        "access denied",
        "not available",
        "not accessible",
        "unavailable",
        "error occurred",
        "error loading",
        "page not found",
        "does not exist",
        "cannot access",
        "blocked",
        "restricted",
        "geo-restricted",
        "geo-blocked",
        "this video is not available",
        "this content is not available",
        "sign in required",
        "subscribe",
        "premium only",
        "members only",
        "paywall",
        "dws.youtube" if "youtube" in url.lower() else "",  # YouTube error domain
    ]

    # Check if any error indicator appears prominently
    return any(phrase in text_lower or phrase in title_lower
               for phrase in error_indicators if phrase)
```

### 2. Add domain mismatch detection

```python
def _check_domain_mismatch(original_url: str, final_url: str) -> bool:
    """
    Detect if we got redirected to a completely different domain.
    Example: URL youtube.com → redirects to error.com or ads.com

    Returns True if domains match (or are related), False if suspicious redirect.
    """
    from urllib.parse import urlparse

    original_domain = urlparse(original_url).netloc.lower()
    final_domain = urlparse(final_url).netloc.lower()

    # Extract base domain (handle subdomains)
    def get_base_domain(domain: str) -> str:
        parts = domain.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return domain

    original_base = get_base_domain(original_domain)
    final_base = get_base_domain(final_domain)

    # Allow subdomains but reject completely different domains
    return original_base == final_base or original_domain == final_domain
```

### 3. Update `fetch_url_context()` to use new validators

```python
async def fetch_url_context(url: str) -> dict[str, Any]:
    # ... existing code ...

    try:
        # ... fetch response ...
        resp = await client.get(url)
        resp.raise_for_status()
        final_url = str(resp.url)
        html_text = resp.text[:300_000]

        title = ... # extract title

        # NEW: Check for domain mismatch
        if not _check_domain_mismatch(url, final_url):
            result["skip_screenshot"] = True
            result["error"] = "Unexpected redirect to different domain"
            logger.warning("Domain mismatch for %s → %s", url, final_url)
            return result

        # NEW: Check for error pages
        if _is_error_page(html_text, title, url):
            result["skip_screenshot"] = True
            result["error"] = "Page appears to be an error or not available"
            logger.warning("Error page detected for %s: %s", url, title)
            return result

        # Existing Cloudflare check
        if _is_challenge_page(html_text, title):
            result["skip_screenshot"] = True

        # ... rest of function ...
```

### 4. Update note creation to warn user

In `src/handlers/core.py` where screenshot is used (`create_note_in_joplin`):

```python
if url_context.get("error"):
    await message.reply_text(
        f"⚠️ Could not fetch content from that URL:\n{url_context['error']}\n\n"
        f"Screenshot will not be included. Proceeding with text content only."
    )
elif url_context and url_context.get("url") and not url_context.get("skip_screenshot"):
    image_data_url = await capture_url_screenshot(url_context["url"])
```

## Technical References

- File: `src/url_enrichment.py` — URL validation and content extraction
- File: `src/url_enrichment.py:246-268` — `_is_challenge_page()` as reference for detection pattern
- File: `src/handlers/core.py` — Screenshot integration in `create_note_in_joplin` (DEF-025: only show "screenshot skipped" when URL was primary input)
- File: `src/url_screenshot.py` — Screenshot capture (downstream of validation)

## Testing

- [ ] Verify error pages (404, 403, 500) are detected and screenshot skipped
- [ ] Verify geo-blocked YouTube videos skip screenshot
- [ ] Verify paywall pages (requires sign-in) skip screenshot
- [ ] Verify domain redirect mismatch is detected (youtube.com → random-ads.com)
- [ ] Verify valid pages still get screenshots
- [ ] Verify subdomain redirects are allowed (youtube.com → youtu.be)
- [ ] Verify user is notified when screenshot is skipped with reason
- [ ] Unit test: error_page detection with various error messages
- [ ] Unit test: domain_mismatch with valid and invalid redirects
- [ ] Integration test: paste geo-blocked video → no error screenshot

## Dependencies

- None (improvements to `url_enrichment.py`)

## Notes

- The fix should be defensive: **when in doubt, skip the screenshot** rather than polluting notes with error images
- Error messages should be logged at WARNING level so we can identify websites that frequently fail
- Consider adding a `/set_strict_mode` setting where users can choose to abort note creation entirely if URL validation fails (vs. proceeding without screenshot)
- Future enhancement: use an OCR/vision model to verify the screenshot actually contains expected keywords (e.g., screenshot of YouTube video page should show "YouTube" or video title)

## History

- 2026-03-04 - Created (user-reported: geo-blocked YouTube video → German error screenshot)
