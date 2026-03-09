# Defect: DEF-027 - Braindump: Google Tasks Creation Fails with token_expired, Generic Error Shown

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 2
**Created**: 2026-03-09
**Updated**: 2026-03-09
**Assigned Sprint**: Backlog

---

## Problem Statement

When a brain dump session completes successfully and the bot attempts to extract action items to Google Tasks, task creation fails silently if the Google OAuth token has expired. The user receives a generic error that hides the real cause; discovering that re-authentication is needed requires running a separate command.

**User impact:** Trust erosion. The user just completed a mind sweep, captured valuable items, and saw "BRAIN DUMP SAVED TO JOPLIN" — then "Could not create Google Tasks. Check /tasks_status for details." They must run `/tasks_status` to learn the reason is `token_expired`, and may not know that `/tasks_connect` will fix it.

---

## Evidence

**From Fly.io logs (2026-03-09 04:49–04:52 UTC):**
- Brain dump session completed; note saved to Joplin ("BRAIN DUMP SAVED TO JOPLIN")
- Bot showed "Extracting action items to Google Tasks..."
- Task creation failed; user saw "Could not create Google Tasks. Check /tasks_status for details."
- `/tasks_status` revealed: "Failed syncs: 1 (token_expired)"

**User report:** "braindump got an error while saving a task" (captured via fallback task creation)

---

## Root Cause Analysis

### Technical Flow

1. **Token refresh exists:** `GoogleTasksClient` uses `OAuth2Session` with `auto_refresh_url` and `token_updater`. On 401/token_expired, it calls `refresh_token()` and retries.
2. **Refresh can fail:** When the refresh token is revoked, expired, or invalid, `refresh_token()` returns `None` and the client raises `GoogleAuthError("Token expired and refresh failed")`.
3. **Error is swallowed:** In `task_service.create_tasks_from_decision()`, the exception is caught (lines 522–531), logged to `log_task_sync` with `error_msg`, and the function returns an empty list. No error type or reason is propagated to the caller.
4. **Handler shows generic message:** The braindump handler (and core handler) checks `if created:` vs `else:`. When `created` is empty, it shows "Could not create Google Tasks. Check /tasks_status for details." — regardless of whether the cause was no token, token_expired, rate limit, or network error.

### Why Refresh Fails

- User revoked OAuth access in Google account settings
- Refresh token expired (Google refresh tokens can expire after 6 months of inactivity or when credentials change)
- Stored token corrupted or missing `refresh_token`
- Network/API transient failure during refresh

---

## Solution Options

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **A** | Surface error reason in handler | Minimal code change; reuses existing `log_task_sync` data | Requires `create_tasks_from_decision` to return error info |
| **B** | Proactive token check before task creation | Catches expired token before user sees "Extracting..."; can show message immediately | Extra API call; may still fail between check and create |
| **C** | Raise `GoogleAuthError` from task_service; handler catches it | Clear separation; handler can show specific message for auth errors | Requires exception handling in all callers (braindump, core, etc.) |
| **D** | Return `(created_tasks, error_reason)` tuple | Explicit; no exceptions | Breaking change to return type; all callers must update |

### Recommended: **Option C** (raise) + **Option A** (fallback)

1. **In `create_tasks_from_decision`:** When token refresh fails, re-raise `GoogleAuthError` instead of catching and returning empty. For other exceptions, keep current behavior (log, return empty).
2. **In braindump and core handlers:** Catch `GoogleAuthError` and show: "🔑 Google token expired or revoked. Use /tasks_connect to re-authenticate."
3. **Fallback:** If we cannot easily propagate the error, query the most recent failed sync reason from `log_task_sync` and, if it contains "token_expired" or "refresh", show the re-auth message.

---

## Acceptance Criteria

