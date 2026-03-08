# MCP Project Management Server — Implementation Plan

## Goal

Expose the project-management philosophy and processes as an MCP (Model Context Protocol) server so any MCP client (Cursor, Claude Desktop, OpenCode, etc.) can use tools, resources, and prompts without manually attaching files.

**Scope decisions** (from user):
- Works with all AI clients (Claude, Cursor, OpenCode)
- Works for **any repo**; if `project-management/` doesn't exist, **create it**
- Project root from `cwd`; configurable path via env
- All 8 script tools; expose `--auto` for release notes
- All resources; list all user stories (and defects, sprints)
- Prompts: best-judgment content size; **add tools that write files**
- Dedicated venv; Python 3.10+

---

## Architecture

```
<repo-root>/
├── project-management/          # created by MCP if missing
│   ├── scripts/*.sh            # copied from package or repo
│   ├── processes/*.md
│   ├── backlog/
│   ├── templates/
│   └── criteria/
└── mcp-project-management/     # MCP package (can live in any repo)
    ├── pyproject.toml
    ├── src/mcp_project_management/
    │   ├── __init__.py
    │   ├── server.py
    │   ├── tools.py            # script tools + file-writing tools
    │   ├── resources.py
    │   ├── prompts.py
    │   └── bootstrap.py        # create project-management/ structure
    ├── data/                   # bundled templates for bootstrap
    │   ├── product-backlog-template.md
    │   ├── user-story-template.md
    │   ├── defect-template.md
    │   ├── technical-debt-template.md
    │   └── index.md
    ├── PLAN.md
    └── README.md
```

**Project root**: From `PROJECT_ROOT` env or `cwd`. MCP config sets `cwd` to repo.
**Project-management path**: From `PM_PATH` env or default `project-management/` (relative to project root).

---

## 1. Tools

### Script tools (8)

| Tool | Script | Arguments |
|------|--------|-----------|
| `validate_backlog` | validate-backlog.sh | `backlog_dir` |
| `backlog_metrics` | backlog-metrics.sh | `stats` (bool), `backlog_dir`, `sprints_dir` |
| `check_links` | check-links.sh | `scan_dir`, `base_dir` |
| `generate_release_notes_draft` | generate-release-notes-draft.sh | `commit_count`, `auto` (bool), `dry_run` (bool) — **expose --auto** |
| `validate_backlog_integrity` | validate-backlog-integrity.sh | `backlog_dir` |
| `visualize_dependencies` | visualize-dependencies.sh | `backlog_dir` |
| `lint_project_management` | lint-project-management.sh | (none) |
| `prepare_gap_check` | prepare-gap-check.sh | (none) |

**Script runner**: `subprocess.run()` with `cwd=project_root`, `capture_output=True`, `text=True`, `timeout=60`. Project root from `PROJECT_ROOT` env or `Path.cwd()`.

### File-writing tools (3)

| Tool | Purpose |
|------|---------|
| `create_user_story` | Create US-XXX file from template, add row to product-backlog |
| `create_defect` | Create DEF-XXX file from template, add row to product-backlog |
| `create_technical_debt` | Create TD-XXX file from template, add row to product-backlog |

**Logic**:
- Resolve next ID by scanning existing files (US-001, US-002, ...)
- Fill template with user-provided fields (title, description, acceptance_criteria, priority, story_points, etc.)
- Write to `backlog/user-stories/US-XXX-slug.md` (slug from title)
- Append table row to product-backlog.md (parse table, insert row, write back)
- If project-management/ missing: run `ensure_project_management()` first

**ensure_project_management()**: Create folder structure + minimal files. Use `importlib.resources.files()` to read bundled data from package. Create: backlog/, user-stories/, defects/, technical-debt/, retrospective-improvements/, processes/, templates/, criteria/, sprints/, architecture-decision-records/, scripts/. Copy bundled templates to templates/, scripts to scripts/, product-backlog.md to backlog/. Bundle: user-story-template, defect-template, technical-debt-template, product-backlog-template, INDEX.md, README.md, and all 9 scripts. Ensures "any repo" works without cloning ai-workflow-template.

---

## 2. Resources (URI patterns)

| URI | Content |
|-----|---------|
| `pm://index` | INDEX.md |
| `pm://glossary` | glossary.md |
| `pm://product-backlog` | backlog/product-backlog.md |
| `pm://processes/{process}` | processes/{process}.md |
| `pm://criteria/{criteria}` | criteria/{criteria}.md |
| `pm://backlog/user-stories/{id}` | First matching user-stories/{id}*.md |
| `pm://backlog/defects/{id}` | First matching defects/{id}*.md |
| `pm://sprints/{id}` | First matching sprints/{id}*.md |
| `pm://backlog/user-stories` | **List all** user story IDs and titles (for discovery) |
| `pm://backlog/defects` | **List all** defect IDs and titles |
| `pm://sprints` | **List all** sprint IDs and names |

---

## 3. Prompts (8)

| Prompt | Args | Purpose |
|--------|------|---------|
| `create_user_story` | description, acceptance_criteria?, dependencies? | Create US from template |
| `create_defect` | description, steps_to_reproduce?, priority? | Create DEF from template |
| `run_documentation_code_consistency_check` | — | Doc-code consistency workflow |
| `generate_release_notes` | commit_count? | Release notes workflow |
| `refine_backlog_item` | item_id | DoR checklist |
| `start_sprint_planning` | sprint_number, velocity? | Sprint planning workflow |
| `run_sprint_retrospective` | sprint_number | Retrospective workflow |
| `identify_technical_debt` | description | Technical debt item creation |

---

## 4. Implementation Order

1. **Project structure** — pyproject.toml, package layout, `__init__.py`, `data/` with bundled files
2. **Bootstrap** — `ensure_project_management()`, copy bundled templates + scripts
3. **Script runner** — `run_script()` helper, project root resolution, call ensure before scripts
4. **Script tools** — All 8 tools with correct script args
5. **File-writing tools** — `create_user_story`, `create_defect`, `create_technical_debt`
6. **Resources** — All URI patterns including list endpoints (`pm://backlog/user-stories` etc.)
7. **Prompts** — All 8 prompts with excerpted content (token-efficient)
8. **Server** — `server.py` entry point, imports to register components
9. **venv + README** — Setup instructions, Cursor/Claude/OpenCode config

---

## 5. Dependencies

- `fastmcp>=3.0.0` (Python 3.10+)

---

## 6. Cursor MCP Config

```json
{
  "mcpServers": {
    "project-management": {
      "command": "python",
      "args": ["-m", "mcp_project_management.server"],
      "cwd": "/Volumes/T7/src/ai-workflow-template",
      "env": {}
    }
  }
}
```

With venv: use full path to venv's `python` in `command`.

---

## 7. Risks / Notes

- **Script args**: `backlog-metrics.sh` has complex arg parsing (--stats, positional). Pass args in correct order.
- **generate-release-notes-draft**: `--auto` and `--dry-run` are mutually exclusive. Order: flags first, then N.
- **Project root**: Prefer `PROJECT_ROOT` env; fallback to `Path.cwd()` when MCP runs with cwd=repo.
- **Bootstrap scripts**: Scripts expect `project-management/` layout. Bundled scripts must use same paths.
- **Product-backlog parsing**: Table parsing for "add row" is fragile. Use regex or simple line-by-line to find table end, insert row.
- **ID generation**: Scan `user-stories/`, `defects/`, `technical-debt/` for max US-NNN, DEF-NNN, TD-NNN; next = max+1.
