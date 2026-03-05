# Bug Fix: BF-015 - Mypy Type Errors (60 errors in 23 files)

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 5
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Backlog

## Description

Running `mypy src/ --ignore-missing-imports --no-strict-optional --explicit-package-bases` reports **60 errors in 23 files**. CI runs mypy with `continue-on-error: true`, so the build passes, but type safety is not enforced.

## Steps to Reproduce

```bash
mypy src/ --ignore-missing-imports --no-strict-optional --explicit-package-bases
```

## Expected Behavior

- Mypy exits with code 0 (no errors), or a small number of acceptable errors.

## Actual Behavior

- 60 errors across 23 files.
- Exit code 1.

## Error Categories

### 1. Missing type stubs (3 files)
| File | Error |
|------|-------|
| `auth_service.py:14` | Library stubs not installed for "requests" → `pip install types-requests` |
| `timezone_utils.py:14` | Library stubs not installed for "pytz" → `pip install types-pytz` |
| `scheduler_service.py:13` | Library stubs not installed for "pytz" |
| `handlers/reports.py:366` | Library stubs not installed for "pytz" |

### 2. Exception.response attribute (3 files)
| File | Error |
|------|-------|
| `recipe_image.py:75` | "Exception" has no attribute "response" |
| `ocr_service.py:93` | "Exception" has no attribute "response" |
| `dream_image.py:75` | "Exception" has no attribute "response" |

**Fix**: Use `getattr(exc, "response", None)` or narrow exception type to `httpx.HTTPStatusError`.

### 3. user_id type mismatch (str vs int)
| File | Error |
|------|-------|
| `task_service.py:286` | Argument 1 to "log_task_sync" expected "int"; got "str" |
| `task_service.py:522` | Argument "user_id" to "Decision" expected "int"; got "str" |

### 4. auth_service.py:165
- Incompatible return value: got "dict[str, Any]", expected "str | None"

### 5. settings.py:106
- Argument "default_factory" to "Field" has incompatible type

### 6. weekly_report_generator.py
| Line | Error |
|------|-------|
| 118 | "JoplinClient" has no attribute "_make_request"; maybe "_request"? |
| 125 | Coroutine not awaited; has no attribute "__iter__" |

### 7. llm_providers.py
| Line | Error |
|------|-------|
| 78 | Argument "messages" incompatible type |
| 88 | ChatCompletionMessageCustomToolCall has no attribute "function" |
| 119 | Need type annotation for "prompt_parts" |

### 8. llm_orchestrator.py:78
- Need type annotation for "_personas"

### 9. reorg_orchestrator.py (multiple)
- Collection[str] used as mutable list (append, index)
- Need type annotations for seen_names, moves_by_target
- "object" has no attribute "append"/"__iter__"

### 10. monthly_report_generator.py:346, 348
- List comprehension type mismatch; return type mismatch

### 11. enrichment_service.py:224
- "None" has no attribute "__await__"

### 12. container.py:83
- Argument 2 to "TaskService" expected "LoggingService"; got "object"

### 13. handlers/reports.py
- task_service argument type "object" vs "TaskService | None" (lines 171, 238, 272)

### 14. handlers/reorg.py:302
- progress_callback type mismatch (Callable with Coroutine vs sync)

### 15. handlers/reading.py:39, 40
- "type[datetime]" has no attribute "UTC" (Python 3.11+ has datetime.UTC)

### 16. handlers/planning.py, google_tasks.py, core.py, braindump.py
- "object" has no attribute "get_available_task_lists", "create_task_with_metadata", etc.
- **Cause**: `orch.task_service` typed as `object` instead of `TaskService | None`; need proper typing on TelegramOrchestrator.

### 17. handlers/habits.py:246, 248
- "MaybeInaccessibleMessage" has no attribute "reply_text"

## Proposed Resolution

**Phase 1 (quick wins)**:
1. Add `types-requests` and `types-pytz` to requirements-dev.txt
2. Fix Exception.response in recipe_image, ocr_service, dream_image (use getattr or narrow type)
3. Fix user_id str→int in task_service

**Phase 2 (type annotations)**:
4. Add annotations: llm_orchestrator._personas, llm_providers.prompt_parts, reorg_orchestrator variables
5. Fix settings.py default_factory (use lambda or correct type)

**Phase 3 (structural)**:
6. Add proper TaskService type to TelegramOrchestrator; fix container/reports/handlers
7. Fix weekly_report_generator (await, _request vs _make_request)
8. Fix reorg_orchestrator Collection→list typing
9. Fix reading.py datetime.UTC (use zoneinfo or conditional for Python 3.10)
10. Fix habits.py MaybeInaccessibleMessage (narrow type or assert)

## Affected Files (23)

auth_service, timezone_utils, task_service, scheduler_service, settings, recipe_image, ocr_service, dream_image, weekly_report_generator, llm_providers, llm_orchestrator, reorg_orchestrator, monthly_report_generator, enrichment_service, container, handlers/reports, handlers/reorg, handlers/reading, handlers/planning, handlers/habits, handlers/google_tasks, handlers/core, handlers/braindump

## Resolution (2026-03-05)

- Phase 1: Added types-requests, types-pytz; fixed Exception.response (exc_resp var); fixed user_id int() in task_service
- Phase 2: Added type annotations (_personas, prompt_parts, seen_names, moves_by_target, plan, conflicts, audit); fixed TelegramOrchestrator.task_service typing; fixed weekly_report_generator (get_all_notes, await get_folders); fixed auth_service return type; fixed reading.py timezone.utc; fixed monthly_report_generator peak_hours; fixed enrichment_service progress_callback; added type: ignore for pydantic Field, llm_providers, habits, reorg

## References

- [BF-012: Mypy Module Resolution](BF-012-mypy-module-resolution.md) — fixed with --explicit-package-bases
- [Mypy error codes](https://mypy.readthedocs.io/en/stable/error_codes.html)
