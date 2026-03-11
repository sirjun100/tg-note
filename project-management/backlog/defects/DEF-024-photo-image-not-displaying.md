# Defect: DEF-024 - Photo OCR: Image Not Displaying in Joplin Note

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 2
**Created**: 2026-03-07
**Updated**: 2026-03-07
**Assigned Sprint**: Backlog
**Related**: [US-030](../user-stories/US-030-photo-ocr-capture.md) Photo OCR Capture

## Description

When a user sends a photo for OCR capture, the note is created with the correct markdown (e.g. `` ![Captured image](:/resource_id) ``) in the body, but the image does not display properly in Joplin. Instead of showing the image inline, Joplin shows a download icon. The image may not appear until the user runs `/sync` in the bot and syncs in Joplin.

## Steps to Reproduce

1. Send a photo to the bot (with OCR enabled).
2. Bot processes photo, creates note with "## Original Image" section.
3. Open the note in Joplin Desktop.
4. Observe: Image section shows download icon instead of rendered image; image may not display inline.

## Expected Behavior

- Image displays inline in the Joplin note, same as Dream journal images.
- No manual sync step required for image to appear (or clear guidance if sync is needed).

## Actual Behavior

- Image shows as download icon or does not render.
- User must run `/sync` in the bot and sync in Joplin to see the image.

## Root Cause

1. **Missing Joplin sync**: The Dream handler calls `_schedule_joplin_sync()` after creating a note with an embedded image. The Photo handler does not. Without this, the Joplin server may not push the new resource to the sync target (e.g. Dropbox), so the desktop client cannot display it until sync runs.

2. **No user guidance**: Unlike Stoic journal, the photo success message does not tell users to run `/sync` if the image doesn't appear.

## Solution

1. Call `_schedule_joplin_sync()` after successful photo note creation (both `_handle_photo` and `handle_photo_message`).
2. Add sync hint to success message: "If the image doesn't show, run /sync then sync in Joplin."

## Files Modified

- `src/handlers/photo.py` — Added `_schedule_joplin_sync()` after note creation (both `_handle_photo` and `handle_photo_message`); added sync hint to success message when image is embedded

## History

- 2026-03-07 - Bug reported; fix implemented: schedule Joplin sync after photo note creation, add user hint for /sync
