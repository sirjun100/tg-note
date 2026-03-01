# Fly.io scheduled scaling (6am–10pm up, 10pm–6am down)

You can keep the app **always running during the day** (e.g. 6am–10pm) and **scaled to zero at night** (10pm–6am), while still allowing it to **wake on the first request** outside that window.

## Behavior

| Time (example: your local 6am–10pm) | Fly machines | Cost |
|-------------------------------------|--------------|------|
| 6am–10pm                            | 1 running    | ~\$3–4/month (16 h/day) |
| 10pm–6am                            | 0 (scale to zero) | No compute |
| First request at 2am                | Machine starts, handles request, then can stop again | Pay only for that run |

Your `fly.toml` already has `auto_start_machines = true` and `min_machines_running = 0`. When the scheduler sets the app to **0 machines**, the Fly proxy still starts a machine on the first HTTP request (e.g. Telegram webhook), so the bot works 24/7 from the user’s perspective; you just pay for less compute.

## Setup

1. **Create a Fly API token** (with deploy permission):
   ```bash
   fly tokens create deploy
   ```
   Copy the token.

2. **Add it as a GitHub secret**:
   - Repo → Settings → Secrets and variables → Actions → New repository secret
   - Name: `FLY_API_TOKEN`
   - Value: the token from step 1

3. **Timezone:** The workflow is set for **Montreal (Eastern Time)**:
   - **11:00 UTC** → scale to 1 machine (6am Eastern)
   - **03:00 UTC** → scale to 0 machines (10pm Eastern)  
   To use another timezone, edit `SCALE_UP_UTC_HOUR` and `SCALE_DOWN_UTC_HOUR` in the workflow and the cron schedule.

## Manual scale

In GitHub: Actions → “Fly schedule scale” → Run workflow → choose scale **0** or **1**.

## Approximate cost

- ~16 hours/day with 1 machine (shared-cpu-1x, 1 GB) ≈ **\$3–4/month**.
- Plus volume and any extra run time when the app wakes at night.
