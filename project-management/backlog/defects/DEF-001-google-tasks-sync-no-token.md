# Defect: DEF-001 - Google Tasks Sync Fails with "No Google token found for user"

**Status**: ✅ Completed  
**Priority**: 🟠 High  
**Story Points**: 2  
**Created**: 2026-03-01  
**Updated**: 2026-03-01  
**Assigned Sprint**: Backlog

## Description

Google Tasks sync status shows 0 synced, 1 failed. Sync fails with error: "No Google token found for user 7256045321". User sees failed sync in "Recent syncs" and "Failed syncs" with no successful syncs. 

## Steps to Reproduce

1. Have a Telegram user (e.g. user ID 7256045321) who has not completed Google OAuth or whose token is missing/expired.
2. Trigger or run Google Tasks sync for that user (e.g. via sync status command or scheduled sync).
3. Observe sync result.

**Precondition**: User exists in system but has no valid Google OAuth token stored (never linked or token lost/expired).

## Expected Behavior

- Either: User is prompted to link Google account (OAuth flow) before sync runs, and sync does not run until token exists.
- Or: Sync is skipped for users without a token with a clear, user-facing message (e.g. "Link your Google account first") instead of counting as a failed sync.

## Actual Behavior

- Sync runs and fails with: "No Google token found for user 7256045321".
- Sync is counted as **Failed** (e.g. "Failed: 1", "❌ Failed syncs: 1").
- Recent syncs show: "❌ none - 2026-02-27 03:36:55".
- Total synced: 0, Successful: 0, Failed: 1.

## Environment

- **Context**: Google Tasks sync (feature from US-012).
- **User**: Telegram user ID 7256045321.
- **Observed**: 2026-02-27 03:36:55 (recent sync); status observed 2026-03-01.

## Screenshots/Logs

**Sync status output:**
```
Total synced: 0
✅ Successful: 0
❌ Failed: 1

Recent syncs:
❌ none - 2026-02-27 03:36:55

⚠️ Failed syncs: 1
• No Google token found for user 7256045321
```

## Technical Details

- Sync logic attempts to run for the user without checking for (or handling missing) Google token first.
- "No Google token found" is treated as a sync failure rather than "no sync attempted" or "action required: link account".
- UX impact: User sees a failed sync and may not know they need to link Google or re-authorize.
- I am wondering if the token does not expires and we need to refreshit

## Root Cause

In `TaskService.create_tasks_from_decision`, when the user has no Google token the code logged a **task_sync** row with `sync_result="failed"` and `error_message="No Google token found for user {user_id}"`. That is incorrect: no sync was attempted, so it should not be recorded as a failed sync. The status UI (`get_task_sync_status` / `/tasks_status`) reads `task_sync_history` and shows failed_count and failed_syncs, so the user saw "Failed: 1" and the error message.

## Solution

- **Implemented**: When token is missing in `create_tasks_from_decision`, do **not** call `log_task_sync`. Skip task creation and return `[]`; log a warning to console only. Sync status then shows 0 failed for "no token" (no new failed row is written).
- Handlers already show a clear message when the user has no token: `/tasks_status` and list-inbox reply with "Google Tasks not authorized — Use /authorize_google_tasks to set up access".

## Reference Documents

- [US-012](../user-stories/US-012-google-tasks-integration.md) - Google Tasks Integration

## Technical References

- **File**: `src/task_service.py`
- **Method**: `TaskService.create_tasks_from_decision()` (lines ~162–171): removed `log_task_sync(..., "failed", error_msg)` when `load_google_token(user_id)` returns None.
- **Status aggregation**: `TaskService.get_task_sync_status()` uses `LoggingService.get_failed_syncs(user_id)` which queries `task_sync_history` where `sync_result = 'failed'`.
- **Handlers**: `src/handlers/google_tasks.py` — `_tasks_status` and `_list_inbox_tasks` already check token and reply with link-authorize message before calling task_service.

## Testing

- [ ] Unit test added/updated
- [ ] Integration test added/updated
- [ ] Manual testing completed (user with no token → clear message, no false "failed" count)
- [ ] Regression: user with valid token still syncs successfully

## Notes

- User 7256045321 may need to (re-)complete Google OAuth to get a token; fix should improve messaging and failure semantics for all users in this state.
- **Cleanup**: Existing false "failed" rows can be removed with `LoggingService.delete_failed_syncs_no_token()` or by running `python scripts/cleanup_no_token_sync_failures.py` once.

## History

- 2026-03-01 - Created
- 2026-03-01 - Branch fix/DEF-001-google-tasks-sync-no-token; stop logging "failed" when no token in create_tasks_from_decision (task_service.py)
- 2026-03-01 - Added LoggingService.delete_failed_syncs_no_token() and scripts/cleanup_no_token_sync_failures.py for one-off DB cleanup
- 2026-03-01 - Fix committed on branch fix/DEF-001-google-tasks-sync-no-token (dd4c132)
