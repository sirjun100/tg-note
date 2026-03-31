---
template_version: 1.1.0
last_updated: 2026-03-24
compatible_with: [feature-request, sprint-planning, product-backlog]
requires: [markdown-support]
---

# User Story: US-061 - LLM-generated image after Stoic reflection

[← Back to Product Backlog](../product-backlog.md)

**Status**: ✅ Done
**Priority**: 🟠 High
**Story Points**: 5
**Created**: 2026-03-17
**Updated**: 2026-03-24
**Assigned Sprint**: Sprint 20

## Description

After I answer the Stoic morning/evening questions and save with `/stoic_done`, I want the bot to generate a tasteful, symbolic image representing the reflection and attach it to the saved Joplin note, so the entry is more evocative and easier to revisit.

## User Story

As a user who journals daily with `/stoic`,
I want an LLM-generated image created after my morning/evening reflection is saved,
so that my journal entries feel more meaningful and memorable when I review them later.

## Acceptance Criteria

- [x] **AC-1: Generate image after save**
  - [x] When the user completes a Stoic session and runs `/stoic_done`, the bot generates an image based on the reflection content (and mode: `morning` or `evening`).
  - [x] The image generation happens after the note content is finalized (including replace/append flows).

- [x] **AC-2: Attach image to the Joplin note**
  - [x] The generated image is uploaded as a Joplin resource and embedded into the saved note body.
  - [x] The note remains valid Markdown and renders the image in Joplin.

- [x] **AC-3: Safe, tasteful prompt**
  - [x] Prompt produces a non-photorealistic, journal-appropriate visual (e.g., minimal illustration / watercolor / ink style).
  - [x] Prompt must avoid including personally identifying details, medical claims, or explicit content.

- [x] **AC-4: UX and failure handling**
  - [x] User sees a short “Generating image…” message, then a success confirmation when the note is updated.
  - [x] If image generation fails, the reflection is still saved; the bot reports a concise error and does not break the Stoic flow.

## Notes

- This should reuse the existing image generation pipeline used for URL notes (resource upload + embed) where possible.

## Key Files

| File | Purpose |
|------|---------|
| `src/handlers/stoic.py` | Stoic session flows; hook image generation after save |
| `src/llm_orchestrator.py` | Prompting/formatting utilities as needed |
| `src/joplin_client.py` | Resource upload + note update helpers |

