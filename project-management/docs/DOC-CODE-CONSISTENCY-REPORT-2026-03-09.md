# Documentation-Code Consistency Report - 2026-03-09

**Scope**: Recent code changes (recipe folder, recipe image, DEF-025 screenshot-skipped)

## Out of Date

| File | What is outdated | Suggested |
|------|------------------|-----------|
| README.md | "Resources/Recipes" | Update to "Resources/🍽️ Recipe" to match code |
| docs/para-where-to-put.md | Generic "Resources → Recipes" | Add note: bot uses Resources/🍽️ Recipe (Ressources fallback for French) |
| project-management/backlog/defects/DEF-007 | Line refs "850-877" in core.py | Update to "handlers/core.py (create_note_in_joplin)" — line numbers change |
| docs/api-reference.md | Recipe image flow | Add: returns (data_url, error_reason) on failure for user feedback |

## Contradictions

- None identified. Code is source of truth.

## Illogical Statements

- None identified.

## Updates Applied

- [x] README.md — Recipe folder path (Resources/🍽️ Recipe)
- [x] docs/para-where-to-put.md — Recipe folder note
- [x] docs/for-users/gtd-second-brain-workflow.md — Recipe folder path
- [x] DEF-007 — Line references; added DEF-025 cross-ref
- [x] docs/api-reference.md — Recipe image return type and failure handling
