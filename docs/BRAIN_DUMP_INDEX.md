# Brain Dump Documentation Index

Complete reference documentation for the `/braindump` feature (GTD mind sweep).

**Last Updated:** 2026-03-04
**Feature Status:** Production-ready
**Complexity Level:** Medium (stateful conversation with LLM)

---

## Documentation Files

### 1. **brain-dump-quick-reference.md** ⚡
**Start here** if you need a quick overview or are debugging.

**Contains:**
- File map (which file does what)
- Command summary (what each `/braindump*` command does)
- State structure (what data is stored)
- Message flow (how user input → LLM → response)
- LLM response schema (what LLM returns)
- Key APIs (state_manager, llm_orchestrator, etc.)
- Common patterns (code snippets)
- Debug checklist

**Time to read:** 5 minutes
**Best for:** Quick lookup, onboarding, debugging

---

### 2. **brain-dump-implementation-guide.md** 📖
**Read this** if you're implementing the feature or need to understand every detail.

**Contains:**
- Feature overview (what is it, why exists)
- Architecture & flow diagram (big picture)
- Session lifecycle (step-by-step: start → conversation → finish)
- Detailed component breakdown (state, LLM, persona)
- LLM integration (how the orchestrator works)
- Message handling loop (complete code flow)
- Note creation & finalization (saving to Joplin)
- Google Tasks integration (optional feature)
- Error handling strategy (all error paths)
- Testing checklist (unit, integration, manual tests)
- Code examples (real code for each step)

**Time to read:** 30-40 minutes
**Best for:** Full implementation, understanding the complete flow

---

### 3. **brain-dump-flow-diagrams.md** 📊
**Look here** if you're visual and want to understand the flow without reading prose.

**Contains:**
- High-level session lifecycle diagram
- Message processing state machine
- Detailed message handler flow (with all branches)
- Session finalization flow (step-by-step)
- LLM integration points (how LLM is called)
- State transitions (session creation → end)
- Data flow: User input → Joplin note (complete journey)
- Error paths (what happens when things fail)

**Time to read:** 10-15 minutes
**Best for:** Visual learners, presentation, documenting architecture

---

### 4. **brain-dump-prompt-tuning.md** 🎯
**Read this** if you need to adjust the LLM behavior or create prompt variants.

