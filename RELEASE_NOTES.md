# Release Notes

Release notes for the Intelligent Joplin Librarian (Telegram-Joplin Bot). Date-based versioning. One entry per merge/push to main.

**Process**: See [project-management/docs/processes/release-notes-process.md](project-management/docs/processes/release-notes-process.md)

---

## 2026-03-06

### New Features
- **Joplin ↔ Google Tasks project sync** — Feature request for syncing Joplin projects with Google Tasks (project = parent task, tasks = subtasks). [FR-034](project-management/backlog/features/FR-034-joplin-google-tasks-project-sync.md)

### Bug Fixes
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
