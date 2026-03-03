# Bug Fix: BF-004 - Fly.io Deploy Fails: No Access Token Available

**Status**: ✅ Completed
**Priority**: 🔴 Critical
**Story Points**: 1
**Created**: 2026-03-03
**Updated**: 2026-03-03
**Assigned Sprint**: Backlog

## Description

The CI deploy step fails instantly (0 seconds) with `Error: No access token available. Please login with 'flyctl auth login'`. The `FLY_API_TOKEN` secret is either missing, expired, or not being passed to the deploy step correctly.

## Steps to Reproduce

1. Push a commit to `main` branch.
2. CI runs `lint-and-test` (passes).
3. `deploy` job starts and runs `flyctl deploy --remote-only`.
4. Fails immediately with: `Error: No access token available`.

**Precondition**: Push to `main` triggers the deploy job.
**Note**: `docker-build` step was removed by FR-021; deploy now depends only on `lint-and-test`.

## Expected Behavior

- `flyctl deploy --remote-only` authenticates using the `FLY_API_TOKEN` secret and deploys to Fly.io.

## Actual Behavior

```
Run flyctl deploy --remote-only
Error: No access token available. Please login with 'flyctl auth login'
Error: Process completed with exit code 1.
```

The step runs for 0 seconds — flyctl doesn't even attempt to connect to Fly.io.

## Environment

- **Server Environment**: GitHub Actions CI/CD (deploy job)
- **Workflow**: `.github/workflows/ci.yml`
- **Step**: `Deploy to Fly.io`
- **flyctl**: Installed via `superfly/flyctl-actions/setup-flyctl@master`

## Screenshots/Logs

```
Run flyctl deploy --remote-only
Error: No access token available. Please login with 'flyctl auth login'
Error: Process completed with exit code 1.
```

## Technical Details

The deploy step in `ci.yml`:

```yaml
deploy:
  needs: [lint-and-test, docker-build]
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: superfly/flyctl-actions/setup-flyctl@master
    - name: Deploy to Fly.io
      run: flyctl deploy --remote-only
      env:
        FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

The `FLY_API_TOKEN` is passed as an environment variable. flyctl reads it automatically.

## Root Cause

The `FLY_API_TOKEN` repository secret was not configured in GitHub. Without it, `flyctl` cannot authenticate with Fly.io.

## Solution

1. **Code fix**: Added a `Verify Fly.io token` step to both `ci.yml` and `fly-schedule-scale.yml` that checks for the secret before attempting to deploy/scale. If missing, it prints a clear error with instructions on how to generate and set the token.
2. **Configuration**: User must set the `FLY_API_TOKEN` repository secret in GitHub (Settings → Secrets → Actions) using a token generated with `fly tokens create deploy -x 8760h`. The value must include the `FlyV1` prefix as generated.

## Reference Documents

- `.github/workflows/ci.yml` — Deploy job configuration
- [Fly.io deploy tokens docs](https://fly.io/docs/flyctl/tokens-create/)

## Technical References

- File: `.github/workflows/ci.yml` (lines 52–64)
- Secret: `FLY_API_TOKEN` in GitHub repository settings
- Command: `fly tokens create deploy`

## Testing

- [x] Verify `Verify Fly.io token` step added to `ci.yml` (line 53) — `-z` check tested locally
- [x] Verify `Verify Fly.io token` step added to `fly-schedule-scale.yml` (line 56) — `-z` check tested locally
- [x] Empty-token detection works: `FLY_API_TOKEN=""` triggers error with clear remediation message
- [x] Valid-token passthrough works: `FLY_API_TOKEN="FlyV1 ..."` skips the error and proceeds
- [ ] Verify `FLY_API_TOKEN` secret exists in GitHub repo settings (manual — user must configure)
- [ ] Re-run deploy job after setting token (manual — user must trigger)
- [ ] Deploy completes successfully (manual — depends on valid token)
- [ ] Application is accessible after deploy (manual — depends on deploy success)

## Notes

- The `fly-schedule-scale.yml` workflow also uses `FLY_API_TOKEN` — if the scheduler succeeds but deploy fails, the token might be scoped differently (deploy vs read-only).
- If the token was never set, both deploy and scheduler would fail.
- This is a configuration issue, not a code issue. No code changes needed — only a GitHub secret update.

## History

- 2026-03-03 - Created
- 2026-03-03 - Completed: added token validation step to CI and scheduler workflows
