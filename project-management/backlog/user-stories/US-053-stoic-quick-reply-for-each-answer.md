# User Story: US-053 - Stoic Journal Quick Reply for Each Answer

[← Back to Product Backlog](../product-backlog.md)

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 3
**Created**: 2026-03-09
**Updated**: 2026-03-10
**Assigned Sprint**: Sprint 19
**Parent**: [US-052](US-052-world-class-stoic-journaling-experience.md) World-Class Stoic Journaling Experience

## Description

When the Stoic Journal asks each question (morning or evening), show quick reply buttons (ReplyKeyboardMarkup) with context-appropriate suggested answers. Users can tap a button instead of typing, speeding up the flow especially on mobile.

## User Story

As a Stoic Journal user,
I want quick reply buttons for each question,
so that I can tap my answer instead of typing and complete sessions faster.

## Acceptance Criteria

- [ ] Each Stoic question displays a ReplyKeyboardMarkup (quick reply) with 2–5 suggested options
- [ ] Options are context-appropriate per question (e.g. mood: "Good", "Okay", "Low"; yes/no: "Yes", "No", "Skip")
- [ ] User can still type a custom answer; quick reply is optional
- [ ] Works for both morning and evening sessions; quick mode and full mode
- [ ] Keyboard is removed or replaced when moving to next question
- [ ] No regression: existing free-text flow still works

## Business Value

Reduces friction and speeds up journaling. One-tap answers are faster than typing, especially on mobile. Aligns with Telegram quick reply UX (e.g. Photo OCR folder picker in US-045).

## Dependencies

- US-052 (World-Class Stoic Journaling) ✅
- US-019 (Stoic Journal) ✅

## History

- 2026-03-09 - Created
- 2026-03-10 - Assigned to Sprint 19; Status changed to ✅ Completed
