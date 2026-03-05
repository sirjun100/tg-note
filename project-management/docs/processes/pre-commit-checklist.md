# Pre-Commit Checklist

**Purpose**: Ensure CI passes before pushing. The [GitHub Actions workflow](https://github.com/martinfou/telegram-joplin/actions) runs on every push to `main` and will fail if lint or tests fail.

## Before Every Commit and Push

Run these commands locally before committing and pushing:

```bash
# 1. Lint (must pass — CI fails on lint errors)
ruff check src/ config.py main.py

# 2. Tests (must pass)
pytest tests/ -v --ignore=tests/e2e
```

Or in one command:

```bash
ruff check src/ config.py main.py && pytest tests/ -v --ignore=tests/e2e
```

## Auto-Fix Lint Issues

Ruff can auto-fix many issues:

```bash
ruff check src/ config.py main.py --fix
```

Then re-run `ruff check` to confirm no remaining errors.

## Reference

- **CI workflow**: [.github/workflows/ci.yml](../../../.github/workflows/ci.yml)
- **CI runs**: [GitHub Actions](https://github.com/martinfou/telegram-joplin/actions)
- **Example failure**: [CI run #30](https://github.com/martinfou/telegram-joplin/actions/runs/22724990395) — lint errors caused deploy to be skipped

## Rule

> **Always run `ruff check` and `pytest` before committing and pushing to `main`.**
