# Google Tasks OAuth and Token Refresh

This document describes how the bot stores and refreshes Google OAuth tokens for the Tasks API, and when users need to re-authorize.

## Overview

- **Access token**: Short-lived (~1 hour). Used for API requests.
- **Refresh token**: Long-lived. Used to obtain new access tokens without user interaction.
- We request **offline access** (`access_type=offline`, `prompt=consent`) so Google issues a refresh token at authorization time.
- **Auto-refresh**: `OAuth2Session` is configured with `auto_refresh_url` and `token_updater` so expired tokens are refreshed automatically before API calls. The refreshed token is persisted via the callback.

## Why Re-authorization Was Needed Often (Fixed)

Previously, users had to run `/authorize_google_tasks` repeatedly because:

1. **Access tokens expire** (~1 hour). The app correctly refreshed them using the refresh token when a request returned 401.
2. **Google’s refresh response** only returns `access_token` and `expires_in` — it does **not** return a new `refresh_token`.
3. **Bug**: We overwrote the stored token with the refresh response. That dropped the `refresh_token`, so the next time the access token expired we could no longer refresh and the user had to re-authorize.

**Fix**: When refreshing, we merge the new token with the previous one and preserve `refresh_token` if the new response doesn’t include it. We also persist the refreshed token (with the preserved `refresh_token`) after any Tasks API call that may have triggered a refresh (e.g. creating tasks from notes, listing tasks).

See: `GoogleTasksClient.refresh_token()` in `src/google_tasks_client.py`, and token saving in `src/task_service.py` and `src/handlers/google_tasks.py`.

## When Re-authorization Is Still Required

Users need to run `/authorize_google_tasks` again only if:

- They **revoke** the app’s access in their [Google account security settings](https://myaccount.google.com/permissions).
- The **refresh token is revoked or expires** (e.g. long inactivity, or Google policy limits; see [Google’s token expiration](https://developers.google.com/identity/protocols/oauth2#expiration)).
- The **database** that stores tokens is reset or lost (e.g. new deployment without persistent volume).

## Implementation Notes

- **Storage**: Tokens are stored in SQLite (`google_tokens` table) via `LoggingService.save_google_token` / `load_google_token`. Path is controlled by `LOGS_DB_PATH` (default `data/bot/bot_logs.db`).
- **Refresh**: Any code path that uses `GoogleTasksClient` may trigger a refresh on 401. After a successful refresh, the client’s `token` is updated; callers that have a reference to the original token should persist the client’s token when `client.token != original_token` so the DB gets the new access token and the preserved refresh token.
- **Scopes**: We use `https://www.googleapis.com/auth/tasks` only.

## Token Validation

- **`/google_tasks_status`** validates the token by making a lightweight API call before showing sync status. If the token is expired, it is refreshed automatically. If refresh fails, the user is prompted to re-authorize.

## Related Code

| File | Responsibility |
|------|----------------|
| `src/google_tasks_client.py` | OAuth session with auto_refresh, `set_token(..., token_updater=)`, Tasks API calls |
| `src/auth_service.py` | Authorization URL and code exchange (initial auth) |
| `src/logging_service.py` | `save_google_token`, `load_google_token` |
| `src/task_service.py` | Load token, set on client, call API, save token if refreshed |
| `src/handlers/google_tasks.py` | OAuth flow, list tasks, status; save token if refreshed |
