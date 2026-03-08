# User Story: US-044 - /project_new Command to Create Project with Default Folders

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 5
**Created**: 2026-03-06
**Updated**: 2026-03-06
**Assigned Sprint**: Sprint 15

## Description

Add a new command `/project_new <name-of-the-project>` that creates a project in Joplin under the Projects folder with all default subfolders. The default structure matches the PARA project template used in `ReorgOrchestrator`: Overview, Backlog, Execution, Decisions, Assets, References. This gives users a one-command way to spin up a new project without manually creating folders or running the full reorg flow.

## User Story

As a user who starts new projects frequently,
I want to run `/project_new name-of-the-project` and get a project folder with all default subfolders,
so that I can start capturing notes immediately without manual folder setup.

## Acceptance Criteria

### Creation

- [ ] `/project_new <name>` and `/pn <name>` create a project folder under **Projects** (always "Projects"; create if missing)
- [ ] Project path: `Projects/<name>/` with subfolders; name **normalized to kebab-case** (e.g. "Website Redesign" → `website-redesign`)
- [ ] Default subfolders: Overview, Backlog, Execution, Decisions, Assets, References (always; no custom list)
- [ ] **Initial Overview note**: Create "Project Overview" note in Overview folder with template (project name, date, placeholder sections)
- [ ] Success message: "✅ Created project 'X' with folders: Overview, Backlog, Execution, Decisions, Assets, References"
- [ ] `/project_new` or `/pn` without name shows usage

### Duplicate Handling (project already exists)

- [ ] Show message: "Project 'X' already exists. Use /find to search for notes in it."
- [ ] List existing subfolders
- [ ] If some default subfolders are missing: ask user whether to add them (inline buttons or reply)

### General

- [ ] Whitelist check; Joplin must be accessible; show error if not

## Business Value

- **Low friction**: One command instead of creating 7 folders manually
- **Consistency**: Every project gets the same structure (PARA-aligned)
- **Discovery**: Reuses the project template from `/reorg_init`; users who haven't run reorg can still create well-structured projects

## Technical Requirements

### 1. Default Folder Structure

Reuse `ReorgOrchestrator.PROJECT_SUBFOLDERS`:

```python
PROJECT_SUBFOLDERS = [
    "Overview",
    "Backlog",
    "Execution",
    "Decisions",
    "Assets",
    "References",
]
```

Path: `Projects/<project_name>/Overview`, `Projects/<project_name>/Backlog`, etc.

### 2. Projects Parent Folder

- Always use **"Projects"** (create if it doesn't exist via `get_or_create_folder_by_path`)

### 3. Implementation

- Register both `project_new` and `pn` as command handlers (same handler)
- **Option A — New handler in reorg or core**:
- Add `CommandHandler("project_new", _project_new(orch))` 
- Handler: parse name from `context.args`, validate, call `joplin_client.get_or_create_folder_by_path(["Projects", project_name])` then create each subfolder
- Or: add `create_project_with_default_folders(project_name)` to a service or `joplin_client`

**Option B — Extend ReorgOrchestrator**:
- Add `async def create_project(self, project_name: str) -> list[str]` that creates `Projects/<name>` and all subfolders
- Returns list of created folder IDs or paths
- Handler calls `orch.reorg_orchestrator.create_project(name)`

### 4. Name Normalization

- **Kebab-case**: "Website Redesign" → `website-redesign` (folder name)
- Trim whitespace; replace spaces with hyphens; lowercase; avoid special chars that break Joplin

### 5. Initial Overview Note

Create note in `Projects/<name>/Overview/` with template (industry best practice—concise, skimmable):

- **Title**: `<Project Name> - Overview`
- **Body**:
  ```
  # <Project Name>

  **Created**: <date>
  **Status**: Planning

  ## Goals
  - 

  ## Key Decisions
  - 

  ## Next Steps
  - 
  ```

### 6. Duplicate Handling

- Before creating, check if `Projects/<name>` already exists
- If exists: (A) Show "Project 'X' already exists. Use /find to search." (B) List existing subfolders (C) If default subfolders missing, ask user to add them (inline buttons or reply)

## Reference Documents

- [US-016: Joplin Database Reorganization](US-016-joplin-database-reorganization.md)
- [ReorgOrchestrator](../../../src/reorg_orchestrator.py) — `PROJECT_SUBFOLDERS`, `get_or_create_folder_by_path`
- [Reorg handler](../../../src/handlers/reorg.py) — "Duplicate that folder when you add a new project"
- [PARA Where to Put](../../../docs/para-where-to-put.md)

## Technical References

- `src/reorg_orchestrator.py` — `PROJECT_SUBFOLDERS`, `get_or_create_folder_by_path` usage
- `src/joplin_client.py` — `get_or_create_folder_by_path()`, `create_folder()`, `get_folders()`
- `src/handlers/reorg.py` — command registration pattern, whitelist
- `src/telegram_orchestrator.py` — handler registration

## Dependencies

- Joplin client (US-005) ✅
- ReorgOrchestrator or equivalent folder creation logic

## Design Decisions (2026-03-06)

- **Projects folder**: Always "Projects" (create if missing)
- **Alias**: Both `/project_new` and `/pn`
- **Subfolders**: Always default 6 (no custom list)
- **Initial Overview note**: Yes, with template (project name, date, placeholder sections)
- **Name normalization**: Kebab-case
- **Duplicate handling**: Message + list subfolders + ask to add missing subfolders

## Notes

- The reorg help text says "Duplicate that folder when you add a new project" — this command automates that
- Folder names with emoji or special chars: Joplin supports them; no need to strip unless problematic
- Consider adding to greeting/help command list once implemented

## Implementation Guide

**Sprint 15**: See [sprint-15-implementation-guide.md](../../sprints/sprint-15-implementation-guide.md) § US-044 for full `create_project()` and handler code. Key: `ReorgOrchestrator.create_project`, `get_or_create_folder_by_path`, `create_note`, register in `reorg.py`.

## History

- 2026-03-06 - Created
- 2026-03-06 - Design decisions: Projects only, /pn alias, kebab-case, Overview template, full duplicate handling; story points 5
