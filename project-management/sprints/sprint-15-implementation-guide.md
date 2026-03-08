# Sprint 15 Implementation Guide — LLM-Ready Reference

**Purpose**: This document provides all context an LLM needs to implement Sprint 15 without asking questions. Read this before coding.

**Sprint Plan**: [sprint-15-stability-and-project-foundation.md](sprint-15-stability-and-project-foundation.md)

---

## Quick Start (for LLM)

1. **DEF-022**: Verify `src/handlers/search.py` has the fix (grep DEF-022); add unit tests; test in production.
2. **DEF-023**: Edit `src/handlers/ask.py` — add `html.escape`, `_send_ask_response_safe`, `split_message_for_telegram`; replace lines 60–66.
3. **US-044**: Add `create_project` to `src/reorg_orchestrator.py`; add `_project_new` handler in `src/handlers/reorg.py`; register `project_new` and `pn`; update greeting in `src/handlers/core.py`.
4. **US-039**: Add `URGENT` to `PriorityLevel`, `_detect_star_priority`, update `create_google_task_item` and `_build_routing_system_prompt` in `src/report_generator.py` and `src/llm_orchestrator.py`.

All code snippets, line numbers, and patterns are in the sections below.

---

## 1. DEF-022: /find Command Fix — VERIFY (Implementation May Exist)

### Current State

**File**: `src/handlers/search.py`

The fix may already be implemented. Check for:
- Lines 118–124: `get_folders()` wrapped in `try/except`; on failure `folder_by_id = {}`
- Lines 126–144: `html.escape()` for `query`, `title`, `folder_name`, `snippet`
- Lines 53–76: `_send_search_results_safe()` — HTML send with plain-text fallback on parse error

### Verification Tasks

1. **Confirm implementation**: Grep for `DEF-022` in `src/handlers/search.py` — comments should reference it.
2. **Unit tests**: Add to `tests/test_search.py` (or create):
   - `test_search_folders_failure_returns_results_with_unknown` — mock `get_folders` to raise; assert results still sent, folder shows "Unknown"
   - `test_search_special_chars_in_title_no_parse_error` — search returns note with title containing `*`, `_`, `` ` ``; assert no BadRequest
3. **Production**: Run `/find test` on Fly.io; confirm results returned without error.

### Reference Pattern (if re-implementing)

Copy from `src/handlers/core.py` lines 125–149 (`_greeting_to_plain`, `_send_greeting_safe`) or `src/handlers/search.py` lines 46–76 (`_search_html_to_plain`, `_send_search_results_safe`).

---

## 2. DEF-023: /ask Command Fix — IMPLEMENT

### Problem

`src/handlers/ask.py` lines 60–66 build response with `parse_mode="Markdown"` and **no escaping**. LLM `answer` and Joplin `source titles` can contain `*`, `_`, `` ` ``, `[`, `]` → Telegram `BadRequest: Can't parse entities`.

### Exact Fix

**File**: `src/handlers/ask.py`

1. **Add imports** (top of file):
   ```python
   import html
   from src.security_utils import split_message_for_telegram
   ```

2. **Add helper** (before `_ask`):
   ```python
   def _ask_html_to_plain(html_text: str) -> str:
       """Strip HTML for plain-text fallback (DEF-023)."""
       import re
       out = re.sub(r"</?b>", "", html_text)
       out = re.sub(r"</?i>", "", out)
       return out.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

   async def _send_ask_response_safe(message, msg_html: str) -> None:
       """Send /ask response with HTML; fallback to plain; split if > 4096 chars (DEF-023)."""
       plain = _ask_html_to_plain(msg_html)
       if len(msg_html) > 4096:
           for chunk in split_message_for_telegram(plain):
               await message.reply_text(chunk)
           return
       try:
           await message.reply_text(msg_html, parse_mode="HTML")
       except Exception as exc:
           exc_str = str(exc).lower()
           is_parse = "parse" in exc_str or "entities" in exc_str or "badrequest" in type(exc).__name__.lower()
           if is_parse:
               for chunk in split_message_for_telegram(plain):
                   await message.reply_text(chunk)
               return
           raise
   ```

