# User Story: US-054 - Note Creation: Show Full Save Path and Auto-Sync

[← Back to Product Backlog](../product-backlog.md)

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 2
**Created**: 2026-03-09
**Updated**: 2026-03-09
**Assigned Sprint**: Backlog

## Description

When a note is created (via any flow: plain message, /note, braindump, photo OCR, recipe, etc.), the success message should display the full path where the note was saved and the bot should automatically run sync so the note appears on the user's other devices promptly.

## User Story

As a user creating notes in Joplin via the bot,
I want to see the full save path and have sync run automatically,
so that I know exactly where the note went and it appears on my other devices without running /sync manually.

## Acceptance Criteria

- [ ] Success message shows full folder path (e.g. "Saved to: Areas/Work/Projects/MyProject")
- [ ] Sync runs automatically after every note creation (equivalent to /sync)
- [ ] Applies to all note-creation flows: plain message, /note, braindump, photo OCR, recipe, planning, stoic, dream
- [ ] User sees note on other devices without manually running /sync

## Business Value

Improves discoverability (full path) and reduces friction (no manual sync). Users with multi-device Joplin setups (e.g. phone + desktop) get notes synced immediately.

## Related

- [DEF-031](../defects/DEF-031-note-creation-should-show-full-path-and-trigger-sync.md) — Same scope, tracked as defect; can be closed when this story is implemented.
