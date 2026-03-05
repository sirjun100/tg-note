# Brain Dump Quick Reference Card

**For:** Rapid onboarding and lookup during implementation

---

## File Map

```
src/handlers/braindump.py
├─ register_braindump_handlers()     [Registration point]
├─ _braindump(orch)                  [/braindump command handler]
├─ _braindump_stop(orch)             [/braindump_stop command handler]
├─ handle_braindump_message(...)     [Message processing loop - MAIN]
└─ _finish_session(...)              [Session finalization & note save]

src/prompts/gtd_expert.txt
└─ GTD expert system prompt          [Persona definition]

src/llm_orchestrator.py
├─ LLMOrchestrator
│  └─ async process_message(...)     [LLM call wrapper]
└─ JoplinNoteSchema                  [Response model]

src/handlers/core.py
├─ create_note_in_joplin(...)        [Note creation]
└─ Message router → handle_braindump_message()  [Dispatcher]
```

---

## Command Summary

| Command | Handler | Action |
|---------|---------|--------|
| `/braindump` | `_braindump()` | Start session, create state, ask first Q |
| `/capture` | `_braindump()` | Alias for `/braindump` |
| `/braindump_stop` | `_braindump_stop()` | Stop session, generate summary, save |
| Any message | `handle_braindump_message()` | Process message, call LLM, continue or finish |

---

## State Structure

```python
{
    "active_persona": "GTD_EXPERT",          # Identifies brain dump
    "session_start": "2026-03-04T10:30:00",  # ISO timestamp
    "captured_items": [],                     # Legacy (unused)
    "conversation_history": [                 # All turns
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
    ],
    "final_note": {                          # Set on completion
        "title": "Brain Dump - March 4",
        "body": "## Work\n- Item",
        "parent_id": "folder_id",
        "tags": ["brain-dump"]
    }
}
```

---

## Message Flow

```
User Input
    ↓
Core router checks: active_persona == "GTD_EXPERT"?
    ↓ YES
handle_braindump_message(orch, user_id, text, message)
    ├─► Get state
    ├─► Build history
    ├─► Call: orch.llm_orchestrator.process_message(
    │       user_message=text,
    │       persona="gtd_expert",
    │       history=history
    │   )
    ├─► Check status:
    │   ├─ "NEED_INFO" → Ask next Q, update state
    │   ├─ "SUCCESS" → Call _finish_session(note_data)
    │   └─ ERROR → Log error, ask user to retry
    └─► (Exit function)
```

---

## LLM Response Schema

```python
JoplinNoteSchema {
    status: str              # "NEED_INFO" or "SUCCESS"
    confidence_score: float  # 0.0 - 1.0 (only "NEED_INFO" < 0.9)
    question: str | None     # Next Q (required if NEED_INFO)
    log_entry: str           # Debug: phase/decision
    note: dict | None        # Final note (required if SUCCESS)
}
```

**NEED_INFO Response:**
```json
{
  "status": "NEED_INFO",
  "confidence_score": 0.6,
  "question": "What else is pressing?",
  "log_entry": "Pressure Release phase",
  "note": null
}
```

**SUCCESS Response:**
```json
{
  "status": "SUCCESS",
  "confidence_score": 0.95,
  "question": null,
  "log_entry": "Comprehensive brain dump complete",
  "note": {
    "title": "Brain Dump - March 4, 2026",
    "body": "## Work\n- Email\n## Home\n- Dog",
    "parent_id": "Inbox",
    "tags": ["brain-dump", "mindsweep"]
  }
}
```

---

## Session Phases

| Phase | Duration | Focus | Items |
|-------|----------|-------|-------|
| **Pressure Release** | 2-3 min | Most stressful | 2-4 items |
| **Quick Sweep** | 8-10 min | All categories | 15-25 items |
| **Stragglers** | 2-3 min | Final catch | 1-5 items |
| **TOTAL** | ~15 min | Everything | 20-30 items |

---

## Key APIs

### State Manager
```python
orch.state_manager.get_state(user_id)          # Fetch state
orch.state_manager.update_state(user_id, state) # Save state
orch.state_manager.clear_state(user_id)        # Delete state
```

### LLM Orchestrator
```python
await orch.llm_orchestrator.process_message(
    user_message="User input",
    context={"session_start": "...", "item_count": 5},
    persona="gtd_expert",
    history=[{"role": "...", "content": "..."}, ...]
)
# Returns: JoplinNoteSchema
```

### Joplin Client
```python
await orch.joplin_client.get_folders()
await orch.joplin_client.get_notes_in_folder(folder_id)
await orch.joplin_client.create_note(folder_id, title, body)
```

### Logging Service
```python
orch.logging_service.log_decision(decision: Decision)
```

### Task Service (Optional)
```python
if GOOGLE_TASKS_AVAILABLE and orch.task_service:
    created = orch.task_service.create_tasks_from_decision(decision, user_id)
    status = orch.task_service.get_task_sync_status(user_id)
```

---

## Common Patterns

### Start Session
```python
session_start = get_user_timezone_aware_now(user_id, orch.logging_service)
new_state = {
    "active_persona": "GTD_EXPERT",
    "session_start": session_start.isoformat(),
    "captured_items": [],
    "conversation_history": [],
}
orch.state_manager.update_state(user_id, new_state)
```

### Update History
```python
history = state.get("conversation_history", [])
history.append({"role": "user", "content": text})
state["conversation_history"] = history[-15:]  # Keep last 15
orch.state_manager.update_state(user_id, state)
```

