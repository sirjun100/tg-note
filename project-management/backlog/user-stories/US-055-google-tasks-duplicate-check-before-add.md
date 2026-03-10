# User Story: US-055 - Google Tasks: Duplicate Check Before Add, Offer Edit/Priority/Cancel

[← Back to Product Backlog](../product-backlog.md)

**Status**: ⭕ Not Started
**Priority**: 🟡 Medium
**Story Points**: 5
**Created**: 2026-03-09
**Updated**: 2026-03-09
**Assigned Sprint**: Backlog

## Description

Before adding a new task to Google Tasks, the bot should look up the user's existing tasks to check if a similar task already exists. If a duplicate (or near-duplicate) is found, the bot should propose options: **edit** the existing task, **change priority** (e.g. star it), or **cancel** (don't add). This prevents duplicate tasks and gives users control when overlap is detected.

## User Story

As a user adding tasks via the bot,
I want the bot to check if the task already exists before adding,
so that I can choose to edit, change priority, or cancel instead of creating duplicates.

## Acceptance Criteria

- [ ] Before creating a Google Task, fetch user's existing tasks (from configured task list(s))
- [ ] Compare new task title/text against existing tasks (exact match or fuzzy/semantic similarity)
- [ ] If duplicate detected: show message with options — **Edit** existing, **Change priority**, **Cancel**
- [ ] **Edit**: Update existing task (e.g. add to notes, change due date, update title)
- [ ] **Change priority**: Star/unstar or set priority on existing task
- [ ] **Cancel**: Do not add; user keeps existing task as-is
- [ ] Applies to task creation flows: /task, braindump, content routing (task/both), planning, stoic

## Business Value

Reduces duplicate tasks. Users often re-send the same task or add similar items; detecting and offering edit/priority/cancel prevents clutter and gives control.

## Related

- [US-040](US-040-check-existing-task-note-update-append.md) — Broader story: duplicate check for **both** notes and tasks, with Update/Append/Create new. US-055 is the **tasks-only** slice with Edit/Priority/Cancel options. Consider implementing US-040 for full scope, or US-055 as a task-focused first step.
