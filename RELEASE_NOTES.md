# Release Notes

Release notes for the Intelligent Joplin Librarian (Telegram-Joplin Bot). Date-based versioning. One entry per merge/push to main.

**Process**: See [project-management/docs/processes/release-notes-process.md](project-management/docs/processes/release-notes-process.md)

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