3. **Replace lines 60–66** in `_ask` handler:
   ```python
   # Build response with HTML + escape (DEF-023)
   q_esc = html.escape(question)
   lines = [f"🔍 <b>{q_esc}</b>\n", html.escape(answer)]
   if sources:
       lines.append("\n📚 <b>Sources:</b>")
       for s in sources[:5]:
           lines.append(f"• \"{html.escape(s['title'])}\"")
   response = "\n".join(lines)
   await _send_ask_response_safe(msg, response)
   ```

4. **Usage message** (lines 41–46): Already uses Markdown for static text; optional: switch to HTML for consistency (`<code>`, `&lt;`, `&gt;`).

### References

- [DEF-023](../backlog/defects/DEF-023-ask-command-crash.md)
- [DEF-010](../backlog/defects/DEF-010-greeting-parse-entities-error.md) — same pattern
- [DEF-022](../backlog/defects/DEF-022-find-command-flyio-error.md) — same pattern
- `src/handlers/search.py` lines 53–76
- `src/security_utils.py` `split_message_for_telegram` (DEF-019)
- `src/constants.py` `TELEGRAM_MESSAGE_MAX_LENGTH = 4096`

---

## 3. US-044: /project_new Command — IMPLEMENT

### Overview

Add `/project_new <name>` and `/pn <name>` that create `Projects/<name>/` with subfolders: Overview, Backlog, Execution, Decisions, Assets, References, plus an initial Overview note.

### Implementation Location

**Option B (recommended)**: Extend `ReorgOrchestrator` and add handler in `reorg.py`.

### Step 1: ReorgOrchestrator.create_project

**File**: `src/reorg_orchestrator.py`

Add method:

```python
async def create_project(self, project_name: str) -> dict[str, Any]:
    """
    Create project under Projects/ with default subfolders and Overview note.
    Returns: {"project_folder_id": str, "overview_note_id": str, "subfolders": list[str]}
    Raises: ReorgException if project already exists.
    """
    import re
    from datetime import datetime

    # Normalize: kebab-case
    normalized = re.sub(r'[^a-zA-Z0-9\s-]', '', project_name).strip()
    normalized = normalized.lower().replace(' ', '-').replace('--', '-').strip('-')
    if not normalized:
        raise ReorgException("Invalid project name")

    # Check if Projects/<normalized> exists
    folders = await self.joplin_client.get_folders()
    projects_id = None
    for f in folders:
        if (f.get("title") or "").lower() == "projects" and (f.get("parent_id") or "") == "":
            projects_id = f["id"]
            break
    if not projects_id:
        projects_id = await self.joplin_client.get_or_create_folder_by_path(["Projects"])

    # Check for existing project
    for f in folders:
        if f.get("parent_id") == projects_id and (f.get("title") or "").lower() == normalized:
            raise ReorgException(f"Project '{project_name}' already exists")

    # Create project folder and subfolders
    project_folder_id = await self.joplin_client.get_or_create_folder_by_path(["Projects", normalized])
    overview_id = await self.joplin_client.get_or_create_folder_by_path(["Projects", normalized, "Overview"])

    for sub in self.PROJECT_SUBFOLDERS:
        if sub != "Overview":
            await self.joplin_client.get_or_create_folder_by_path(["Projects", normalized, sub])

    # Create Overview note
    now = datetime.now().strftime("%Y-%m-%d")
    body = f"""# {project_name}

**Created**: {now}
**Status**: Planning

## Goals
- 

## Key Decisions
- 

## Next Steps
- 
"""
    note_id = await self.joplin_client.create_note(overview_id, f"{project_name} - Overview", body)

    return {
        "project_folder_id": project_folder_id,
        "overview_note_id": note_id,
        "subfolders": list(self.PROJECT_SUBFOLDERS),
    }
```

