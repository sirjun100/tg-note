# Brain Dump (/braindump) Implementation Guide

**For:** LLM implementers rebuilding or extending the GTD brain dump feature
**Target Files:** `src/handlers/braindump.py`, `src/llm_orchestrator.py`, `src/prompts/gtd_expert.txt`
**Status:** Complete feature, ready for reference implementation

---

## Table of Contents

1. [Feature Overview](#feature-overview)
2. [Architecture & Flow Diagram](#architecture--flow-diagram)
3. [Session Lifecycle](#session-lifecycle)
4. [Detailed Component Breakdown](#detailed-component-breakdown)
5. [LLM Integration](#llm-integration)
6. [Message Handling Loop](#message-handling-loop)
7. [Note Creation & Finalization](#note-creation--finalization)
8. [Google Tasks Integration](#google-tasks-integration)
9. [Error Handling Strategy](#error-handling-strategy)
10. [Testing Checklist](#testing-checklist)
11. [Code Examples](#code-examples)

---

## Feature Overview

**Purpose:** Help users quickly empty their minds into a structured capture list using a GTD (Getting Things Done) methodology in ~15 minutes.

**User Commands:**
- `/braindump` — Start a new brain dump session (alias: `/capture`)
- `/braindump_stop` — End the current session and save
- During session: Just type your response; the bot continues asking questions

**Key Behaviors:**
- Conversational, Telegram-native (no special UI, just message exchanges)
- LLM-guided questioning to extract all thoughts from the user
- Automatic session end detection (LLM decides when user has dumped everything)
- Converts raw input into an organized, categorized note
- Optionally extracts action items to Google Tasks

---

## Architecture & Flow Diagram

```
User Message
    ↓
┌─────────────────────────────────────────┐
│ Message Router (core.py)                │
│ - Checks user whitelist                 │
│ - Routes to active_persona handler      │
└─────────────────────────────────────────┘
    ↓
    ├─ active_persona == "GTD_EXPERT"
    │
    ↓
┌─────────────────────────────────────────┐
│ handle_braindump_message()              │
│ - Gets current state                    │
│ - Builds conversation context           │
│ - Calls LLM with GTD persona            │
└─────────────────────────────────────────┘
    ↓
    ├─ Sends user message + history to LLM
    │
    ↓
┌─────────────────────────────────────────┐
│ LLM Response Processing                 │
│ (llm_orchestrator.process_message)      │
└─────────────────────────────────────────┘
    ↓
    ├─ Status: "NEED_INFO"
    │  └─ Ask next question
    │     └─ Update state.conversation_history
    │     └─ Reply to user
    │
    ├─ Status: "SUCCESS"
    │  └─ LLM has compiled final note
    │     └─ Call _finish_session()
    │     └─ Save to Joplin
    │     └─ Extract actions to Google Tasks
    │     └─ Clear state
    │
    └─ Status: "ERROR"
       └─ Log error & ask user to retry or use /braindump_stop


Command: /braindump_stop
    ↓
    └─ Force end session
       └─ Generate summary from history (if no final note yet)
       └─ Save to Joplin
       └─ Clear state
```

---

## Session Lifecycle

### Phase 1: Session Start (`/braindump` command)

**Handler:** `_braindump(orch)`

**Steps:**
1. User sends `/braindump` or `/capture`
2. Check whitelist (security)
3. Check if user already has active GTD_EXPERT session
   - If yes: return message "You already have an active session"
   - If no: proceed
4. Create new state in state_manager:
   ```python
   {
       "active_persona": "GTD_EXPERT",
       "session_start": ISO_TIMESTAMP,
       "captured_items": [],
       "conversation_history": [],
   }
   ```
5. Load first question from `src/prompts/gtd_expert.txt` (or use fallback)
6. Send first question to user
7. Wait for user response

**Initial Question (from prompt file):**
```
"Ready to dump your brain? Let's do 15 minutes.
First—what is the thing that has been poking at you the most lately?
The one that keeps coming back."
```

---

### Phase 2: Conversation Loop (User Responds)

**Handler:** `handle_braindump_message(orch, user_id, text, message)`

**Triggered by:** Any message from user while `active_persona == "GTD_EXPERT"`

**Steps:**

1. **Fetch current state**
   ```python
   state = orch.state_manager.get_state(user_id)
   history = state.get("conversation_history", [])
   ```

2. **Prepare LLM context**
   ```python
   ctx = {
       "session_start": state.get("session_start"),
       "item_count": len(state.get("captured_items", [])),
   }
   ```

3. **Call LLM with GTD persona**
   ```python
   llm_response = await orch.llm_orchestrator.process_message(
       user_message=text,
       context=ctx,
       persona="gtd_expert",  # ← Loads gtd_expert.txt system prompt
       history=history
   )
   ```

4. **Append to conversation history**
   ```python
   history.append({"role": "user", "content": text})
   ```

5. **Check LLM response status**

   **Case A: Status = "NEED_INFO"**
   - LLM wants to continue conversation
   - Question: `llm_response.question`
   - Action:
     ```python
     history.append({"role": "assistant", "content": next_q})
     state["conversation_history"] = history[-15:]  # Keep last 15 turns
     orch.state_manager.update_state(user_id, state)
     await message.reply_text(next_q)
     ```
   - Truncate history to last 15 turns to manage context window

   **Case B: Status = "SUCCESS"**
   - LLM has completed brain dump & compiled final note
   - Note data: `llm_response.note` (dict with title, body, parent_id, tags)
   - Action:
     ```python
     state["final_note"] = llm_response.note
     state["conversation_history"] = history
     orch.state_manager.update_state(user_id, state)
     await _finish_session(orch, user_id, message, llm_response.note)
     ```

   **Case C: Status = "ERROR"**
   - LLM failed to process
   - Action: Log error, ask user to retry or use `/braindump_stop`

---

### Phase 3: Session End

**Triggers:**
1. LLM returns `status="SUCCESS"` during conversation
2. User sends `/braindump_stop` command
3. Error occurs requiring manual stop

**Handler:** `_finish_session(orch, user_id, message, note_data=None)`

**Steps:**

1. **Send "Finishing..." message**
   ```python
   await message.reply_text("🏁 *FINISHING BRAIN DUMP SESSION...*")
   ```

2. **Get or generate final note**
   ```python
   final_note = note_data or state.get("final_note")

   if not final_note and history exists:
       # LLM didn't auto-complete; generate summary
       await message.reply_text("📊 Generating summary...")
       llm_response = await orch.llm_orchestrator.process_message(
           user_message="Please summarize everything we've talked about so far into an organized list.",
           persona="gtd_expert",
           history=history,
       )
       if llm_response.status == "SUCCESS":
           final_note = llm_response.note
   ```

3. **Fallback: No LLM summary**
   ```python
   if not final_note:
       final_note = {
           "title": f"Brain Dump Session - {date_str}",
           "body": "\n".join(f"{h['role']}: {h['content']}" for h in history),
           "parent_id": "Inbox",
           "tags": ["brain-dump", "mindsweep"],
       }
   ```

4. **Resolve parent folder**
   ```python
   # Search for Inbox/Brain Dump/Capture folder
   folders = await orch.joplin_client.get_folders()
   for folder in folders:
       if folder["title"].lower() in ("inbox", "brain dump", "capture"):
           final_note["parent_id"] = folder["id"]
           break
   ```

5. **Create note in Joplin**
   ```python
   from src.handlers.core import create_note_in_joplin
   note_result = await create_note_in_joplin(orch, final_note)
   ```

6. **Log decision to database**
   ```python
   decision = Decision(
       user_id=user_id,
       status="SUCCESS",
       folder_chosen=final_note.get("parent_id"),
       note_title=final_note.get("title"),
       note_body=final_note.get("body"),
       tags=final_note.get("tags", []),
       joplin_note_id=note_result["note_id"],
   )
   orch.logging_service.log_decision(decision)
   ```

7. **Extract action items to Google Tasks (if available)**
   ```python
   if GOOGLE_TASKS_AVAILABLE and orch.task_service:
       await message.reply_text("🚀 Extracting action items...")
       created = orch.task_service.create_tasks_from_decision(decision, str(user_id))
       if created:
           await message.reply_text(f"✅ Created {len(created)} task(s) in Google Tasks")
   ```

8. **Clear session state**
   ```python
   orch.state_manager.clear_state(user_id)
   await message.reply_text("✨ Brain dump session closed...")
   ```

---

## Detailed Component Breakdown

### 1. State Management

**Where:** `state_manager` (TelegramOrchestrator.state_manager)

**Session State Schema:**
```python
{
    "active_persona": "GTD_EXPERT",           # Identifies this as a brain dump
    "session_start": "2026-03-04T10:30:00",  # ISO timestamp
    "captured_items": [],                     # Legacy field (not used in current impl)
    "conversation_history": [                 # Conversation turns
        {
            "role": "user",
            "content": "My dog needs a vet appointment"
        },
        {
            "role": "assistant",
            "content": "Got it. What else is urgent?"
        },
        # ... more turns
    ],
    "final_note": {                          # Set when LLM completes
        "title": "Brain Dump - March 4",
        "body": "## Work\n- Email client\n## Home\n- Vet appt",
        "parent_id": "inbox_folder_id",
        "tags": ["brain-dump"]
    }
}
```

**Key Operations:**
- `orch.state_manager.get_state(user_id)` — Fetch session state
- `orch.state_manager.update_state(user_id, state)` — Save state changes
- `orch.state_manager.clear_state(user_id)` — Delete session (on completion/error)

---

### 2. LLM Orchestrator Integration

**File:** `src/llm_orchestrator.py`

**Key Function:** `LLMOrchestrator.process_message()`

```python
async def process_message(
    user_message: str,
    context: dict[str, Any] = None,
    persona: str = None,
    history: list[dict[str, str]] = None,
) -> JoplinNoteSchema:
    """
    Process user message with LLM using a persona.

    For brain dump:
    - persona = "gtd_expert"
    - Loads system prompt from src/prompts/gtd_expert.txt
    - Returns JoplinNoteSchema
    """
```

**Return Type:** `JoplinNoteSchema`
```python
class JoplinNoteSchema(BaseModel):
    status: str  # "SUCCESS", "NEED_INFO", or error
    confidence_score: float  # 0.0 to 1.0
    question: str | None  # Next question to ask user
    log_entry: str  # Internal note about decision
    note: dict[str, Any] | None  # Final note data (only if SUCCESS)
```

**Provider Support:**
- OpenAI (with function calling)
- DeepSeek (with function calling)
- Ollama (structured prompt fallback)

---

### 3. GTD Expert Persona Prompt

**File:** `src/prompts/gtd_expert.txt`

**Key Sections:**

1. **Role Definition**
   - Warm, brisk, focused on capture only
   - Not a therapist or project manager

2. **Session Structure (3 phases)**
   - **Pressure Release** (2-3 min): Most stressful items
   - **Quick Sweep** (8-10 min): Work, home, paperwork, finances, health, projects
   - **Stragglers** (2-3 min): Final chance to add anything

3. **Response Format**
   - Always return JSON (even for questions)
   - `status`: "NEED_INFO" (while asking) or "SUCCESS" (final summary)
   - `question`: Next question for user
   - `note`: Final organized summary (only when SUCCESS)

4. **Key Behaviors**
   - Ask ONE short question at a time
   - Briefly acknowledge before moving on
   - If user says "nothing", move on immediately
   - Redirect tangents: "Let's just capture that and keep moving"
   - Extra focus on paperwork (taxes, renewals, contracts)

5. **Final Summary Format**
   ```markdown
   ## Work
   - Item 1
   - Item 2

   ## Home
   - Item 1

   ## Paperwork
   - Renew car registration
   ```

---

## LLM Integration

### How the LLM Drives the Conversation

**System Prompt Loading:**
```python
# In llm_orchestrator._get_persona_prompt()
persona_file = self.prompts_dir / f"{persona}.txt"
system_prompt = persona_file.read_text()
```

**Message Flow:**
```python
messages = [
    {"role": "system", "content": system_prompt},  # GTD expert instructions
    *history,  # Previous turns
    {"role": "user", "content": user_message},  # Current user input
]
```

**Response Parsing:**

For OpenAI/DeepSeek:
```python
# Use function calling to force JSON response
response = await provider.generate_response(
    messages=messages,
    functions=[{"name": "create_joplin_note", "parameters": JoplinNoteSchema.schema()}],
    function_call={"name": "create_joplin_note"},
    temperature=0.3,
    max_tokens=1000
)

# Extract JSON from function call arguments
args = json.loads(response["function_call"]["arguments"])
result = JoplinNoteSchema(**args)
```

For Ollama (no function calling):
```python
# Use structured prompt to request JSON
response = await provider.generate_response(
    messages=[{"role": "user", "content": structured_prompt}],
    temperature=0.1,  # Very low temp for structure
    max_tokens=1500
)

# Parse JSON from response content
json_text = response["content"]
args = json.loads(json_text)
result = JoplinNoteSchema(**args)
```

---

## Message Handling Loop

**Complete Flow for One User Message:**

```python
async def handle_braindump_message(
    orch: TelegramOrchestrator,
    user_id: int,
    text: str,
    message: Message
) -> None:
    # 1. Fetch state
    state = orch.state_manager.get_state(user_id)
    if not state or state.get("active_persona") != "GTD_EXPERT":
        return  # Not in brain dump

    # 2. Prepare history
    history = state.get("conversation_history", [])
    ctx = {
        "session_start": state.get("session_start"),
        "item_count": len(state.get("captured_items", [])),
    }

    # 3. Call LLM
    llm_response = await orch.llm_orchestrator.process_message(
        user_message=text,
        context=ctx,
        persona="gtd_expert",
        history=history
    )

    # 4. Update history
    history.append({"role": "user", "content": text})

    # 5. Handle response
    if llm_response.status == "SUCCESS":
        # Brain dump complete
        state["final_note"] = llm_response.note
        state["conversation_history"] = history
        orch.state_manager.update_state(user_id, state)
        await _finish_session(orch, user_id, message, llm_response.note)

    elif llm_response.status == "NEED_INFO":
        # Continue conversation
        next_q = llm_response.question or "Any other thoughts?"
        history.append({"role": "assistant", "content": next_q})
        state["conversation_history"] = history[-15:]  # Keep last 15
        orch.state_manager.update_state(user_id, state)
        await message.reply_text(next_q)

    else:  # ERROR
        logger.error(f"LLM error: {llm_response.log_entry}")
        await message.reply_text(
            "❌ Sorry, I had trouble processing that. "
            "You can continue or use /braindump_stop."
        )
```

---

## Note Creation & Finalization

### Note Structure

**Input (from LLM):**
```python
{
    "title": "Brain Dump - March 4, 2026",
    "body": """## Work
- Email client redesign meeting prep
- Review Q1 budget

## Home
- Schedule vet appointment for dog
- Buy groceries (milk, eggs, bread)

## Paperwork
- Renew car registration (expires June)
- Review car insurance renewal
    """,
    "parent_id": "Inbox",
    "tags": ["brain-dump", "mindsweep"]
}
```

**Processing in `_finish_session()`:**

1. **Folder Resolution**
   ```python
   if not final_note.get("parent_id") or final_note.get("parent_id") == "Inbox":
       folders = await orch.joplin_client.get_folders()
       for f in folders:
           if f["title"].lower() in ("inbox", "brain dump", "capture"):
               final_note["parent_id"] = f["id"]
               break
   ```

2. **Note Creation**
   ```python
   from src.handlers.core import create_note_in_joplin
   note_result = await create_note_in_joplin(orch, final_note)
   # Returns: {"note_id": "abc123", ...}
   ```

3. **Decision Logging**
   ```python
   decision = Decision(
       user_id=user_id,
       status="SUCCESS",
       folder_chosen=final_note.get("parent_id"),
       note_title=final_note.get("title"),
       note_body=final_note.get("body"),
       tags=final_note.get("tags", []),
       joplin_note_id=note_result["note_id"],
   )
   orch.logging_service.log_decision(decision)
   ```

---

## Google Tasks Integration

**Prerequisite:** `GOOGLE_TASKS_AVAILABLE` is True (google_tasks_client and task_service modules present)

**Flow:**

1. **Check availability**
   ```python
   if GOOGLE_TASKS_AVAILABLE and orch.task_service:
       # Proceed
   ```

2. **Extract tasks from brain dump**
   ```python
   created = orch.task_service.create_tasks_from_decision(
       decision=decision,
       user_id=str(user_id)
   )
   ```

3. **Notify user**
   ```python
   if created:
       await message.reply_text(
           f"✅ Created {len(created)} task(s) in Google Tasks"
       )
       # Also get sync status
       status = orch.task_service.get_task_sync_status(user_id)
       s, f = status.get("success_count", 0), status.get("failed_count", 0)
       await message.reply_text(f"📊 Sync: ✅ {s}, ❌ {f}")
   else:
       # Check if token exists
       has_token = orch.logging_service.load_google_token(str(user_id))
       if has_token:
           await message.reply_text("❌ Could not create tasks. Check /google_tasks_status")
       else:
           await message.reply_text(
               "❌ No Google Tasks token. Use /authorize_google_tasks"
           )
   ```

---

## Error Handling Strategy

### Error Scenarios

| Scenario | Handler | User Message |
|----------|---------|--------------|
| No active session on `/braindump_stop` | `_braindump_stop()` | "You don't have an active session" |
| Already have active session | `_braindump()` | "You already have an active session" |
| LLM processing fails | `handle_braindump_message()` | "Sorry, I had trouble processing that. Continue or /braindump_stop" |
| Note creation fails | `_finish_session()` | "Failed to save note to Joplin" |
| Joplin folder not found | `_finish_session()` | Falls back to first available folder |
| Google Tasks token missing | `_finish_session()` | "No token, use /authorize_google_tasks" |
| Unexpected error during finish | `_finish_session()` | "An error occurred. I've cleared the session" |

### Logging

All errors logged at appropriate levels:
```python
logger.info("User %d starting /braindump session", user_id)
logger.warning("Failed to read GTD prompt: %s", exc)
logger.error("Error in GTD brain dump for user %d: %s", user_id, exc)
logger.error("Error finishing brain dump for user %d: %s", user_id, exc, exc_info=True)
```

---

## Testing Checklist

### Unit Tests

- [ ] `test_braindump_start_creates_state()` — Verify state initialized with correct schema
- [ ] `test_braindump_start_loads_first_question()` — Verify prompt file loaded or fallback used
- [ ] `test_braindump_start_already_active()` — Verify blocks if session exists
- [ ] `test_handle_message_updates_history()` — Verify conversation history appended
- [ ] `test_handle_message_need_info_continues()` — Verify asks next question
- [ ] `test_handle_message_success_finishes()` — Verify calls _finish_session()
- [ ] `test_handle_message_error_notifies_user()` — Verify error handling
- [ ] `test_braindump_stop_clears_state()` — Verify state cleared on `/braindump_stop`
- [ ] `test_braindump_stop_no_session()` — Verify error if no active session

### Integration Tests

- [ ] `test_full_brain_dump_flow()` — User starts → answers 3-4 questions → LLM auto-finishes → note saved
- [ ] `test_brain_dump_with_manual_stop()` — User starts → answers 2 questions → sends `/braindump_stop` → summary generated
- [ ] `test_brain_dump_with_folder_fallback()` — Note saves to first available folder if Inbox not found
- [ ] `test_brain_dump_with_google_tasks()` — Note created → tasks extracted → status reported
- [ ] `test_brain_dump_without_google_tasks()` — Note created, task step skipped
- [ ] `test_brain_dump_joplin_connection_failure()` — Error message sent, state cleared
- [ ] `test_brain_dump_llm_timeout()` — LLM takes too long, error handled gracefully

### Manual Tests (QA)

1. **Basic Flow**
   - [ ] Start `/braindump`, answer 5 questions, LLM says done, note saved ✅

2. **Early Stop**
   - [ ] Start `/braindump`, answer 2 questions, `/braindump_stop`, summary auto-generated ✅

3. **Double Start**
   - [ ] Start `/braindump`, try `/braindump` again → error message ✅

4. **Whitelist Check**
   - [ ] Non-whitelisted user tries `/braindump` → no response ✅

5. **Google Tasks**
   - [ ] After brain dump, tasks extracted to Google Tasks ✅
   - [ ] If no token, error message suggests `/authorize_google_tasks` ✅

6. **Error Recovery**
   - [ ] Joplin connection fails → user notified, state cleared ✅
   - [ ] LLM returns malformed response → user told to retry/cancel ✅

---

## Code Examples

### Example 1: Starting a Session

```python
# User sends: /braindump

user = update.effective_user  # User object from Telegram
if not check_whitelist(user.id):
    return  # Silently ignore non-whitelisted users

user_id = user.id
state = orch.state_manager.get_state(user_id)

# Check for existing session
if state and state.get("active_persona") == "GTD_EXPERT":
    await update.message.reply_text(
        "💡 You already have an active brain dump session! "
        "Just keep typing, or use /braindump_stop to finish."
    )
    return

# Create new session
session_start = get_user_timezone_aware_now(user_id, orch.logging_service)
new_state = {
    "active_persona": "GTD_EXPERT",
    "session_start": session_start.isoformat(),
    "captured_items": [],
    "conversation_history": [],
}
orch.state_manager.update_state(user_id, new_state)

# Load first question
first_question = "Ready to dump your brain? ..."
prompt_path = Path(__file__).parent.parent / "prompts" / "gtd_expert.txt"
if prompt_path.exists():
    try:
        lines = prompt_path.read_text().strip().split("\n")
        if lines:
            first_question = lines[-1]
    except Exception as exc:
        logger.warning("Failed to read GTD prompt: %s", exc)

await update.message.reply_text(
    f"🧠 *GTD MIND SWEEP SESSION STARTED*\n\n{first_question}",
    parse_mode="Markdown",
)
```

### Example 2: Processing a User Message

```python
# User sends: "My dog needs a vet appointment"

state = orch.state_manager.get_state(user_id)
if not state or state.get("active_persona") != "GTD_EXPERT":
    return  # Not in brain dump

history = state.get("conversation_history", [])
ctx = {
    "session_start": state.get("session_start"),
    "item_count": len(state.get("captured_items", [])),
}

# Call LLM
try:
    llm_response = await orch.llm_orchestrator.process_message(
        user_message=text,
        context=ctx,
        persona="gtd_expert",
        history=history
    )
except Exception as exc:
    logger.error("Error in GTD brain dump for user %d: %s", user_id, exc)
    await message.reply_text(
        "❌ Sorry, I had some trouble processing that. "
        "You can continue or use /braindump_stop to finish."
    )
    return

# Update history
history.append({"role": "user", "content": text})

# Handle response
if llm_response.status == "SUCCESS":
    logger.info("GTD session for user %d completed by LLM", user_id)
    state["final_note"] = llm_response.note
    state["conversation_history"] = history
    orch.state_manager.update_state(user_id, state)
    await _finish_session(orch, user_id, message, llm_response.note)

elif llm_response.status == "NEED_INFO":
    next_q = llm_response.question or "Any other thoughts?"
    history.append({"role": "assistant", "content": next_q})
    state["conversation_history"] = history[-15:]  # Keep last 15
    orch.state_manager.update_state(user_id, state)
    await message.reply_text(next_q)

else:  # ERROR
    logger.error("LLM error for user %d: %s", user_id, llm_response.log_entry)
    await message.reply_text(
        "❌ Sorry, I had some trouble processing that. "
        "You can continue or use /braindump_stop to finish."
    )
```

### Example 3: Finishing a Session

```python
# Called when LLM says SUCCESS or user sends /braindump_stop

state = orch.state_manager.get_state(user_id)
if not state:
    return

await message.reply_text("🏁 *FINISHING BRAIN DUMP SESSION...*", parse_mode="Markdown")

try:
    final_note = note_data or state.get("final_note")

    # Generate summary if needed
    if not final_note:
        history = state.get("conversation_history", [])
        if history:
            await message.reply_text("📊 Generating summary of your session...")
            llm_response = await orch.llm_orchestrator.process_message(
                user_message="Please summarize everything we've talked about so far into an organized list.",
                persona="gtd_expert",
                history=history,
            )
            if llm_response.status == "SUCCESS":
                final_note = llm_response.note

    # Fallback
    if not final_note:
        date_str = get_current_date_str(user_id, orch.logging_service)
        final_note = {
            "title": f"Brain Dump Session - {date_str}",
            "body": "\n".join(f"{h['role']}: {h['content']}" for h in history),
            "parent_id": "Inbox",
            "tags": ["brain-dump", "mindsweep"],
        }

    # Resolve folder
    if not final_note.get("parent_id") or final_note.get("parent_id") == "Inbox":
        folders = await orch.joplin_client.get_folders()
        inbox_id = None
        for f in folders:
            if f["title"].lower() in ("inbox", "brain dump", "capture"):
                inbox_id = f["id"]
                break
        if inbox_id:
            final_note["parent_id"] = inbox_id
        elif folders:
            final_note["parent_id"] = folders[0]["id"]

    # Create note
    from src.handlers.core import create_note_in_joplin
    note_result = await create_note_in_joplin(orch, final_note)

    if note_result:
        await message.reply_text(
            f"✅ *BRAIN DUMP SAVED TO JOPLIN*\n\nNote: {final_note['title']}",
            parse_mode="Markdown",
        )

        # Log decision
        decision = Decision(
            user_id=user_id,
            status="SUCCESS",
            folder_chosen=final_note.get("parent_id"),
            note_title=final_note.get("title"),
            note_body=final_note.get("body"),
            tags=final_note.get("tags", []),
            joplin_note_id=note_result["note_id"],
        )
        orch.logging_service.log_decision(decision)

        # Extract Google Tasks
        if GOOGLE_TASKS_AVAILABLE and orch.task_service:
            await message.reply_text("🚀 Extracting action items to Google Tasks...")
            created = orch.task_service.create_tasks_from_decision(decision, str(user_id))
            if created:
                await message.reply_text(f"✅ Created {len(created)} task(s) in Google Tasks.")
    else:
        await message.reply_text("❌ Failed to save note to Joplin.")

    # Cleanup
    orch.state_manager.clear_state(user_id)
    await message.reply_text("✨ Brain dump session closed. Your head should feel lighter now!")

except Exception as exc:
    logger.error("Error finishing brain dump for user %d: %s", user_id, exc, exc_info=True)
    await message.reply_text(
        "❌ An error occurred while finishing your session. I've cleared the session state."
    )
    orch.state_manager.clear_state(user_id)
```

---

## Summary

The `/braindump` feature is a **stateful, LLM-driven conversation** that:

1. **Initiates** with `/braindump` command
2. **Runs** through a multi-turn conversation with LLM-as-GTD-coach
3. **Auto-detects** completion when LLM returns `status="SUCCESS"`
4. **Compiles** final note from all captured items
5. **Saves** to Joplin in appropriate folder
6. **Extracts** action items to Google Tasks (if configured)
7. **Cleans up** session state

Key design principles:
- **Simple conversation loop** — user types, bot asks next question
- **LLM-driven pacing** — no predefined number of questions
- **Stateful** — uses state_manager to maintain context
- **Graceful degradation** — fallbacks if LLM/Joplin fails
- **Privacy** — whitelist check, user data logged to database

For implementation, focus on the **three main handlers** (`_braindump`, `_braindump_stop`, `handle_braindump_message`) and ensure proper **state transitions** and **LLM integration**.
