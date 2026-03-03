# Bug Fix: BF-003 - Scheduler Service Not Working

**Status**: ⭕ Not Started  
**Priority**: 🔴 Critical  
**Story Points**: 5  
**Created**: 2026-03-01  
**Updated**: 2026-03-01  
**Assigned Sprint**: Backlog

## Description

The scheduler service is non-functional, causing the application to be consistently down. The Fly.io machine is not being started/stopped on schedule, and/or the application process is not running when it should be.

## Steps to Reproduce

1. Observe the Fly.io application status during expected uptime hours (6am–10pm).
2. Attempt to interact with the Telegram bot.
3. Bot is unresponsive — application is down.

**Precondition**: Fly.io scheduled scaling is configured via `.github/workflows/fly-schedule-scale.yml` and/or Fly.io machine settings.

## Expected Behavior

- The Fly.io machine starts automatically at the configured schedule (6am).
- The application is available and the Telegram bot responds to messages during uptime hours.
- The machine scales to zero at night (10pm) to save costs.
- On first request outside schedule, the machine wakes up.

## Actual Behavior

- The scheduler does not start/wake the Fly.io machine.
- The application remains down and the Telegram bot is unresponsive.
- Users cannot interact with the bot at any time.

## Environment

- **Server Environment**: Production (Fly.io)
- **Deployment**: Fly.io with scheduled scaling
- **Scheduler**: GitHub Actions cron workflow (`.github/workflows/fly-schedule-scale.yml`)
- **Region**: See `fly.toml`

## Screenshots/Logs

[TODO: Capture logs from Fly.io and GitHub Actions scheduler runs]

```
# Check Fly.io machine status
fly status

# Check Fly.io logs
fly logs

# Check GitHub Actions scheduler workflow runs
```

## Technical Details

- The scheduling mechanism uses a GitHub Actions workflow (`.github/workflows/fly-schedule-scale.yml`) with cron triggers to scale the Fly.io machine up and down.
- See `docs/fly-scheduled-scaling.md` for the intended architecture.
- Possible failure points:
  1. GitHub Actions cron job not triggering
  2. Fly.io API token expired or misconfigured in GitHub Secrets
  3. `fly machine start`/`fly machine stop` commands failing
  4. Fly.io machine ID changed or machine was destroyed/recreated
  5. Fly.io auto-stop configuration conflicting with scheduled scaling

## Root Cause

[TODO: Investigate scheduler logs to determine root cause]

Potential causes:
- GitHub Actions cron schedule syntax error
- `FLY_API_TOKEN` secret expired or not set in GitHub repository
- Fly.io machine ID mismatch (machine was recreated with a new ID)
- Fly.io app configuration issue (`fly.toml` auto_stop/auto_start settings)
- GitHub Actions workflow permissions issue
- Fly.io account/billing issue preventing machine start

## Solution

[TODO: Implement fix after root cause is identified]

Investigation steps:
1. Check GitHub Actions → Actions tab → `fly-schedule-scale` workflow history
2. Verify `FLY_API_TOKEN` is set and valid: `fly auth token`
3. Verify machine ID: `fly machines list`
4. Check `fly.toml` auto_stop/auto_start configuration
5. Manually run the workflow to see if it works on demand
6. Check Fly.io dashboard for machine status and billing

## Reference Documents

- [Fly.io scheduled scaling](../../../docs/fly-scheduled-scaling.md) — Architecture and configuration
- `.github/workflows/fly-schedule-scale.yml` — The scheduler workflow
- `fly.toml` — Fly.io application configuration

## Technical References

- File: `.github/workflows/fly-schedule-scale.yml`
- File: `fly.toml`
- File: `docs/fly-scheduled-scaling.md`
- Dashboard: Fly.io app dashboard
- Dashboard: GitHub Actions → workflow runs

## Testing

- [ ] GitHub Actions cron workflow triggers on schedule
- [ ] `fly machine start` succeeds when run manually
- [ ] `fly machine stop` succeeds when run manually
- [ ] Application is accessible after machine start
- [ ] Telegram bot responds after machine start
- [ ] Machine auto-stops at scheduled time
- [ ] Machine wakes on first request (if auto_start is configured)

## Notes

- This bug, combined with BF-002 (build failure), means the application is currently unavailable and cannot be redeployed through the normal pipeline.
- **Impact**: Application is completely down for all users.
- Workaround: manually start the Fly.io machine via `fly machine start <machine_id>` or `fly apps restart`.
- If the machine was destroyed, a fresh deploy (`fly deploy`) may be needed.

## History

- 2026-03-01 - Created
