# User Story: US-022 - Enforce Single Machine Limit on Fly.io

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 1
**Created**: 2026-03-03
**Updated**: 2026-03-03
**Assigned Sprint**: Backlog

## Description

Ensure that the Fly.io deployment never scales beyond 1 machine, regardless of load. The application uses a single SQLite database on a mounted volume, and Joplin CLI runs inside the container — multiple machines would cause data corruption and split-brain issues. The configuration should explicitly cap the machine count at 1.

## User Story

As the bot operator,
I want to guarantee only one machine ever runs at a time,
so that my SQLite databases, Joplin state, and mounted volume are never accessed concurrently by multiple machines.

## Acceptance Criteria

- [x] `fly.toml` sets `max_machines_running = 1` under `[http_service]` (line 25)
- [x] `fly scale count` is capped at 1 (scheduler workflow only uses 0 or 1)
- [x] Fly.io does not auto-scale beyond 1 machine under load (`max_machines_running = 1`)
- [x] Document the single-machine constraint and why it exists (this document + fly.toml comments)

## Why This Matters

The application has several components that are inherently single-instance:

1. **SQLite databases** — `conversation_state.db`, `logs.db` are stored on the mounted volume. Two machines writing to the same SQLite file simultaneously would corrupt the database.
2. **Joplin CLI** — runs inside the container with a profile directory on the mounted volume. Two Joplin processes syncing the same profile would cause conflicts.
3. **Telegram webhook** — Telegram sends webhooks to a single URL. If Fly load-balances across multiple machines, messages could arrive at either machine, causing inconsistent state.
4. **Mounted volume** — `telegram_joplin_data` can only be attached to one machine at a time on Fly.io (volumes are not shared storage).

## Current Configuration

`fly.toml` currently has:

```toml
[http_service]
  auto_stop_machines = 'stop'
  auto_start_machines = true
  min_machines_running = 0
  # max_machines_running is NOT set — Fly.io default may allow scaling beyond 1
```

## Proposed Change

```toml
[http_service]
  auto_stop_machines = 'stop'
  auto_start_machines = true
  min_machines_running = 0
  max_machines_running = 1
```

Additionally, verify the machine count is set to 1:

```bash
fly scale show -a telegram-joplin
# Should show: Count = 1
# If not: fly scale count 1 -a telegram-joplin
```

## Technical References

- File: `fly.toml` (lines 18–24)
- File: `.github/workflows/fly-schedule-scale.yml` (already caps at 0 or 1)
- [Fly.io auto-scaling docs](https://fly.io/docs/reference/configuration/#http_service)

## Dependencies

None.

## Notes

- The `fly-schedule-scale.yml` workflow already only scales between 0 and 1, so the scheduler is safe.
- The risk is Fly.io's built-in auto-scaling, which could spin up additional machines under high traffic if `max_machines_running` is not explicitly set.
- Fly.io volumes can only attach to one machine, so in practice a second machine would fail to start — but it's better to prevent the attempt entirely.

## History

- 2026-03-03 - Created
- 2026-03-03 - Completed: added max_machines_running = 1 to fly.toml
