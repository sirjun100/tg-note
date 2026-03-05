# Bug Fix: BF-006 - Stoic Journal: Session Gets Stuck in Loop with No Cancel Option

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 3
**Created**: 2026-03-04
**Updated**: 2026-03-06
**Assigned Sprint**: Backlog

## Description

When a user starts a Stoic journal session with `/stoic`, `/stoic morning`, or `/stoic evening`, but then decides not to provide answers, they become trapped in an active session with no way to cancel or restart it. The session persists indefinitely, blocking any new journal sessions from being started.

## Steps to Reproduce

1. User sends `/stoic morning`
2. Bot asks the first question
3. User decides they don't want to journal right now and doesn't answer
4. User waits or leaves the chat
5. User tries to start a new journal session with `/stoic evening`
6. Bot responds: "📓 You already have a Stoic journal session. Keep replying, or use /stoic_done to save."
7. User has only two options:
   - Continue answering questions for the unwanted morning session
   - Use `/stoic_done` which saves partial/empty answers to the journal
8. **There is no way to cancel the session without polluting the journal.**

## Expected Behavior

When a user starts a Stoic journal session, they should have the ability to:
1. **Cancel the session** using a `/stoic_cancel` command that clears the session state without saving
2. **Start a new session** by calling `/stoic` again, which should prompt them to confirm they want to abandon the current session
3. **Timeout** — A session that is inactive for more than X minutes should auto-cancel (optional enhancement)

## Root Cause

`src/handlers/stoic.py` lines 358-363 check if a session is already active:

```python
state = orch.state_manager.get_state(user_id)
if state and state.get("active_persona") == "STOIC_JOURNAL":
    await update.message.reply_text(
        "📓 You already have a Stoic journal session. "
        "Keep replying, or use /stoic_done to save."
    )
    return
```

This blocks the user from starting a new session or canceling the current one. There is no `/stoic_cancel` command, and no way to override an existing session.

## Proposed Solution

### 1. Add `/stoic_cancel` command

Create a new handler that clears the active session without saving:

```python
def _stoic_cancel(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return

        user_id = user.id
        state = orch.state_manager.get_state(user_id)

        if not state or state.get("active_persona") != "STOIC_JOURNAL":
            await update.message.reply_text("No active Stoic journal session to cancel.")
            return

        mode = state.get("mode", "morning")
        orch.state_manager.clear_state(user_id)
        logger.info("User %s cancelled Stoic journal session (%s)", user_id, mode)
        await update.message.reply_text(
            "❌ Stoic journal session cancelled. No changes were saved.\n\n"
            "Start a new session with /stoic, /stoic morning, or /stoic evening."
        )

    return handler
```

Register it in `register_stoic_handlers()`:

```python
application.add_handler(CommandHandler("stoic_cancel", _stoic_cancel(orch)))
```

### 2. Add option to override existing session (optional)

Allow starting a new session with a flag that cancels the existing one:

```python
# In _stoic() handler, after line 357:
state = orch.state_manager.get_state(user_id)
if state and state.get("active_persona") == "STOIC_JOURNAL":
    # Check if user passed --force flag
    if context.args and "--force" in [arg.lower() for arg in context.args]:
        orch.state_manager.clear_state(user_id)
        await update.message.reply_text("Previous session cancelled. Starting new session...\n")
    else:
        await update.message.reply_text(
            "📓 You already have a Stoic journal session in progress.\n\n"
            "• Keep replying to complete it\n"
            "• /stoic_done to save it\n"
            "• /stoic_cancel to abandon it\n"
            "• /stoic --force to start over (cancels current session)"
        )
        return
```

### 3. Update user help text

When `/stoic_done` is called with no answers, provide a clearer message:

```python
if not answers:
    await message.reply_text(
        "No answers recorded. Use /stoic_cancel to discard this session, "
        "or add some reflection before calling /stoic_done."
    )
    return False
```

## Technical References

- File: `src/handlers/stoic.py` — session creation and management
- File: `src/handlers/stoic.py:335-339` — `register_stoic_handlers()` registration point
- File: `src/telegram_orchestrator.py` — `state_manager` API for session storage

## Testing

- [ ] Verify `/stoic_cancel` command clears active session
- [ ] Verify `/stoic_cancel` returns error when no active session exists
- [ ] Verify user can start a new session after canceling with `/stoic_cancel`
- [ ] Verify `/stoic_done` with no answers shows appropriate message (if implementing step 3)
- [ ] Verify `/stoic --force` cancels existing session and starts new one (if implementing step 2)
- [ ] Verify user help text mentions `/stoic_cancel` as an option

## Dependencies

- None (self-contained in `src/handlers/stoic.py`)

## Notes

- The `/stoic_cancel` command is the minimal solution and most critical
- The `--force` override is a convenience feature for power users
- Consider adding a timeout mechanism in the state manager to auto-expire stale sessions (enhancement for future)

## History

- 2026-03-04 - Created (user-reported: unable to cancel stuck stoic session)
- 2026-03-06 - Verified fixed: `/stoic_cancel` implemented in `src/handlers/stoic.py` (lines 279–306)
