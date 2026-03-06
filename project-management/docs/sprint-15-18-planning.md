# Sprint 15–18 Planning: Feature Order & Rationale

**Date**: 2026-03-06  
**Status**: Ready for Review  
**Historical Velocity**: ~14 pts/sprint (2 weeks)  
**Definition of Done**: [definition-of-done.md](definition-of-done.md)

---

## Executive Summary

This document proposes sprint ordering for Sprints 15–18 based on:
1. **Stability first** — Fix production bugs before new features
2. **Dependency order** — Features that enable others come first
3. **Quick wins** — Small, high-impact items paired with larger work
4. **Cohesive themes** — Group related work for focus

---

## Bug Fixes (Sprint 14 & 15)

| Sprint | Bug | Description | Pts |
|--------|-----|-------------|-----|
| **Sprint 14** | BF-017 | /dream command crashes on invocation — fix parse_mode, welcome message | 1 |
| **Sprint 15** | BF-022 | /find command error in Fly.io — get_folders try/except, HTML escape | 2 |
| **Sprint 15** | BF-023 | /ask command crashes on certain prompts — HTML escape, plain-text fallback | 2 |

**Total bug fix points**: 5 pts across Sprints 14–15. All three share the same root cause (Telegram Markdown parse errors); fix pattern: HTML mode + `html.escape()` + plain-text fallback.

---

## Current State

| Sprint | Status | Contents | Points |
|--------|--------|----------|--------|
| **Sprint 13** | ⏳ In Progress | BF-007, FR-036 | 13 |
| **Sprint 14** | ⏳ Planned | BF-017 (bug), FR-033 | 9 |
| **Sprint 15** | 📋 Planned | BF-022 (bug), BF-023 (bug), FR-044, FR-039 | 12 |

**Remaining unassigned bugs**: None (all high-priority bugs assigned to Sprint 14–15)

**Unassigned Features** (by proposed order):

| Order | ID | Title | Pts | Rationale |
|-------|-----|-------|-----|------------|
| 1 | FR-044 | /project_new command | 5 | **Enables FR-034** — Users need to create projects before syncing them |
| 2 | FR-034 | Joplin ↔ Google Tasks project sync | 13 | High value; depends on project creation flow |
| 3 | FR-039 | Star on task as high priority | 3 | Quick win; improves all reports |
| 4 | FR-043 | Report speed + async + UI updates | 5 | Improves daily/weekly/monthly report UX |
| 5 | FR-042 | Stoic "What I Learned Today" | 4 | Builds on FR-019; content pipeline |
| 6 | FR-040 | Check existing task/note, update/append | 8 | Reduces duplicates; uses FR-026 semantic search |
| 7 | FR-038 | AI Identity, User Profile, Chat History | 8 | Personalization; standalone |
| 8 | FR-041 | Project mgmt: Commit style + Doc sync | 5 | Process/documentation; can slot in anytime |
| 9 | FR-035 | World-class brain dump | 13 | Large enhancement; no blocking deps |

---

## Proposed Sprint Plan

### Sprint 14: Flashcard & Dream Fix (context)
**Duration**: 2026-05-05 – 2026-05-18  
**Bug Fix**: BF-017 (1 pt) — /dream command crash  
**Feature**: FR-033 (8 pts) — Flashcard practice from notes  
**Plan**: [sprint-14-flashcard-and-dream-fix.md](../sprints/sprint-14-flashcard-and-dream-fix.md)  
**Success Criteria**: /dream shows welcome without crash; /flashcard with SM-2, card extraction, session flow.

---

### Sprint 15: Stability & Project Foundation
**Duration**: 2026-05-19 – 2026-06-01 (2 weeks)  
**Target**: 12 pts  
**Plan**: [sprint-15-stability-and-project-foundation.md](../sprints/sprint-15-stability-and-project-foundation.md)  
**Implementation Guide**: [sprint-15-implementation-guide.md](../sprints/sprint-15-implementation-guide.md) — LLM-ready code snippets, file paths, patterns

**Bug Fixes** (4 pts):
| Item | Points | Rationale |
|------|--------|-----------|
| BF-022 | 2 | /find fix — in progress; complete for production stability |
| BF-023 | 2 | /ask fix — same Markdown parse pattern as BF-022, BF-017 |

**Features** (8 pts):
| Item | Points | Rationale |
|------|--------|-----------|
| FR-044 | 5 | /project_new — creates projects with default folders; prerequisite for FR-034 |
| FR-039 | 3 | Star on task — quick win; improves reports immediately |

**Total**: 12 pts (4 bug fix + 8 feature)

**Theme**: Fix broken commands first, then establish project creation flow.

**Success Criteria**: All 4 stories done; /find and /ask work in production; /project_new creates projects; star priority in reports. See [Definition of Done](definition-of-done.md).

**Scope Reduction** (if needed): Drop FR-039 → 9 pts; or drop FR-044 → 7 pts (bugs + FR-039 only).

---

### Sprint 16: Project Sync
**Duration**: 2026-06-02 – 2026-06-15 (2 weeks)  
**Target**: 13 pts

