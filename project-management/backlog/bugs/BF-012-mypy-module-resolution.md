# Bug Fix: BF-012 - Mypy Module Resolution Error

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 0.5
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Backlog

## Description

When running `mypy src/ --ignore-missing-imports --no-strict-optional`, mypy fails with:

```
src/handlers/braindump.py: error: Source file found twice under different module names: "handlers.braindump" and "src.handlers.braindump"
```

Mypy discovers the same file under two different module paths (with and without `src.` prefix), which prevents further type checking.

## Steps to Reproduce

1. Run: `mypy src/ --ignore-missing-imports --no-strict-optional`
2. Observe: Error about duplicate module names; exit code 2.

## Expected Behavior

- Mypy runs without the module resolution error.
- Type checking proceeds (other errors may still exist).

## Actual Behavior

- Mypy exits immediately with the duplicate-module error.
- No further type checking is performed.

## Root Cause

Mypy infers module names from file paths. When run from the project root with `src/` as the target, it can resolve `src/handlers/braindump.py` as both `handlers.braindump` (relative to some path) and `src.handlers.braindump` (with explicit package base). The `--explicit-package-bases` flag tells mypy to treat `src` as the package root, resolving the ambiguity.

## Resolution

Add `--explicit-package-bases` to the mypy command:

```bash
mypy src/ --ignore-missing-imports --no-strict-optional --explicit-package-bases
```

## References

- [Mypy: Mapping file paths to modules](https://mypy.readthedocs.io/en/stable/running_mypy.html#mapping-file-paths-to-modules)
- Common resolutions: a) adding `__init__.py` somewhere, b) using `--explicit-package-bases` or adjusting MYPYPATH

## Files Changed

- `.github/workflows/ci.yml`: Add `--explicit-package-bases` to the mypy step.
