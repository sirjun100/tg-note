# Defect: DEF-025 - Recipe Pasted as Text Shows "Screenshot skipped: Security verification required" Incorrectly

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 2
**Created**: 2026-03-09
**Updated**: 2026-03-09
**Assigned Sprint**: Backlog
**Related**: [DEF-007](DEF-007-url-screenshot-no-content-validation.md) URL Screenshots validation

## Description

When the user copies and pastes recipe text directly (no URL, or URL is incidental from copy-paste), the bot incorrectly shows "Screenshot skipped: Security verification required". There is no URL to screenshot for pasted content, so this message is misleading and suggests the bot wrongly treats pasted recipes as if they came from a paywalled or security-protected URL.

## Steps to Reproduce

1. Open Telegram chat with Joplin bot.
2. Copy recipe text from any source (e.g. a document, email, or website) and paste it into the chat.
3. Send the message (user intent: paste recipe text; URL may or may not be included from copy-paste).
4. Observe the bot's response.

## Expected Behavior

- For pasted recipe text with no user-provided URL: no "Screenshot skipped" message.
- The bot should either attempt AI-generated image only, or skip image-related messages entirely.
- The "Screenshot skipped" message should only appear when the user explicitly provided a URL that could not be screenshotted.

## Actual Behavior

- Bot shows "Screenshot skipped: Security verification required" even when the user pasted text.
- The note is created successfully in Resources/Recipe with tags.
- The misleading warning appears and confuses the user (e.g. "it makes no sense that the recipe is paywalled").

## Root Cause

- When user pastes from a webpage, the paste can include the URL. `extract_urls` finds it, we fetch the page.
- If the page has Cloudflare/security verification, `skip_screenshot` is set.
- The bot showed "Screenshot skipped" regardless of whether the user sent a link (short message) or pasted long text (URL incidental).
- No distinction between "user sent URL" vs "user pasted text with URL embedded".

## Solution Implemented

1. Added `url_was_primary` flag: `True` when message length < 200 chars (user likely sent a link), `False` when long (pasted content).
2. Only show "Screenshot skipped" when `url_was_primary` is True.
3. Set the flag in `_handle_new_request` and braindump reply handler when url_context has a real URL (not "(pasted)").

## Files Modified

- `src/handlers/core.py` — Added `url_was_primary` to url_context; conditional display of screenshot-skipped message

## History

- 2026-03-09 - User report: pasted carrot cake recipe showed "Screenshot skipped: Security verification required"; defect created
- 2026-03-09 - Fix: only show screenshot-skipped when `url_was_primary` (message < 200 chars)
