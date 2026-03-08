# User Story: US-020 - Marketing-Focused README for Project Root

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 3
**Created**: 2026-03-03
**Updated**: 2026-03-03
**Assigned Sprint**: Backlog

## Description

Rewrite the root `README.md` to be marketing-focused rather than technical. The current README leads with architecture diagrams and file trees, which is appropriate for developers but alienating for potential users. The new README should sell the *why* — explaining the benefits of combining GTD (Getting Things Done) with Second Brain methodology, and how this bot makes both systems effortless through a Telegram interface.

## User Story

As a potential user visiting the GitHub repository,
I want to immediately understand what this bot does for me and why I need it,
so that I can decide to try it without reading technical documentation first.

## Acceptance Criteria

- [x] README opens with a compelling value proposition, not a feature list
- [x] Explains the GTD + Second Brain methodology in accessible terms
- [x] Uses the CODE (Capture, Organize, Distill, Express) and PARA frameworks as selling points
- [x] Shows concrete before/after scenarios (what life looks like without vs with the bot)
- [x] Includes a "How It Works" section with conversational examples
- [x] Technical setup instructions moved below the fold (still present but secondary)
- [x] Architecture and file tree removed from README (lives in developer docs)
- [x] Bot commands presented as capabilities, not a CLI reference
- [x] Links to detailed documentation for developers, business analysts, and users

## Business Value

The README is the first thing anyone sees. A marketing-focused README:
- Increases adoption by helping users understand value before complexity
- Reduces bounce rate from the repository page
- Makes the project feel polished and user-centric
- Attracts contributors who understand the vision

## Reference Documents

- Second Brain infographic (CODE workflow + PARA method)
- `docs/for-users/gtd-second-brain-workflow.md` — detailed GTD + Second Brain workflow
- `docs/para-where-to-put.md` — PARA decision framework

## Technical References

- File: `README.md` (root)
- Docs: `docs/README.md`, `docs/for-users/README.md`

## Dependencies

- GTD + Second Brain workflow documentation (completed)

## History

- 2026-03-03 - Created and implemented
