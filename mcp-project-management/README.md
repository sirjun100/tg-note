# MCP Project Management Server

Exposes the project-management philosophy and processes as an MCP (Model Context Protocol) server for AI clients (Cursor, Claude Desktop, OpenCode, etc.).

## Features

- **Tools**: Validate backlog, metrics, check links, release notes, create user stories/defects/technical debt
- **Resources**: `pm://` URIs for INDEX, glossary, product backlog, processes, criteria, backlog items
- **Prompts**: Workflow templates for sprint planning, retrospectives, doc-code consistency, etc.
- **Bootstrap**: Creates `project-management/` structure when missing (any repo)

## Setup

### 1. Create virtual environment

```bash
cd mcp-project-management
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Configure MCP client

**Cursor** — Add to MCP settings (e.g. `~/.cursor/mcp.json` or project `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "project-management": {
      "command": "/path/to/mcp-project-management/.venv/bin/python",
      "args": ["-m", "mcp_project_management.server"],
      "cwd": "/path/to/your/repo"
    }
  }
}
```

**Claude Desktop** — Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "project-management": {
      "command": "/path/to/mcp-project-management/.venv/bin/python",
      "args": ["-m", "mcp_project_management.server"],
      "cwd": "/path/to/your/repo"
    }
  }
}
```

**OpenCode** — Similar MCP config; set `cwd` to your repo root.

### 3. Environment variables (optional)

- `PROJECT_ROOT` — Override project root (default: `cwd`)
- `PM_PATH` — Override project-management path (default: `project-management`)

## Tools

| Tool | Description |
|------|-------------|
| `validate_backlog` | Validate backlog structure, naming, cross-refs |
| `backlog_metrics` | Backlog health, aging, velocity |
| `check_links` | Check markdown links |
| `generate_release_notes_draft` | Draft from commits (supports `--auto`) |
| `validate_backlog_integrity` | Orphan refs, duplicates, Fibonacci |
| `visualize_dependencies` | Mermaid dependency graph |
| `lint_project_management` | Full lint |
| `prepare_gap_check` | Pre-commit doc-code consistency reminder |
| `create_user_story` | Create US-XXX and add to backlog |
| `create_defect` | Create DEF-XXX and add to backlog |
| `create_technical_debt` | Create TD-XXX and add to backlog |

## Resources (pm://)

- `pm://index` — Project Management Index
- `pm://glossary` — Terminology
- `pm://product-backlog` — Product backlog
- `pm://processes/{name}` — Process docs
- `pm://criteria/{name}` — DoR, DoD, etc.
- `pm://backlog/user-stories` — List all user stories
- `pm://backlog/user-stories/{id}` — User story by ID
- `pm://backlog/defects` — List all defects
- `pm://backlog/defects/{id}` — Defect by ID
- `pm://sprints` — List all sprints
- `pm://sprints/{id}` — Sprint by ID

## Run manually

```bash
python -m mcp_project_management.server
```

Uses stdio transport by default (for MCP clients).
