# Feature Request: FR-021 - Remove Redundant Docker Build Step from CI

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 1
**Created**: 2026-03-03
**Updated**: 2026-03-03
**Assigned Sprint**: Backlog

## Description

Remove the `docker-build` job from `.github/workflows/ci.yml`. This job builds the Docker image locally in CI to validate the Dockerfile, but the `deploy` job already builds the image remotely via `flyctl deploy --remote-only` on Fly.io's builders. The CI Docker build doesn't push anywhere — it only validates the Dockerfile can build, which is redundant since the deploy step itself will fail if the Dockerfile is broken.

Removing it saves ~1–2 minutes of CI time per push and simplifies the pipeline.

## User Story

As a developer pushing to main,
I want the CI pipeline to be as fast as possible without redundant steps,
so that deploys happen quickly and CI minutes aren't wasted.

## Acceptance Criteria

- [x] `docker-build` job removed from `ci.yml`
- [x] `deploy` job's `needs` updated to depend only on `lint-and-test`
- [x] Deploy still works correctly on push to main (YAML valid, flyctl deploy unchanged)
- [x] CI pipeline is faster by ~1–2 minutes (docker-build job eliminated)

## Current State

```yaml
docker-build:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Build Docker image
      run: docker build -t telegram-joplin:ci .

deploy:
  needs: [lint-and-test, docker-build]    # docker-build is redundant here
```

## Proposed Change

```yaml
deploy:
  needs: [lint-and-test]                  # only depend on lint-and-test
```

Remove the entire `docker-build` job.

## Technical References

- File: `.github/workflows/ci.yml`

## Notes

- The `flyctl deploy --remote-only` command builds the Docker image on Fly.io's remote builders, making the CI Docker build purely a validation step.
- If the Dockerfile breaks, the deploy step will fail and report the error — no need for a separate gate.

## History

- 2026-03-03 - Created
- 2026-03-03 - Completed: removed docker-build job and updated deploy needs
