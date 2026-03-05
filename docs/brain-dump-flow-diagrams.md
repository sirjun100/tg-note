# Brain Dump Flow Diagrams

Visual representations of the `/braindump` feature for implementation reference.

---

## 1. High-Level Session Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    BRAIN DUMP SESSION FLOW                       │
└─────────────────────────────────────────────────────────────────┘

User sends: /braindump
    │
    ▼
┌──────────────────────────────────────┐
│ _braindump() handler                 │
│ - Check whitelist                    │
│ - Check for existing session         │
│ - Create state with empty history    │
│ - Load first question from prompt    │
└──────────────────────────────────────┘
    │
    ▼
send: "🧠 GTD MIND SWEEP SESSION STARTED\n\n{first_question}"
    │
    ├─────────────────────────────────────────────────┐
    │ STATE: active_persona = "GTD_EXPERT"            │
    │        conversation_history = []                │
    └─────────────────────────────────────────────────┘
    │
    ▼
User responds: "My dog needs a vet appointment"
    │
    ▼
┌──────────────────────────────────────────────┐
│ handle_braindump_message()                   │
│ - Get state                                  │
│ - Build history + context                   │
│ - Call LLM with "gtd_expert" persona         │
└──────────────────────────────────────────────┘
    │
    ▼
    │
    ├──────────────────────────────┬──────────────────────────────┬────────────────────────────┐
    │                              │                              │                            │
    ▼                              ▼                              ▼                            ▼
LLM returns:                 LLM returns:                  LLM returns:            LLM returns:
status="NEED_INFO"           status="SUCCESS"              status="ERROR"          (Other)
question="What else?"        note={...}                    log_entry="..."
    │                            │                              │                            │
    ▼                            ▼                              ▼                            ▼
Append answer                  Final note ready           Log error, ask         Log warning,
to history                     Call _finish_session()     user to retry          treat as error
    │                            │                              │                            │
    ▼                            ▼                              ▼                            ▼
Update state                 Save to Joplin          "Sorry, had trouble      Reply: "Sorry,
Reply with                   Extract to              processing that.         had trouble..."
next question                Google Tasks             Continue or /stop"       Continue listening
    │                            │                                               for input
    │                            ▼
    │                      Clear state
    │                            │
    └────────────────────────────┤
                                 ▼
                        "✨ Brain dump closed"
                                 │
                                 ▼
                        Session ends

OR

User sends: /braindump_stop
    │
    ▼
┌──────────────────────────────────────┐
│ _braindump_stop() handler            │
│ - Validate session exists            │
│ - Call _finish_session()             │
└──────────────────────────────────────┘
    │
    ▼
(Same as _finish_session() above)
```

---

## 2. Message Processing State Machine

```
                    ┌─────────────────────────┐
                    │   SESSION NOT ACTIVE    │
                    └─────────────────────────┘
                              ▲
                              │
                    /braindump_stop
                    (no session)
                              │
                    ┌─────────┴──────────────────────┐
                    │                                │
                    ▼                                ▼
            ┌──────────────────┐        ┌──────────────────────────┐
            │  /braindump      │        │  User sends /braindump   │
            │  Already active  │        │  (creates state)         │
            │  → "You already" │        │                          │
            │    have session" │        │                          │
            └──────────────────┘        └──────────────────────────┘
                    ▲                              │
                    │                              ▼
                    │                   ┌──────────────────────────┐
                    │                   │   SESSION ACTIVE         │
                    │                   │                          │
                    │                   │ state: {                 │
                    │                   │   active_persona:        │
                    │                   │     "GTD_EXPERT",        │
                    │                   │   conversation_history   │
                    │                   │ }                        │
                    │                   └──────────────────────────┘
                    │                              │
                    │              ┌───────────────┼───────────────┐
                    │              │               │               │
                    │              ▼               ▼               ▼
                    │        LLM: NEED_INFO   LLM: SUCCESS   /braindump_stop
                    │              │               │               │
                    │              ▼               ▼               ▼
                    │         Continue      _finish_session()
                    │         Listening      Generate summary
                    │              │         Save to Joplin
                    │              │         Extract tasks
                    │              │              │
                    └──────────────┴──────────────┴──> Clear state
                                                       SessionEnds
```

---

## 3. Detailed Message Handler Flow

```
User types message
    │
    ▼
