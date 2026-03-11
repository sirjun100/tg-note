# Defect: DEF-033 - Joplin agent fails to take screenshot of YouTube videos

[← Back to Product Backlog](../product-backlog.md)

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 3
**Created**: 2026-03-10
**Updated**: 2026-03-10
**Assigned Sprint**: Sprint 19

---

## Problem Statement

When a user sent a YouTube URL to the bot, the screenshot step failed because YouTube's static HTML contains strings like "video not available" which triggered `_is_error_page()` as a false-positive. This set `skip_screenshot=True` with an error, causing a "Screenshot skipped" warning to be shown. Additionally, the `og:image` thumbnail fallback only applied to recipe content, so YouTube links showed no image at all.

**User impact:** YouTube URLs saved to Joplin with no thumbnail and an unnecessary warning message.

---

## Steps to Reproduce

1. Send a YouTube URL to the bot (e.g. `https://www.youtube.com/watch?v=dQw4w9WgXcQ`)
2. Bot attempts to take a screenshot
3. False-positive error detected → "Screenshot skipped: ..." warning shown
4. Note saved with no image

---

## Expected Behavior

- No "Screenshot skipped" warning for YouTube/media sites
- `og:image` thumbnail used as fallback image
- Note saved cleanly with thumbnail

---

## Actual Behavior

- Warning shown: "Screenshot skipped: Security verification required" or similar
- No thumbnail in saved note

---

## Root Cause

Two issues:
1. `_is_error_page()` in `src/url_enrichment.py` matched YouTube HTML (contains "video not available" strings) as an error page
2. `og:image` fallback in `src/handlers/core.py` was recipe-only — not applied to media content type

---

## Fix

In `src/url_enrichment.py`:
- Added `_MEDIA_DOMAINS` tuple (`youtube.com`, `youtu.be`, `vimeo.com`, `spotify.com`)
- Media sites skip screenshot silently (no error set) before `_is_error_page()` is called

In `src/handlers/core.py`:
- Extended `og:image` fallback to cover `content_type == "media"` (not just recipes)
- Skip warning only shown when `url_context.get("error")` is non-empty

| File | Change |
|------|--------|
| `src/url_enrichment.py` | Media domain detection; skip before error checks |
| `src/handlers/core.py` | `og:image` fallback extended to media; conditional warning |

---

## References

- [Sprint 19](../../sprints/sprint-19-polish-and-bug-fixes.md)

---

## History

- 2026-03-10 - Created
- 2026-03-10 - Assigned to Sprint 19; Status changed to ✅ Completed
