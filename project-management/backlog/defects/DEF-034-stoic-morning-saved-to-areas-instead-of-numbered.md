# Defect: DEF-034 - /stoic morning saved to Areas instead of 01 - Areas

[← Back to Product Backlog](../product-backlog.md)

**Status**: ⭕ Not Started
**Priority**: 🟠 High
**Story Points**: 2
**Created**: 2026-03-17
**Updated**: 2026-03-17
**Assigned Sprint**: -

---

## Problem Statement

When a user runs `/stoic morning`, the generated note can be created under a top-level notebook named `Areas` instead of the intended numbered notebook `01 - Areas` (PARA roots use numbered prefixes).

**User impact:** Stoic journal entries end up in an unexpected notebook, breaking organization and making entries harder to find.

---

## Steps to Reproduce

1. In Joplin, use numbered PARA roots like:
   - `01 - Areas`
   - `02 - Projects`
   - `03 - Resources`
   - `04 - Archives` (or `04 - Archive`)
2. Run `/stoic morning`
3. Complete the prompt and save with `/stoic_done`

---

## Expected Behavior

- Stoic notes are always saved under:
  - `01 - Areas / 📓 Journaling / Stoic Journal`

---

## Actual Behavior

- Stoic notes are saved under:
  - `Areas / 📓 Journaling / Stoic Journal`

---

## Root Cause

Multiple handlers hardcode non-numbered PARA root names (e.g. `["Areas", ...]`, `["Resources", ...]`) which can cause folder resolution to create a new root notebook when the numbered root exists.

---

## Fix

- Standardize all top-level PARA root references across the codebase to:
  - `01 - Areas`
  - `02 - Projects`
  - `03 - Resources`
  - `04 - Archives`
- Keep backward-compatible matching for `Archive` vs `Archives`.

---

## References

- Stoic handler: `src/handlers/stoic.py`
- Planning handler: `src/handlers/planning.py`
- Dream handler: `src/handlers/dream.py`
- Core handler helper paths: `src/handlers/core.py`

---

## History

- 2026-03-17 - Created
