# Project Sync Smoke Test (Manual)

Use this checklist to verify the full project sync flow in production (real Joplin + Google Tasks).

## Prerequisites

- Bot running (`python main.py`)
- Joplin running with Web Clipper enabled
- Google Tasks authorized (`/tasks_connect` completed)
- At least one project folder in Joplin (e.g. create via `/project_new TestProject`)

## Automated Tests (no real APIs)

Run before manual verification:

```bash
./scripts/smoke_project_sync.sh
```

Or directly:

```bash
pytest tests/test_task_service.py tests/test_project_sync_integration.py -v --tb=short
```

## Manual Production Verification

### 1. Enable project sync

- [ ] Send `/tasks_toggle_project_sync` → expect "Project sync: ✅ On"
- [ ] Send `/tasks_config` → verify project sync status shown

### 2. Initial sync

- [ ] Create 2+ project folders in Joplin (e.g. `/project_new Test1`, `/project_new Test2`)
- [ ] Send `/tasks_sync_projects` → expect "Created: 2 parent task(s)" (or "Already existed: N")
- [ ] Open Google Tasks → verify parent tasks "Test1", "Test2" exist in your configured list

### 3. Task for project (explicit /task)

- [ ] Send `/task Call client about proposal`
- [ ] Bot asks "Is this for a project?" with project list
- [ ] Select a project (e.g. Test1) via button or reply with number
- [ ] Open Google Tasks → verify "Call client about proposal" appears as **subtask** under "Test1"

### 4. Note in project → subtask (braindump / action extraction)

- [ ] Create a note inside a project folder (e.g. Projects/Test1) with action text like "todo: Review proposal"
- [ ] Or use `/braindump`, place note in a project folder, include action items
- [ ] Open Google Tasks → verify extracted task appears as **subtask** under the project parent

### 5. Stalled projects (reports)

- [ ] Create a parent task with no subtasks (or complete all subtasks)
- [ ] Send `/report_daily` or `/report_weekly`
- [ ] Verify "⚠️ Projects with no next actions: ..." lists stalled projects

### 6. Reset and re-sync

- [ ] Send `/tasks_reset_project_sync` → mappings cleared
- [ ] Send `/tasks_sync_projects` → fresh parent tasks created
- [ ] Verify in Google Tasks: old parents may remain (delete manually if needed); new sync creates new parents

## Success Criteria

- Parent tasks in Google Tasks match Joplin project folders
- Tasks created for a project appear as subtasks under the correct parent
- Stalled projects appear in daily/weekly reports
- Reset clears mappings; re-sync creates fresh parents
