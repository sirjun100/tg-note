# Release Notes

Release notes for the Intelligent Joplin Librarian (Telegram-Joplin Bot). Date-based versioning. One entry per merge/push to main.

**Process**: See [project-management/docs/processes/release-notes-process.md](project-management/docs/processes/release-notes-process.md)

---

## 2026-03-08

### New Features
- **Command naming** — New canonical names: `tasks_*` (tasks_connect, tasks_status, tasks_config, etc.), `report_*` (report_daily, report_weekly, report_config). Old names kept as aliases.
- **Starred tasks first in reports** — Daily and weekly reports sort tasks with * at start to the top.
- **Report footer commands** — Footers now show `/report_daily`, `/report_weekly`, `/report_config` (updated from deprecated names).
- **Pre-commit hook** — `scripts/pre-commit` runs ruff and mypy before each commit. Install: `cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit`
- **"Who am I" profile query** — Plain messages like "who am i" or "what is my profile" now return your stored profile without routing through the LLM.
- **/bookmark feature request** — FR-051 added for saving URLs to Joplin with metadata and tags. [FR-051](project-management/backlog/features/FR-051-bookmark-command.md)

### Bug Fixes
- **Recipe paywall false positive** — Narrowed paywall detection: "subscribe" alone no longer flags recipe sites with newsletter CTAs. Now requires "subscribe to read/continue/unlock".
- **/recipe command** — New command to explicitly save recipes: paste text or send URL. Forces recipe template for pasted content and paywall fallbacks.
- **Recipe note truncation** — Fixed LLM response truncation when saving long recipes (e.g. carrot cake) that caused JSON parse failure on Fly. Increased max_tokens to 2500 for note generation.
- **Mypy return-value errors** — Fixed `_route_plain_message` exception handlers to return `True` instead of bare `return`.
- **Ruff lint** — Auto-fixed unused imports, import order, and other lint issues across tests.

### Breaking Changes
- (none this release)

### Migration Notes
- Old command names still work as aliases. New names preferred: `/report_daily` instead of `/daily_report`, `/report_config` instead of `/show_report_config`, etc.

---

## 2026-03-06

### New Features
- **Flashcard practice from notes** — /flashcard command with SM-2 spaced repetition, card extraction from #flashcard notes, session flow. [FR-033](project-management/backlog/features/FR-033-flashcard.md)
- **/project_new command** — Create project with default PARA folders (Overview, Backlog, Execution, Decisions, Assets, References) and initial Overview note. [FR-044](project-management/backlog/features/FR-044-project-new-command.md)
- **Star on task as high priority** — Tasks with * / ** / *** or ⭐ at start of title ranked as HIGH/CRITICAL/URGENT in reports. [FR-039](project-management/backlog/features/FR-039-star-on-task-as-high-priority.md)
- **Joplin ↔ Google Tasks project sync** — Feature request for syncing Joplin projects with Google Tasks (project = parent task, tasks = subtasks). [FR-034](project-management/backlog/features/FR-034-joplin-google-tasks-project-sync.md)

### Bug Fixes
- **/dream command crash** — Welcome message now uses plain text to avoid Markdown parse errors. [BF-017](project-management/backlog/bugs/BF-017-dream-command-crash.md)
- **/find command error** — get_folders try/except, HTML escape for user content, plain-text fallback. [BF-022](project-management/backlog/bugs/BF-022-find-command-flyio-error.md)
- **/ask command crash** — HTML escape for LLM/Joplin content, safe send with fallback, split long messages. [BF-023](project-management/backlog/bugs/BF-023-ask-command-crash.md)
- **Weekly report shows 0 notes/tasks** — Fixed by requesting completed tasks from Google Tasks API and explicit Joplin timestamp fields. [BF-018](project-management/backlog/bugs/BF-018-weekly-report-incorrect-numbers.md)
- **Dream analysis "Message is too long"** — Long analyses now split into multiple messages (Telegram 4096 char limit). [BF-019](project-management/backlog/bugs/BF-019-dream-message-too-long.md)

### Breaking Changes
- (none this release)

### Migration Notes
- (none this release)

---

## Template (for new releases)

```markdown
## YYYY-MM-DD

### New Features
- **Title** — Short description. [FR-XXX](project-management/backlog/features/FR-XXX-*.md)

### Bug Fixes
- **Title** — Short description. [BF-XXX](project-management/backlog/bugs/BF-XXX-*.md)

### Breaking Changes
- (none this release)

### Migration Notes
- (none this release)
```