### Check for Session
```python
state = orch.state_manager.get_state(user_id)
if state and state.get("active_persona") == "GTD_EXPERT":
    # Session is active
```

### Finish Session
```python
final_note = {
    "title": f"Brain Dump - {date_str}",
    "body": "## Work\n- ...",
    "parent_id": folder_id,
    "tags": ["brain-dump", "mindsweep"]
}
note_result = await create_note_in_joplin(orch, final_note)
orch.state_manager.clear_state(user_id)
```

---

## Whitelist Check

```python
from src.security_utils import check_whitelist

if not check_whitelist(user_id):
    return  # Silently ignore
```

---

## Error Handling Pattern

```python
try:
    llm_response = await orch.llm_orchestrator.process_message(...)
except Exception as exc:
    logger.error(f"Error in brain dump: {exc}")
    await message.reply_text(
        "❌ Sorry, had trouble processing. "
        "Continue or use /braindump_stop to finish."
    )
    return
```

---

## Folder Resolution

```python
if not final_note.get("parent_id") or final_note.get("parent_id") == "Inbox":
    folders = await orch.joplin_client.get_folders()
    for f in folders:
        if f["title"].lower() in ("inbox", "brain dump", "capture"):
            final_note["parent_id"] = f["id"]
            break
    if not final_note.get("parent_id") and folders:
        final_note["parent_id"] = folders[0]["id"]
```

---

## Response Format Examples

### Pressure Release Phase
```json
{
  "status": "NEED_INFO",
  "confidence_score": 0.7,
  "question": "What else is weighing on you right now?",
  "log_entry": "Pressure Release phase, gathering top stressors",
  "note": null
}
```

### Quick Sweep Phase
```json
{
  "status": "NEED_INFO",
  "confidence_score": 0.5,
  "question": "Any household tasks or home projects?",
  "log_entry": "Quick Sweep phase, moved to Home & Household",
  "note": null
}
```

### Ready to Wrap
```json
{
  "status": "NEED_INFO",
  "confidence_score": 0.8,
  "question": "Anything else we should capture before we wrap up?",
  "log_entry": "Stragglers phase, final sweep",
  "note": null
}
```

### Final Summary
```json
{
  "status": "SUCCESS",
  "confidence_score": 0.95,
  "question": null,
  "log_entry": "Session complete, 24 items across 7 categories",
  "note": {
    "title": "Brain Dump - March 4, 2026",
    "body": "## Work\n- Email redesign\n- Review budget\n\n## Home\n- Dog vet\n- Groceries\n\n## Paperwork\n- Car registration\n- Insurance",
    "parent_id": "folder_id",
    "tags": ["brain-dump", "mindsweep"]
  }
}
```

---

## Debug Checklist

- [ ] User is whitelisted?
- [ ] State created with `active_persona="GTD_EXPERT"`?
- [ ] Conversation history being appended?
- [ ] History truncated to last 15 turns?
- [ ] LLM response is valid JSON?
- [ ] status is "NEED_INFO" or "SUCCESS"?
- [ ] question field populated when status="NEED_INFO"?
- [ ] note field populated when status="SUCCESS"?
- [ ] confidence_score is 0.0-1.0?
- [ ] Final note has title, body, parent_id, tags?
- [ ] State cleared after _finish_session()?

---

## Logging Points

```python
logger.info("User %d starting /braindump session", user_id)
logger.info("GTD session for user %d completed by LLM", user_id)
logger.info("User %d stopping /braindump session via command", user_id)
logger.warning("Failed to read GTD prompt: %s", exc)
logger.error("Error in GTD brain dump for user %d: %s", user_id, exc)
logger.error("Error finishing brain dump for user %d: %s", user_id, exc)
```

---

## Test Cases (Quick Checklist)

**Unit:**
- [ ] Session starts with empty history
- [ ] Message appends to history
- [ ] History truncated to 15 turns
- [ ] LLM NEED_INFO continues session
- [ ] LLM SUCCESS calls _finish_session()
- [ ] /braindump_stop clears state
- [ ] Whitelist check prevents non-users

**Integration:**
- [ ] Full session: start → 5 messages → LLM finishes → note saved
- [ ] Manual stop: start → 2 messages → /braindump_stop → summary generated
- [ ] Folder fallback: saves to first folder if Inbox not found
- [ ] Google Tasks: decision logged, tasks extracted (if available)

---

## Commands for Debugging

```bash
# Check if user has active session
# (Would need admin access to state_manager)

# View decision logs
# (Query logging_service.decisions table)

# Inspect last N sessions
# SELECT * FROM decisions WHERE user_id=123 ORDER BY created DESC LIMIT 5;

# Monitor LLM calls
# grep "Processing message" logs/ | grep gtd_expert
```

---

## Quick Links

- **Implementation Guide:** `docs/brain-dump-implementation-guide.md`
- **Flow Diagrams:** `docs/brain-dump-flow-diagrams.md`
- **Prompt Tuning:** `docs/brain-dump-prompt-tuning.md`
- **Current Prompt:** `src/prompts/gtd_expert.txt`
- **Handler Code:** `src/handlers/braindump.py`
- **Tests:** `tests/test_braindump.py` (if exists)

---

## Summary (30-second version)

1. **User sends `/braindump`** → Handler creates state with `active_persona="GTD_EXPERT"`
2. **User types message** → Router sends to `handle_braindump_message()`
3. **Message + history sent to LLM** → LLM responds with JSON (status, question, or note)
4. **If NEED_INFO** → Ask next question, update history
5. **If SUCCESS** → Final note generated, saved to Joplin, state cleared
6. **User can anytime** → Send `/braindump_stop` to finish immediately