| Item | Points | Rationale |
|------|--------|-----------|
| FR-034 | 13 | Joplin Projects ↔ Google Tasks sync — project = parent task, notes → subtasks |

**Total**: 13 pts

**Theme**: Unify Joplin project structure with Google Tasks. FR-044 (project creation) done in Sprint 15.

**Success Criteria**: Project folders map to parent tasks; action items from project notes become subtasks; stalled projects flagged in reports.

**Scope Reduction**: FR-034 is a single 13-pt feature; consider splitting into Phase 1 (basic sync) + Phase 2 (rename/delete, stalled detection) if needed.

---

### Sprint 17: Reports & Stoic
**Duration**: 2026-06-16 – 2026-06-29 (2 weeks)  
**Target**: 9 pts

| Item | Points | Rationale |
|------|--------|-----------|
| FR-043 | 5 | Report speed + async + progress UI — improves perceived and actual performance |
| FR-042 | 4 | Stoic "What I Learned Today" — content pipeline for weekly creation |

**Total**: 9 pts

**Theme**: Report UX and Stoic journal enhancement. Under velocity; buffer for spillover or FR-016/FR-018.

**Success Criteria**: Reports generate faster (measurable); progress messages in chat; Stoic "What I Learned" + /learnings command.

**Scope Reduction**: Drop FR-042 → 5 pts (report speed only); or drop FR-043 → 4 pts (Stoic only).

---

### Sprint 18: Duplicate Check & Process
**Duration**: 2026-06-30 – 2026-07-13 (2 weeks)  
**Target**: 13 pts

| Item | Points | Rationale |
|------|--------|-----------|
| FR-040 | 8 | Check existing task/note, offer update/append — reduces duplicates across all flows |
| FR-041 | 5 | Commit style + Document sync — process docs; complements FR-036 |

**Total**: 13 pts

**Theme**: Data hygiene (duplicate detection) and project process maturity.

**Success Criteria**: Duplicate check before note/task creation; Update/Append/New flow; commit-style and document-sync process docs.

**Scope Reduction**: Drop FR-041 → 8 pts (duplicate check only); or drop FR-040 → 5 pts (process docs only).

---

### Sprint 19+: AI & Brain Dump
**Duration**: 2 weeks each  
**Target**: ~13 pts/sprint

| Sprint | Items | Points |
|--------|-------|--------|
| 19 | FR-038 (AI Identity, User Profile, Chat History) | 8 |
| 20 | FR-035 (World-class brain dump) | 13 |

---

## Dependency Graph

```
BF-022, BF-023 (bugs)     → Sprint 15 (stability)
        ↓
FR-044 (/project_new)     → Sprint 15 (enables FR-034)
        ↓
FR-034 (Project sync)     → Sprint 16
        ↓
FR-039 (Star)             → Sprint 15 (independent)
FR-043 (Report speed)     → Sprint 17 (independent)
FR-042 (Stoic learnings)  → Sprint 17 (FR-019 ✅)
FR-040 (Duplicate check)  → Sprint 18 (FR-026 ✅)
FR-038 (AI identity)     → Sprint 19 (independent)
FR-041 (Process docs)     → Sprint 18 (FR-036 ✅)
FR-035 (Brain dump)       → Sprint 20 (independent)
```

---

## Alternative: Bug-Only Sprint 15

If production stability is **critical** and features must wait, Sprint 15 could focus exclusively on bug fixes:

| Item | Points |
|------|--------|
| BF-022 | 2 |
| BF-023 | 2 |

**Total**: 4 pts. FR-044 and FR-039 would move to Sprint 16 (alongside FR-034, or Sprint 17). Use when /find and /ask are blocking users and must be fixed immediately with no feature work.

---

## Recommendation

1. **Sprint 15**: BF-022, BF-023, FR-044, FR-039 — stability + project foundation
2. **Sprint 16**: FR-034 — project sync (single large feature)
3. **Sprint 17**: FR-043, FR-042 — reports + Stoic
4. **Sprint 18**: FR-040, FR-041 — duplicate check + process docs

This order ensures:
- Broken commands are fixed before new features
- Project creation exists before project sync
- Quick wins (FR-039) ship early
- Report improvements and Stoic enhancement are grouped
- Duplicate detection improves data quality before AI personalization

---

## Quality Checklist (World-Class Sprint Planning)

- [x] **Clear sprint goals** — Each sprint has a measurable, outcome-focused goal
- [x] **Bug fixes prioritized** — Stability before features (Sprints 14–15)
- [x] **Dependency order** — FR-044 before FR-034; dependencies explicit
- [x] **Task breakdowns** — Sprint 15 has tasks per story (T-001–T-014)
- [x] **Definition of Done** — Referenced; success criteria per sprint
- [x] **Scope reduction options** — Fallback plans if velocity or capacity changes
- [x] **Dates** — Sprint 15–18 have explicit date ranges
- [x] **Pre-sprint checklist** — Doc-code review, backlog refinement

---

**Next Steps**:
1. Review and approve this plan
2. Run doc-code review before Sprint 15 kickoff
3. Create `sprint-16-project-sync.md` when Sprint 15 starts
4. Update `product-backlog.md` sprint assignments as work completes