┌────────────────────────────────────────────┐
│ Core message router checks:                │
│ - Is message for active_persona?           │
│ - active_persona == "GTD_EXPERT"? YES ✓    │
└────────────────────────────────────────────┘
    │
    ▼
handle_braindump_message(orch, user_id, text, message)
    │
    ├─► state = orch.state_manager.get_state(user_id)
    │
    ├─► if not state or active_persona != "GTD_EXPERT":
    │   └─► return  (not a brain dump)
    │
    ├─► history = state.get("conversation_history", [])
    │
    ├─► ctx = {
    │       "session_start": state["session_start"],
    │       "item_count": len(state["captured_items"])
    │   }
    │
    ├─► TRY:
    │   │
    │   ├─► llm_response = await orch.llm_orchestrator.process_message(
    │   │       user_message=text,
    │   │       context=ctx,
    │   │       persona="gtd_expert",  ◄─ Loads src/prompts/gtd_expert.txt
    │   │       history=history
    │   │   )
    │   │
    │   ├─► history.append({"role": "user", "content": text})
    │   │
    │   └─► Check llm_response.status:
    │       │
    │       ├─ "SUCCESS":
    │       │   │
    │       │   ├─► state["final_note"] = llm_response.note
    │       │   ├─► state["conversation_history"] = history
    │       │   ├─► orch.state_manager.update_state(user_id, state)
    │       │   │
    │       │   └─► await _finish_session(orch, user_id, message, llm_response.note)
    │       │       │
    │       │       ├─► Create note in Joplin
    │       │       ├─► Log decision
    │       │       ├─► Extract tasks to Google Tasks (optional)
    │       │       ├─► Send confirmation messages
    │       │       │
    │       │       └─► orch.state_manager.clear_state(user_id)
    │       │
    │       ├─ "NEED_INFO":
    │       │   │
    │       │   ├─► next_q = llm_response.question or "Any other thoughts?"
    │       │   ├─► history.append({"role": "assistant", "content": next_q})
    │       │   ├─► state["conversation_history"] = history[-15:]  (keep last 15 turns)
    │       │   ├─► orch.state_manager.update_state(user_id, state)
    │       │   │
    │       │   └─► await message.reply_text(next_q)
    │       │       ◄─ User sees next question
    │       │
    │       └─ ERROR or other:
    │           │
    │           ├─► logger.error(...)
    │           │
    │           └─► await message.reply_text(
    │                   "❌ Sorry, had trouble processing. "
    │                   "Continue or /braindump_stop"
    │               )
    │
    └─► EXCEPT Exception as exc:
        │
        ├─► logger.error(f"Error in GTD: {exc}")
        │
        └─► await message.reply_text(
                "❌ Sorry, had trouble processing. "
                "Continue or /braindump_stop"
            )
