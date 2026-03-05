# Bug Fix: BF-011 - ContentDecision Validation Error + Greeting Should Show Menu

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 1
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Backlog

## Description

**Part A (Validation)**: When the LLM processes a message for content routing (note vs task vs both), it returns a structured `ContentDecision`. The LLM sometimes returns `content_type: null` instead of a valid string. Pydantic validation fails because `content_type` expects a string, causing "Routing failed" and the user sees an error instead of the expected response.

**Part B (Greeting behavior)**: Greetings like "hello", "hi", "hey" should **never** trigger an LLM question or content routing. They should immediately show the menu of tasks/commands (the greeting response). This applies even when the user has pending clarification state from a previous message—"hello" should act as an escape hatch to clear pending state and show the menu.

## Steps to Reproduce

1. Send a message that triggers content routing (e.g., "Create a task I'm wondering if you can understand what I'm talking looks like yo" or similar).
2. LLM responds with structured output including `"content_type": null` or omits it.
3. Observe: Routing fails with Pydantic ValidationError.

## Expected Behavior

- Bot routes the message and creates a note, task, or both as appropriate.
- User receives a valid response.
- **Greetings** ("hello", "hi", "hey", etc.): Show the menu of tasks/commands immediately. Do **not** trigger LLM content routing or clarification questions.

## Actual Behavior

- Routing fails with:
  ```
  Routing failed: 1 validation error for ContentDecision
  content_type
    Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
  ```
- User sees "Something went wrong" or similar error.

## Environment

- **Platform**: Telegram (production)
- **Bot**: Deployed on Fly.io
- **User ID**: 7256045321 (from logs)
- **Trigger**: Message routed through `process_message_for_routing()` (DeepSeek/OpenAI or Ollama)

## Screenshots/Logs

```
{"event": "Routing failed: 1 validation error for ContentDecision\ncontent_type\n  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]\n    For further information visit https://errors.pydantic.dev/2.12/v/string_type", "exc_info": ["<class 'pydantic_core._pydantic_core.ValidationError'>", "1 validation error for ContentDecision\ncontent_type\n  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]\n    For further information visit https://errors.pydantic.dev/2.12/v/string_type", "<traceback object at 0x7fe5a636b480>"]}
```

## Technical Details

- `ContentDecision` in `llm_orchestrator.py` defines `content_type: str` (required, non-optional).
- `args.setdefault("content_type", "note")` only adds the key when missing; it does not replace `None` when the LLM returns `"content_type": null`.
- Both DeepSeek/OpenAI (function call) and Ollama (JSON extraction) paths were affected.

## Root Cause

LLM returns `content_type: null` or omits it in some edge cases. `setdefault` does not handle explicit `None` values.

## Solution

### Part A (Implemented)

1. After `args.setdefault("content_type", "note")`, add `args["content_type"] = args.get("content_type") or "note"` to normalize both missing and `None` values.

2. Applied in both code paths:
   - DeepSeek/OpenAI: `process_message_for_routing()` function-call parsing
   - Ollama: `process_message_for_routing()` JSON extraction from content

### Part B (Implemented)

1. **Check greeting before pending state**: In `_message` handler (`src/handlers/core.py`), treat greetings as a top-level escape. When `_is_greeting(validated)` is true:
   - Clear any pending state (`orch.state_manager.clear_state(user_id)`)
   - Send the greeting/menu response
   - Return immediately (do not route to LLM or clarification handler)

2. **Fix applied**: Changed from `if not pending and _is_greeting(validated)` to `if _is_greeting(validated):`. Greeting check now runs regardless of pending state. "hello" acts as escape hatch to clear pending and show menu.

## Technical References

- File: `src/llm_orchestrator.py`
  - `ContentDecision` class (lines 37–53)
  - `process_message_for_routing()` (lines 330–413)
  - `_create_content_decision_error()` — fallback when parsing fails
- File: `src/handlers/core.py`
  - `_message` handler (lines 507–561): greeting check at 534–537, pending-state handling at 540–556
  - `_is_greeting()`, `GREETING_PATTERNS`, `_build_greeting_response()`

## Testing

- [ ] Manual: Send message that previously triggered the error; verify routing succeeds.
- [ ] Verify in production (Fly.io) after deploy.
- [x] **Greeting**: Send "hello" with no pending state → menu shown, no LLM.
- [x] **Greeting with pending**: Greeting check runs first; "hello" clears pending, shows menu, no LLM.

## Notes

- Error occurs intermittently depending on LLM output.
- Fix is defensive: ensures `content_type` is always a valid string before constructing `ContentDecision`.

## History

- 2026-03-05 - Created
- 2026-03-05 - Part A completed: Added `args["content_type"] = args.get("content_type") or "note"` in both routing paths
- 2026-03-05 - Part B added: Greeting ("hello") must show menu, never trigger LLM; fix greeting check to run even when pending
- 2026-03-05 - Part B completed: Greeting check now runs regardless of pending state; clears state and shows menu