- [x] When Google Tasks creation fails due to token_expired or refresh failure, the user sees: **"🔑 Google token expired or revoked. Use /tasks_connect to re-authenticate."**
- [x] The generic "Check /tasks_status for details" is not shown for auth-related failures.
- [x] Other failure types (rate limit, network, etc.) continue to show the generic message or a specific message if we add them later.
- [x] Affected flows: braindump post-save task extraction, default persona task creation, `/task` command, project selection reply/callback, planning, stoic tomorrow task.
- [x] No regression: successful task creation and "no token" (user never connected) flows unchanged.

---

## Affected Code

| File | Change |
|------|--------|
| `src/task_service.py` | In `create_tasks_from_decision`, catch `GoogleAuthError` separately and re-raise (or return error reason). For other exceptions, keep current behavior. |
| `src/handlers/braindump.py` | Catch `GoogleAuthError`; show re-auth message instead of generic. |
| `src/handlers/core.py` | Same for default persona task creation path. |
| `src/handlers/google_tasks.py` | If `/task` command uses `create_tasks_from_decision` or similar, add same handling. |

---

## Implementation Guide

### Step 1: Propagate auth error from task_service

```python
# task_service.create_tasks_from_decision
except GoogleAuthError:
    raise  # Let caller handle auth-specific message
except Exception as e:
    # ... existing log and return []
```

### Step 2: Handle in braindump handler

```python
try:
    created = orch.task_service.create_tasks_from_decision(...)
except GoogleAuthError:
    await message.reply_text(
        "🔑 Google token expired or revoked. Use /tasks_connect to re-authenticate."
    )
    created = []
else:
    if created:
        # ... success path
    else:
        # ... existing generic path (for other failures)
```

### Step 3: Same pattern in core handler (and any other callers)

---

## Testing

- [x] **Unit test:** Mock `create_task` to raise `GoogleAuthError`; assert braindump handler shows re-auth message.
- [x] **Unit test:** Mock token refresh failure; assert `create_tasks_from_decision` raises `GoogleAuthError`.
- [ ] **Manual:** Revoke OAuth in Google account → run braindump → verify re-auth message.
- [x] **Regression:** Normal flow (valid token) still works; user without token still sees "Use /tasks_connect first."

---

## References

- [DEF-001: Google Tasks Sync No Token](DEF-001-google-tasks-sync-no-token.md) — related token handling; different scenario (no token vs expired)
- [US-035: World-Class Brain Dump](../user-stories/US-035-world-class-brain-dump.md) — brain dump is a core capture ritual; task extraction failure undermines trust
- [US-012: Google Tasks Integration](../user-stories/US-012-google-tasks-integration.md) — task creation feature
- `src/google_tasks_client.py` — `GoogleAuthError`, `refresh_token()`, token_expired handling
- `src/task_service.py` — `create_tasks_from_decision`, `_set_client_token`

---

## Success Metrics

- User sees actionable message ("Use /tasks_connect") within the same reply as the failure — no need to run `/tasks_status`.
- Zero increase in "braindump got an error" fallback tasks created for token_expired (users understand and can self-serve).

---

## Solution Implemented (Option C)

1. **task_service.create_tasks_from_decision**: Added `except GoogleAuthError: raise` in three places (get_default_task_list block, inner create_task loop, outer try) so auth errors propagate.
2. **task_service.create_task_with_metadata**: Already re-raises; no change needed.
3. **Handlers**: Added `except GoogleAuthError` with re-auth message in:
   - braindump._finish_session
   - core: is_action_item block, task-only routing, both (note+task) routing, project selection reply, project selection callback
   - planning._finish_planning and _create_priority_tasks
   - stoic._create_tomorrow_task_from_stoic
4. **Unit tests**: test_create_tasks_from_decision_re_raises_google_auth_error, test_finish_session_shows_reauth_on_google_auth_error

## History

- 2026-03-09 - Created from Fly.io logs; user reported via task creation fallback
- 2026-03-09 - Enhanced to world-class: root cause analysis, solution options, acceptance criteria, implementation guide
- 2026-03-09 - Implemented Option C; all callers updated; unit tests added; completed