```

---

## 4. Session Finalization Flow

```
_finish_session(orch, user_id, message, note_data=None)
    │
    ├─► Send: "🏁 FINISHING BRAIN DUMP SESSION..."
    │
    ├─► state = orch.state_manager.get_state(user_id)
    │
    ├─► final_note = note_data OR state.get("final_note")
    │
    ├─► IF NOT final_note:
    │   │
    │   ├─► history = state.get("conversation_history", [])
    │   │
    │   ├─► IF history:
    │   │   │
    │   │   ├─► Send: "📊 Generating summary..."
    │   │   │
    │   │   ├─► llm_response = await orch.llm_orchestrator.process_message(
    │   │   │       user_message="Please summarize everything...",
    │   │   │       persona="gtd_expert",
    │   │   │       history=history
    │   │   │   )
    │   │   │
    │   │   ├─► IF status == "SUCCESS":
    │   │   │   └─► final_note = llm_response.note
    │   │   │
    │   │   └─► ELSE:
    │   │       └─► Send: "⚠️ Couldn't generate summary, saving as-is"
    │   │
    │   └─► IF STILL NO final_note:
    │       │
    │       └─► final_note = {
    │               "title": f"Brain Dump Session - {date}",
    │               "body": "(conversation as text)",
    │               "parent_id": "Inbox",
    │               "tags": ["brain-dump", "mindsweep"]
    │           }
    │
    ├─► TRY:
    │   │
    │   ├─► Resolve parent folder:
    │   │   │
    │   │   ├─► IF final_note.parent_id == "Inbox":
    │   │   │   │
    │   │   │   ├─► folders = await orch.joplin_client.get_folders()
    │   │   │   │
    │   │   │   ├─► FOR folder IN folders:
    │   │   │   │   └─► IF folder.title.lower() in ("inbox", "brain dump", "capture"):
    │   │   │   │       └─► final_note["parent_id"] = folder["id"]
    │   │   │   │           BREAK
    │   │   │   │
    │   │   │   └─► IF not found AND folders:
    │   │   │       └─► final_note["parent_id"] = folders[0]["id"]
    │   │   │
    │   │   └─► ELSE: (parent_id already set)
    │   │       └─► Use as-is
    │   │
    │   ├─► Create note:
    │   │   │
    │   │   ├─► from src.handlers.core import create_note_in_joplin
    │   │   │
    │   │   ├─► note_result = await create_note_in_joplin(orch, final_note)
    │   │   │
    │   │   ├─► IF note_result:
    │   │   │   │
    │   │   │   ├─► Send: "✅ BRAIN DUMP SAVED TO JOPLIN"
    │   │   │   │
    │   │   │   ├─► Create Decision object:
    │   │   │   │
    │   │   │   │   decision = Decision(
    │   │   │   │       user_id=user_id,
    │   │   │   │       status="SUCCESS",
    │   │   │   │       folder_chosen=final_note.parent_id,
    │   │   │   │       note_title=final_note.title,
    │   │   │   │       note_body=final_note.body,
    │   │   │   │       tags=final_note.tags,
    │   │   │   │       joplin_note_id=note_result["note_id"]
    │   │   │   │   )
    │   │   │   │
    │   │   │   ├─► orch.logging_service.log_decision(decision)
    │   │   │   │
    │   │   │   ├─► IF GOOGLE_TASKS_AVAILABLE AND orch.task_service:
    │   │   │   │   │
    │   │   │   │   ├─► Send: "🚀 Extracting action items..."
    │   │   │   │   │
    │   │   │   │   ├─► created = orch.task_service.create_tasks_from_decision(
    │   │   │   │   │       decision, str(user_id)
    │   │   │   │   │   )
    │   │   │   │   │
    │   │   │   │   ├─► IF created:
    │   │   │   │   │   │
    │   │   │   │   │   ├─► Send: f"✅ Created {len(created)} task(s)"
    │   │   │   │   │   │
    │   │   │   │   │   ├─► status = orch.task_service.get_task_sync_status(user_id)
    │   │   │   │   │   │
    │   │   │   │   │   └─► Send: f"📊 Sync: ✅ {s}, ❌ {f}"
    │   │   │   │   │
    │   │   │   │   └─► ELSE:
    │   │   │   │       │
    │   │   │   │       ├─► has_token = orch.logging_service.load_google_token(user_id)
    │   │   │   │       │
    │   │   │   │       └─► IF has_token:
    │   │   │   │           └─► Send: "❌ Could not create tasks. Check /google_tasks_status"
    │   │   │   │           ELSE:
    │   │   │   │           └─► Send: "❌ No token. Use /authorize_google_tasks"
    │   │   │   │
    │   │   │   └─► (Skip Google Tasks if not available)
    │   │   │
    │   │   └─► ELSE: (note_result is None)
    │   │       └─► Send: "❌ Failed to save note to Joplin"
    │   │
    │   └─► Clear state:
    │       │
    │       ├─► orch.state_manager.clear_state(user_id)
    │       │
    │       └─► Send: "✨ Brain dump session closed..."
    │
    └─► EXCEPT Exception as exc:
        │
        ├─► logger.error(f"Error finishing brain dump: {exc}")
        │
        ├─► Send: "❌ Error occurred, session cleared"
        │
        └─► orch.state_manager.clear_state(user_id)
```

---

## 5. LLM Integration Points

```
LLM Orchestrator Call Points
────────────────────────────