### Step 2: Handler in reorg.py

**File**: `src/handlers/reorg.py`

1. Add handler:
   ```python
   def _project_new(orch: TelegramOrchestrator):
       async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
           user = update.effective_user
           if not user or not check_whitelist(user.id):
               return
           if not update.message:
               return

           name = " ".join(context.args).strip() if context.args else ""
           if not name:
               await update.message.reply_text(
                   "📁 <b>Create Project</b>\n\n"
                   "Usage: /project_new &lt;name&gt; or /pn &lt;name&gt;\n"
                   "Example: /project_new Website Redesign",
                   parse_mode="HTML",
               )
               return

           try:
               result = await orch.reorg_orchestrator.create_project(name)
               subs = ", ".join(result["subfolders"])
               await update.message.reply_text(
                   f"✅ Created project '{name}' with folders: {subs}",
                   parse_mode="HTML",
               )
           except Exception as e:
               err = str(e)
               if "already exists" in err.lower():
                   await update.message.reply_text(
                       f"ℹ️ {err}\n\nUse /find to search for notes in it."
                   )
               else:
                   await update.message.reply_text(f"❌ Error: {err}")
                   logger.error("project_new failed: %s", e, exc_info=True)
       return handler
   ```

2. Register in `register_reorg_handlers`:
   ```python
   application.add_handler(CommandHandler("project_new", _project_new(orch)))
   application.add_handler(CommandHandler("pn", _project_new(orch)))
   ```

### Step 3: Greeting Update

**File**: `src/handlers/core.py`

In `_build_greeting()` (around line 97), add under **📝 Capture** or create **📁 Projects** section:
```
"• /project_new &lt;name&gt; or /pn &lt;name&gt; → Create project with default folders\n"
```

### API Reference

- `JoplinClient.get_or_create_folder_by_path(path_parts: list[str]) -> str` — `src/joplin_client.py` line 223
- `JoplinClient.create_note(folder_id, title, body) -> str` — `src/joplin_client.py` line 132
- `JoplinClient.get_folders()` — returns list of `{id, title, parent_id}`
- `ReorgOrchestrator.PROJECT_SUBFOLDERS` — `["Overview", "Backlog", "Execution", "Decisions", "Assets", "References"]` — line 52

### Duplicate Handling (Simplified)

US-044 full spec says: if exists, list subfolders and optionally ask to add missing ones. For MVP: show "Project X already exists. Use /find to search." The `create_project` raises `ReorgException` with that message when folder exists.

---

## 4. US-039: Star on Task as High Priority — IMPLEMENT

### Overview

Tasks with `*`, `**`, `***` (or ⭐/★) at the **beginning** of the title get priority: `*`=HIGH, `**`=CRITICAL, `***`=URGENT. Star **always wins** over due-date inference. Apply to reports and all task displays.

### Step 1: PriorityLevel and Star Detection

**File**: `src/report_generator.py`

1. Add `URGENT` to enum (after line 44):
   ```python
   class PriorityLevel(Enum):
       CRITICAL = 5
       HIGH = 3
       MEDIUM = 1
       LOW = 0
       URGENT = 6   # US-039: *** at start of title
   ```

2. Add to `_priority_label` (around line 1007):
   ```python
   labels = {
       PriorityLevel.URGENT: "🔥 Urgent",
       PriorityLevel.CRITICAL: "🔴 Critical",
       ...
   }
   ```

3. Add helper (before `create_google_task_item`):
   ```python
   def _detect_star_priority(self, title: str) -> PriorityLevel | None:
       """US-039: Detect * / ** / *** or ⭐/★ at start of title. Star wins over due date."""
       if not title or not isinstance(title, str):
           return None
       t = title.strip()
       if t.startswith("***") or t.startswith("⭐⭐⭐") or t.startswith("★★★"):
           return PriorityLevel.URGENT
       if t.startswith("**") or t.startswith("⭐⭐") or t.startswith("★★"):
           return PriorityLevel.CRITICAL
       if t.startswith("*") or t.startswith("⭐") or t.startswith("★"):
           return PriorityLevel.HIGH
       return None
   ```

