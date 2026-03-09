# Project Sync: Joplin ↔ Google Tasks

Project sync keeps your Joplin project folders and Google Tasks in sync. Each Joplin project folder becomes a **parent task** in Google Tasks; tasks you create for that project appear as **subtasks** under that parent.

## What Project Sync Does

| Joplin | Google Tasks |
|--------|--------------|
| Project folder (e.g. `Projects/Q1 Planning`) | Parent task "Q1 Planning" |
| Task created for that project | Subtask under "Q1 Planning" |
| Note in project with action items | Extracted tasks as subtasks under the parent |

This keeps your GTD action list organized by project. When you create a task via `/task` or when the bot extracts actions from a note in a project folder, those tasks appear under the correct project parent in Google Tasks.

## How to Enable

1. **Connect Google Tasks** — Run `/tasks_connect` and complete OAuth if you haven't already.
2. **Enable project sync** — Run `/tasks_toggle_project_sync`. You should see "Project sync: ✅ On".
3. **Verify** — Run `/tasks_config` to confirm project sync is enabled.

## Folder Naming

The bot looks for project folders under a **Projects root**. By default it uses a folder named:

- `Projects`, or
- `01 - projects`, or
- `project`

Create project folders as **direct children** of that root. For example:

```
Projects/                    ← Projects root (default)
├── Q1 Planning              ← Project folder → parent task in Google Tasks
├── Home Office Renovation   ← Project folder → parent task
└── Learn to Sing Harmonies  ← Project folder → parent task
```

If your structure differs, use `/tasks_set_projects_folder` to choose which Joplin folder is the Projects root.

## Commands

| Command | Description |
|---------|-------------|
| `/tasks_toggle_project_sync` | Turn project sync on or off |
| `/tasks_sync_projects` | Create parent tasks in Google Tasks for all Joplin project folders |
| `/tasks_reset_project_sync` | Clear all mappings (use before re-syncing to a different list) |
| `/tasks_set_projects_folder` | Choose which Joplin folder is the Projects root |

## Where to Find Created Subtasks

1. Open **Google Tasks** (web or app).
2. Select the task list you configured (e.g. "My Tasks" or "Projects").
3. Parent tasks appear at the top level; expand them to see subtasks.
4. Tasks created for a project appear as subtasks under the matching parent.

## Stalled Projects in Reports

The daily and weekly reports (`/report_daily`, `/report_weekly`) include a **stalled projects** section: projects that have a parent task in Google Tasks but **no incomplete subtasks**. This helps you spot projects that need a next action.

Example:

```
⚠️ Projects with no next actions: Q1 Planning, Home Office Renovation
```

## Quick Start

1. `/tasks_toggle_project_sync` → enable
2. Create project folders in Joplin (e.g. `/project_new MyProject`)
3. `/tasks_sync_projects` → creates parent tasks in Google Tasks
4. `/task Call client` → select project when asked → task appears as subtask
5. Create a note in a project with "todo: Review proposal" → extracted task appears as subtask

## Troubleshooting

See [Project Sync Troubleshooting](project-sync-troubleshooting.md) for common issues (subtasks not appearing, parent missing, wrong list), how to check logs and the `joplin_project_sync` table, and how to reset or re-sync.