**Contains:**
- Current prompt structure (how it's organized)
- Prompt design principles (what makes it work)
- Session phases deep dive (Pressure Release, Quick Sweep, Stragglers)
- Tuning techniques (how to change behavior)
- Response format constraints (JSON schema requirements)
- Testing & iteration (A/B testing framework)
- Common issues & fixes (problems and solutions)
- Prompt maintenance checklist

**Time to read:** 20-25 minutes
**Best for:** LLM prompt engineering, tuning behavior, fixing issues

---

### 5. **BRAIN_DUMP_INDEX.md** (this file) 📑
Navigation guide for all brain dump documentation.

---

## Reading Guide by Role

### I'm a new developer implementing the feature
1. Start: **quick-reference.md** (5 min overview)
2. Read: **implementation-guide.md** (understand every detail)
3. Reference: **flow-diagrams.md** (visualize the flow)
4. Code: Check `src/handlers/braindump.py` and `src/llm_orchestrator.py`

### I'm debugging a broken brain dump session
1. Check: **quick-reference.md** → Debug Checklist section
2. Read: **flow-diagrams.md** → Error Paths section
3. Reference: **implementation-guide.md** → Error Handling Strategy

### I'm tuning the LLM prompt for better sessions
1. Read: **prompt-tuning.md** (full guide)
2. Reference: `src/prompts/gtd_expert.txt` (actual prompt)
3. Test: Use A/B testing framework from prompt-tuning.md

### I want a 2-minute overview
1. Read: **quick-reference.md** → Summary section

### I'm presenting this feature to others
1. Use: **flow-diagrams.md** (visual, professional)
2. Reference: **implementation-guide.md** for details

---

## Key Files (Non-Documentation)

```
src/
├── handlers/braindump.py              # Main handler code
│   ├── register_braindump_handlers()
│   ├── _braindump()
│   ├── _braindump_stop()
│   ├── handle_braindump_message()     ← Core loop
│   └── _finish_session()
├── llm_orchestrator.py                # LLM interface
│   ├── LLMOrchestrator.process_message()
│   └── JoplinNoteSchema
├── prompts/
│   └── gtd_expert.txt                 # LLM system prompt
└── handlers/core.py
    ├── Message router
    └── create_note_in_joplin()

tests/
└── test_braindump.py                  # If it exists

docs/
├── brain-dump-implementation-guide.md
├── brain-dump-flow-diagrams.md
├── brain-dump-prompt-tuning.md
├── brain-dump-quick-reference.md
└── BRAIN_DUMP_INDEX.md                (this file)
```

---

## Architecture Summary

```
User sends /braindump
    ↓
Handler: _braindump()
    ├─ Create state: {"active_persona": "GTD_EXPERT", ...}
    ├─ Load first question from gtd_expert.txt
    ├─ Send first question
    └─ Wait for user message

User sends message
    ↓
Core Router → handle_braindump_message()
    ├─ Get state
    ├─ Build conversation history
    ├─ Call: LLMOrchestrator.process_message(
    │     user_message=text,
    │     persona="gtd_expert",
    │     history=[...previous turns...]
    │  )
    ├─ LLM returns: JoplinNoteSchema
    │   {
    │     "status": "NEED_INFO" or "SUCCESS",
    │     "question": "Next question",
    │     "note": final_note_dict
    │   }
    ├─ If NEED_INFO: Update history, ask next question
    └─ If SUCCESS: Call _finish_session()

_finish_session()
    ├─ Create/compile final note
    ├─ Resolve Joplin folder
    ├─ Save note: create_note_in_joplin()
    ├─ Log decision to database
    ├─ Extract tasks to Google Tasks (optional)
    ├─ Send success message
    └─ Clear state

Note saved to Joplin
Actions extracted to Google Tasks
Session ends
```

---

## Quick Links

- **Live Prompt:** `src/prompts/gtd_expert.txt`
- **Handler Code:** `src/handlers/braindump.py`
- **LLM Integration:** `src/llm_orchestrator.py`
- **State Management:** Via `TelegramOrchestrator.state_manager`
- **Joplin Client:** Via `TelegramOrchestrator.joplin_client`

---

## Common Questions

**Q: How long should a session take?**
A: ~15 minutes. User is guided through 3 phases: Pressure Release (2-3 min), Quick Sweep (8-10 min), Stragglers (2-3 min). See prompt-tuning.md for tuning.

**Q: What if the user has no active session?**
A: Whitelist check fails silently. Valid user gets "No active session" message on `/braindump_stop`.

**Q: Can users interrupt a session?**
A: Yes, `/braindump_stop` ends it. Also, LLM can auto-finish by returning `status="SUCCESS"`.

**Q: How many items should be captured?**
A: Target is 20-30 items across 7-9 categories. Varies by user and session depth.

**Q: What if Joplin is down?**
A: Error message sent, state is cleared even if save failed. User should try again later.

**Q: Are brain dumps automatically tagged?**
A: Yes, tags include `["brain-dump", "mindsweep"]`. Saved to Inbox or similar folder.

**Q: Can the LLM prompt be changed?**
A: Yes, edit `src/prompts/gtd_expert.txt`. See prompt-tuning.md for guidance.

**Q: Is Google Tasks required?**
A: No. If `GOOGLE_TASKS_AVAILABLE` is False, tasks aren't extracted. Brain dump still works.

---

## Testing

See **implementation-guide.md** → Testing Checklist section for:
- Unit tests to write
- Integration tests to run
- Manual QA steps

Or see **quick-reference.md** → Test Cases for a quick checklist.

---

## Version History

```
2026-03-04 - Created complete documentation set
├─ brain-dump-implementation-guide.md (v1)
├─ brain-dump-flow-diagrams.md (v1)
├─ brain-dump-prompt-tuning.md (v1)
├─ brain-dump-quick-reference.md (v1)
└─ BRAIN_DUMP_INDEX.md (v1)
```

---

## Contributing

When updating the brain dump feature:
1. Update relevant documentation files
2. Keep code examples in sync with source files
3. Test any prompt changes with A/B framework (prompt-tuning.md)
4. Update PROMPT_CHANGELOG (if you modify gtd_expert.txt)

---

## Support

For questions about specific parts:
- **Code:** See implementation-guide.md code examples
- **Flow:** See flow-diagrams.md for visual reference
- **Prompt:** See prompt-tuning.md for tuning guidance
- **Quick answers:** See quick-reference.md FAQ section

---

*End of documentation index*