1. During Conversation:
   ┌──────────────────────────────────────────────────────────────┐
   │ orch.llm_orchestrator.process_message(                        │
   │     user_message="My dog needs a vet appointment",           │
   │     context={                                                │
   │         "session_start": "2026-03-04T10:30:00",             │
   │         "item_count": 3                                     │
   │     },                                                       │
   │     persona="gtd_expert",  ◄─ KEY                           │
   │     history=[                                               │
   │         {"role": "assistant", "content": "First question"}, │
   │         {"role": "user", "content": "First answer"},       │
   │         {"role": "assistant", "content": "Second Q"}       │
   │     ]                                                       │
   │ )                                                           │
   └──────────────────────────────────────────────────────────────┘
                              │
                              ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ LLMOrchestrator._get_persona_prompt("gtd_expert")            │
   │                                                              │
   │ Loads: src/prompts/gtd_expert.txt                           │
   │                                                              │
   │ Returns: Complete system prompt with:                       │
   │   - Role definition                                         │
   │   - Session structure (phases)                              │
   │   - Response format (JSON schema)                           │
   │   - Behavioral guidelines                                   │
   └──────────────────────────────────────────────────────────────┘
                              │
                              ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ Build message list:                                          │
   │                                                              │
   │ [                                                            │
   │   {"role": "system", "content": system_prompt},             │
   │   {"role": "assistant", "content": "First question"},       │
   │   {"role": "user", "content": "First answer"},              │
   │   {"role": "assistant", "content": "Second Q"},             │
   │   {"role": "user", "content": "My dog needs a vet apt"}    │
   │ ]                                                           │
   └──────────────────────────────────────────────────────────────┘
                              │
                              ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ Provider.generate_response(                                  │
   │     messages=messages,                                       │
   │     functions=[{...JoplinNoteSchema...}],  ◄─ Structured    │
   │     function_call={"name": "create_joplin_note"},          │
   │     temperature=0.3,  ◄─ Low temp for consistency           │
   │     max_tokens=1000                                         │
   │ )                                                           │
   └──────────────────────────────────────────────────────────────┘
                              │
                              ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ Parse Response:                                              │
   │                                                              │
   │ response = {                                                 │
   │     "function_call": {                                       │
   │         "name": "create_joplin_note",                       │
   │         "arguments": """                                     │
   │         {                                                    │
   │           "status": "NEED_INFO",                            │
   │           "confidence_score": 1.0,                          │
   │           "question": "Got it. What else is urgent?",       │
   │           "log_entry": "In Pressure Release phase",         │
   │           "note": null                                      │
   │         }                                                    │
   │         """                                                 │
   │     }                                                        │
   │ }                                                            │
   │                                                              │
   │ args = json.loads(function_call["arguments"])               │
   │ result = JoplinNoteSchema(**args)                           │
   └──────────────────────────────────────────────────────────────┘
                              │
                              ▼
   Return JoplinNoteSchema to handle_braindump_message()


2. During Finalization (Summary Generation):
   ┌──────────────────────────────────────────────────────────────┐
   │ orch.llm_orchestrator.process_message(                        │
   │     user_message="Please summarize everything into a list",  │
   │     persona="gtd_expert",  ◄─ Same persona for consistency  │
   │     history=[...all conversation turns...]                  │
   │ )                                                           │
   └──────────────────────────────────────────────────────────────┘
                              │
                              ▼
   (Same flow as above, but expect status="SUCCESS" with note)
                              │
                              ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ result.note = {                                              │
   │     "title": "Brain Dump - March 4, 2026",                  │
   │     "body": "## Work\n- Item 1\n## Home\n- Item 2\n...",    │
   │     "parent_id": "Inbox",                                   │
   │     "tags": ["brain-dump", "mindsweep"]                     │
   │ }                                                           │
   └──────────────────────────────────────────────────────────────┘


Response Schema:
────────────────

JoplinNoteSchema {
    status: "NEED_INFO" | "SUCCESS" | (error)
    confidence_score: float (0.0 - 1.0)
    question: str | None  (only if NEED_INFO)
    log_entry: str  (internal decision log)
    note: dict | None  (only if SUCCESS)
        {
            "title": str,
            "body": str,
            "parent_id": str,
            "tags": list[str]
        }
}
```

---

## 6. State Transitions

```
No Session
    │
    ├─ /braindump
    │     ├─ Check whitelist ✓
    │     ├─ No existing session ✓
    │     └─ Create: {"active_persona": "GTD_EXPERT", ...}
    │           │
    │           ▼
    │    ┌──────────────────────────────┐
    │    │ SESSION ACTIVE               │
    │    │ - Listening for messages     │
    │    │ - Each message → LLM         │
    │    │ - Update history             │
    │    └──────────────────────────────┘
    │           │
    │           ├─ LLM: NEED_INFO
    │           │  └─ Continue loop
    │           │
    │           ├─ LLM: SUCCESS
    │           │  └─ _finish_session()
    │           │       └─ Save to Joplin
    │           │       └─ Extract tasks
    │           │       └─ clear_state() ──┐
    │           │                          │
    │           ├─ /braindump_stop         │
    │           │  └─ Force finish         │
    │           │       └─ Generate summary│
    │           │       └─ Save to Joplin  │
    │           │       └─ clear_state() ──┤
    │           │                          │
    │           └─ Error/Exception         │
    │              └─ clear_state() ───────┤
    │                                      │
    └──────────────────────────────────────┘
                                 │
                                 ▼
                       No Session (Ready for new)
