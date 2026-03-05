# Pre-Commit Checklist

**Purpose**: Ensure CI passes before pushing. The [GitHub Actions workflow](https://github.com/martinfou/telegram-joplin/actions) runs on every push to `main` and will fail if lint or tests fail.

## ⚠️ Run Before Every Commit

> **Do not commit until lint and tests pass.** Run these checks *before* `git commit`, not after.

### Step 1: Lint (run first)

```bash
ruff check src/ config.py main.py
```

If using venv: `.venv/bin/ruff check src/ config.py main.py`

### Step 2: Tests

```bash
pytest tests/ -v --ignore=tests/e2e
```

### One-liner (lint then tests)

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

> **1. Run `ruff check` — fix any lint errors.**  
> **2. Run `pytest` — fix any failing tests.**  
> **3. Then commit.**  
> Do not skip step 1 or 2.
