# Defect: DEF-036 - Task duplicate detection too strict — misses obvious duplicates

[← Back to Product Backlog](../product-backlog.md)

**Status**: ✅ Done
**Priority**: 🟠 High
**Story Points**: 3
**Created**: 2026-03-31
**Updated**: 2026-03-31
**Assigned Sprint**: Backlog

## Description

US-055 duplicate detection fails to catch semantically similar tasks. When user types `/task fill out sponsor form`, the bot creates a new task instead of detecting existing tasks like "I will try to fill out the sponsorship for my daughter".

Root causes:
1. Semantic embedding threshold was 0.90 — too strict for related but differently-worded tasks
2. Fallback was exact normalized string match only — no fuzzy matching layer between exact match and full embeddings

## Steps to Reproduce

1. Have existing task "I will try to fill out the sponsorship for my daughter"
2. Send `/task fill out sponsor form`
3. Bot creates duplicate task instead of showing edit/cancel options

## Expected Behavior

Bot detects "fill out sponsor form" as similar to existing sponsorship tasks and offers Edit/Priority/Cancel options.

## Actual Behavior

Bot creates a new duplicate task without any duplicate warning.

## Root Cause

- Semantic threshold at 0.90 cosine similarity was too high for catching related tasks
- When embeddings fail/unavailable, only exact normalized string match was used (useless for semantic similarity)
- No intermediate fuzzy matching layer

## Solution

Implemented 3-layer duplicate detection in `src/task_service.py`:

1. **Layer 1 — Semantic embeddings** (Gemini): Lowered threshold from 0.90 to 0.65
2. **Layer 2 — Fuzzy token/sequence matching**: New `_fuzzy_match_score()` combining SequenceMatcher ratio + token overlap with partial stem matching (threshold 0.50)
3. **Layer 3 — Exact normalized match**: Existing fallback for identical titles with different punctuation

Token matching uses stop word removal (English + French) and partial stem matching (e.g., "sponsor" matches "sponsorship").

## Technical References

- `src/task_service.py` — `detect_duplicate_task()`, `_fuzzy_match_score()`, `_extract_significant_tokens()`
- `src/note_index.py` — `find_most_similar_title()` threshold lowered
- `tests/test_task_duplicate.py` — 7 new test cases for fuzzy matching

## Testing

- [x] Unit test: fuzzy catches sponsorship duplicate (exact user scenario)
- [x] Unit test: no false positives on unrelated tasks
- [x] Unit test: identical titles score ~1.0
- [x] Unit test: similar sponsor tasks score >= 0.50
- [x] Unit test: partial stem matching works
- [x] Unit test: unrelated tasks rejected
- [x] All 407 existing tests pass

## Acceptance Verification

- [x] Actual Behavior now matches Expected Behavior
- [x] Steps to Reproduce no longer produce the defect
- [x] Fuzzy matching catches "fill out sponsor form" ≈ "I will try to fill out the sponsorship for my daughter" (score 0.667)

## History

- 2026-03-31 - Created and fixed