```

---

## 7. Data Flow: User Input → Joplin Note

```
User Input
    │
    ▼ "My dog needs a vet appointment"
    │
handle_braindump_message()
    │
    ├─► Append to history: {"role": "user", "content": "..."}
    │
    ├─► Call LLM (with all previous turns)
    │
    └─► LLM Response
        │
        ├─► Append to history: {"role": "assistant", "content": "..."}
        │
        └─► Check status:
            │
            ├─► "NEED_INFO"
            │   │
            │   ├─► Update state["conversation_history"]
            │   │
            │   └─► User sees next question
            │
            └─► "SUCCESS"
                │
                ├─► received_note = {
                │       "title": "...",
                │       "body": "## Work\n - Dog vet appt\n...",
                │       "parent_id": "Inbox",
                │       "tags": ["brain-dump"]
                │   }
                │
                ├─► _finish_session(note_data=received_note)
                │
                ├─► Resolve folder ID
                │
                ├─► create_note_in_joplin(orch, received_note)
                │       │
                │       ▼
                │   Joplin API: POST /notes
                │       │
                │       ▼
                │   Returns: {"note_id": "abc123", ...}
                │
                ├─► Log decision to database
                │
                ├─► Extract tasks (optional)
                │
                ├─► Send success messages
                │
                └─► clear_state()


Result in Joplin:
─────────────────
Title: Brain Dump - March 4, 2026
Folder: Inbox
Tags: brain-dump, mindsweep
Body:
    ## Work
    - Email client redesign meeting
    - Review Q1 budget

    ## Home
    - Schedule vet appointment for dog
    - Buy groceries

    ## Paperwork
    - Renew car registration (expires June)
```

---

## 8. Error Paths

```
Error Scenarios
───────────────

1. Whitelist Check:
   /braindump (non-whitelisted user)
   │
   ├─► check_whitelist(user_id) → False
   │
   └─► Return (no response sent)


2. Existing Session:
   /braindump (session already active)
   │
   ├─► get_state(user_id) → found
   ├─► active_persona == "GTD_EXPERT" → True
   │
   └─► "💡 You already have an active session"


3. No Active Session:
   /braindump_stop (no session)
   │
   ├─► get_state(user_id) → None OR active_persona != "GTD_EXPERT"
   │
   └─► "❌ You don't have an active session"


4. LLM Processing Error:
   During conversation:
   │
   ├─► await process_message(...) → Exception
   │
   ├─► logger.error(...)
   │
   └─► "❌ Sorry, had trouble processing. Continue or /braindump_stop"


5. Joplin Save Error:
   _finish_session():
   │
   ├─► await create_note_in_joplin(...) → None/Exception
   │
   ├─► logger.error(...)
   │
   ├─► "❌ Failed to save note to Joplin"
   │
   └─► clear_state()  (even if failed, cleanup)


6. Folder Not Found:
   _finish_session():
   │
   ├─► Search for "Inbox" folder → not found
   │
   ├─► Fallback: use folders[0] (first available)
   │   OR leave as "Inbox" and let Joplin handle


7. Google Tasks Error:
   _finish_session() (if GOOGLE_TASKS_AVAILABLE):
   │
   ├─► create_tasks_from_decision(...) → None
   │
   ├─► Check if token exists
   │
   ├─► IF token missing:
   │   └─► "❌ No Google Tasks token. Use /authorize_google_tasks"
   │
   └─► IF token exists but failed:
        └─► "❌ Could not create tasks. Check /google_tasks_status"
```

