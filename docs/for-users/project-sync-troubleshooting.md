# Project Sync Troubleshooting

Common issues with Joplin ↔ Google Tasks project sync and how to fix them.

## Subtasks Not Appearing

**Symptom**: You create a task for a project or add a note with action items, but no subtask appears in Google Tasks.

**Checks**:

1. **Project sync enabled?** Run `/tasks_config` — project sync should show "✅ On". If not, run `/tasks_toggle_project_sync`.
2. **Parent task exists?** Run `/tasks_sync_projects` to create parent tasks for all Joplin project folders. If you created a new project folder after the last sync, run it again.
3. **Correct task list?** Ensure you're looking at the same Google Tasks list the bot uses. Check `/tasks_config` for the configured list.
4. **Google Tasks authorized?** Run `/tasks_status` — if it shows "Not connected", run `/tasks_connect`.

## Parent Task Missing

**Symptom**: You expect a parent task for a project but it doesn't exist in Google Tasks.

**Checks**:

1. **Run sync** — `/tasks_sync_projects` creates parent tasks for all project folders. Run it after adding new projects.
2. **Folder structure** — Project folders must be **direct children** of the Projects root. The bot looks for folders under `Projects`, `01 - projects`, or `project` (or the folder you set via `/tasks_set_projects_folder`).
3. **Wrong list** — Parent tasks are created in the list from `/tasks_config`. If you switched lists, run `/tasks_reset_project_sync` then `/tasks_sync_projects` to create fresh parents in the new list.

## No Projects Found

**Symptom**: `/tasks_sync_projects` says "No project folders found" or `/task` doesn't ask "Is this for a project?"

**Checks**:

1. **Projects root** — You need a folder named `Projects`, `01 - projects`, or `project` (case-insensitive). Create one if missing.
2. **Project folders** — Create folders as direct children of the Projects root. Use `/project_new MyProject` or create them manually in Joplin.
3. **Custom root** — If your structure differs, run `/tasks_set_projects_folder` and pick the folder that contains your projects.

## Wrong Task List

**Symptom**: Parent tasks or subtasks appear in the wrong Google Tasks list.

**Fix**:

1. Run `/tasks_reset_project_sync` — clears all project mappings.
2. Run `/tasks_set_list` and choose the correct list (e.g. "Projects").
3. Run `/tasks_sync_projects` — creates fresh parent tasks in the new list.
4. Optionally delete old parent tasks from the wrong list in Google Tasks (manual).

## Checking Logs and Database

### Logs

- **Console** — If running locally, check the terminal where `python main.py` runs. Errors are logged there.
- **Fly.io** — Run `fly logs` to see application logs.

### Database: `joplin_project_sync` Table

The bot stores mappings between Joplin folders and Google Tasks in the `joplin_project_sync` table:

| Column | Description |
|--------|-------------|
| `user_id` | Telegram user ID |
| `joplin_folder_id` | Joplin folder ID |
| `joplin_folder_title` | Folder title (used for rename detection) |
| `google_task_id` | Google Tasks parent task ID |
| `google_task_list_id` | Task list where the parent lives |

To inspect (SQLite). Default DB path is `data/bot/bot_logs.db` (or `LOGS_DB_PATH` from `.env`):

```bash
sqlite3 data/bot/bot_logs.db "SELECT * FROM joplin_project_sync;"
```

## Reset or Re-sync

If mappings are corrupted or you want to start fresh:

1. **Reset mappings** — `/tasks_reset_project_sync` clears all entries in `joplin_project_sync` for your user.
2. **Delete old parents** (optional) — In Google Tasks, manually delete the old parent tasks if they're in the wrong list.
3. **Re-sync** — `/tasks_sync_projects` creates new parent tasks and mappings.

**Note**: Resetting does not delete tasks in Google Tasks. It only clears the bot's mapping. You may need to delete orphaned parent tasks manually.