### Step 2: create_google_task_item

**File**: `src/report_generator.py` — `create_google_task_item` (line 372)

Replace the priority logic (around line 388):
```python
# US-039: Star at start of title wins over due date
title = task.get("title", "Untitled Task")
star_priority = self._detect_star_priority(title)
if star_priority is not None:
    priority_level = star_priority
else:
    priority_level = PriorityLevel.HIGH if is_overdue else PriorityLevel.MEDIUM
```

### Step 3: Routing Prompt

**File**: `src/llm_orchestrator.py` — `_build_routing_system_prompt` (line 857)

Add before "For task.due_date:" (around line 915):
```
For task: Star at **beginning** of task text means priority — * or ⭐ = important (HIGH), ** = critical (CRITICAL), *** = urgent (URGENT). Include the star in the task title when user intends priority.
```

### Step 4: Task Creation and Display

- **`/task` handler**: Preserves user input; no change if user types `/task * Buy milk` — title is passed through.
- **Content routing**: The routing prompt update ensures LLM includes star when user implies priority.
- **Other task displays**: Ensure any code that builds task lists for `/find`, `/list`, or reports uses `create_google_task_item` or equivalent logic. The report generator is the main consumer; daily/weekly/monthly reports use it.

### Categorization

**File**: `src/report_generator.py` — `categorize_items` (line 429)

Add handling for `PriorityLevel.URGENT`:
```python
elif item.priority_level == PriorityLevel.URGENT:
    report.critical_items.append(item)  # or add report.urgent_items if you add that
```
Per US-039, URGENT > CRITICAL, so urgent items can go in `critical_items` (top of report) or you add an `urgent_items` section. Simplest: treat URGENT like CRITICAL for categorization.

### References

- [US-039](../backlog/user-stories/US-039-star-on-task-as-high-priority.md)
- `src/report_generator.py` — `create_google_task_item`, `_priority_label`, `categorize_items`
- `src/llm_orchestrator.py` — `_build_routing_system_prompt`

---

## 5. Cross-Reference Summary

| Item   | Primary File           | Key Methods/Patterns                                      |
|--------|------------------------|-----------------------------------------------------------|
| DEF-022 | `handlers/search.py`   | `_send_search_results_safe`, `html.escape`, try/except   |
| DEF-023 | `handlers/ask.py`      | `html.escape`, `split_message_for_telegram`, safe send    |
| US-044 | `reorg_orchestrator.py`, `handlers/reorg.py` | `create_project`, `get_or_create_folder_by_path`, `create_note` |
| US-039 | `report_generator.py`, `llm_orchestrator.py` | `_detect_star_priority`, `create_google_task_item`, routing prompt |

---

## 6. Handler Registration

**File**: `src/telegram_orchestrator.py`

US-044 handlers are added inside `register_reorg_handlers` — no change to `telegram_orchestrator.py` needed.

---

## 7. Tests to Add

- **DEF-022**: `tests/test_search.py` — folder failure, special chars
- **DEF-023**: `tests/test_ask.py` — HTML escape, long message split, parse fallback
- **US-044**: `tests/test_reorg_orchestrator.py` — `create_project` with mock Joplin
- **US-039**: `tests/test_report_generator.py` — `_detect_star_priority`, star wins in `create_google_task_item`

---

## 8. Definition of Done Checklist

- [ ] All acceptance criteria met per story
- [ ] Unit tests added/updated
- [ ] No new linter errors
- [ ] Documentation: README, /help, greeting updated
- [ ] [RELEASE_NOTES.md](../../RELEASE_NOTES.md) updated
- [ ] Doc-code consistency review run
