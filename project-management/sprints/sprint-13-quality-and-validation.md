# Sprint 13: Quality and Validation

**Sprint Goal**: Fix URL screenshot validation (DEF-007) and add Documentation-Code Consistency Review (US-036) to the project-management process.

**Duration**: 2026-04-21 - 2026-05-04 (2 weeks)
**Status**: ✅ Completed
**Team Velocity**: 13 points (DEF-007 + US-036)
**Sprint Planning Date**: 2026-03-06
**Sprint Review Date**: 2026-05-04
**Sprint Retrospective Date**: 2026-05-04

## Sprint Overview

**Focus Areas**:
- URL content validation (error pages, geo-blocking, domain mismatch)
- Documentation-code consistency automation and process integration

**Key Deliverables**:
- DEF-007: Error page detection, domain mismatch detection, user notification when screenshot skipped
- US-036: Doc-code review script (MVP), report format, Definition of Done, sprint planning checklist update

**Dependencies**:
- `src/url_enrichment.py` (existing)
- `project-management/docs/processes/` (existing)
- `docs/`, `README.md` (existing)

**Risks & Blockers**:
- US-036 MVP scope: Categories 1, 2, 3, 9 only — Phase 2 can follow in later sprint

---

## User Stories

### Story 1: URL Screenshot Content Validation - 5 Points

**User Story**: As a user who pastes URLs to create notes, I want the bot to detect error pages (geo-blocked, 404, paywall) and skip useless screenshots, so that my notes are not polluted with error page images.

**Acceptance Criteria**:
- [ ] Error pages (404, 403, 500, geo-blocked, paywall) are detected and screenshot skipped
- [ ] Domain mismatch (redirect to different domain) is detected and screenshot skipped
- [ ] User is notified when screenshot is skipped with a clear reason
- [ ] Valid pages still get screenshots
- [ ] Subdomain redirects (youtube.com → youtu.be) are allowed
- [ ] Unit tests for `_is_error_page` and `_check_domain_mismatch`

**Reference Documents**:
- [DEF-007: URL Screenshots No Content Validation](../backlog/defects/DEF-007-url-screenshot-no-content-validation.md)

**Technical References**:
- File: `src/url_enrichment.py` — `fetch_url_context`, `_is_error_page`, `_check_domain_mismatch`
- File: `src/handlers/core.py` — Screenshot integration, user notification

**Story Points**: 5

**Priority**: 🟠 High

**Status**: ✅ Completed (implementation + tests already in codebase)

**Backlog Reference**: [DEF-007](../backlog/defects/DEF-007-url-screenshot-no-content-validation.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Implement/verify `_is_error_page` (error indicators, multilingual) | `url_enrichment._is_error_page` | DEF-007 | ✅ | 2 | — |
| T-002 | Implement/verify `_check_domain_mismatch` (redirect validation) | `url_enrichment._check_domain_mismatch` | DEF-007 | ✅ | 1.5 | — |
| T-003 | Integrate validators into `fetch_url_context`, set skip_screenshot | `url_enrichment.fetch_url_context` | DEF-007 | ✅ | 1 | — |
| T-004 | Add user notification when screenshot skipped | `handlers/core.py` | DEF-007 | ✅ | 0.5 | — |
| T-005 | Add unit tests for error page and domain mismatch | `tests/test_url_enrichment_validation.py` | DEF-007 | ✅ | 0.5 | — |

**Total Task Points**: 5.5

---

### Story 2: Documentation-Code Consistency Review - 8 Points

**User Story**: As a team member responsible for project quality, I want a pre-sprint documentation-code consistency review that flags contradictions between docs and code, so that we catch mismatches before they cause confusion.

**Acceptance Criteria**:
- [ ] Script or tool scans docs and code for contradictions (Categories 1, 2, 3, 9)
- [ ] Report format: Markdown, stored in `project-management/reports/`
- [ ] Definition of Done created/updated with doc-code review requirement
- [ ] Sprint planning checklist includes "Doc-Code Consistency Review completed"
- [ ] On-demand: documented command to run review (e.g. `./scripts/doc-code-review.sh`)

**Reference Documents**:
- [US-036: Documentation-Code Consistency Review](../backlog/user-stories/US-036-documentation-code-consistency-review.md)
- [Documentation-Code Consistency Problems](../docs/processes/documentation-code-consistency-problems.md) (if exists; else use US-036 taxonomy)

**Technical References**:
- Directory: `docs/`, `project-management/`, `README.md`
- Directory: `src/`, `config.py`, `main.py`
- Script: `scripts/doc-code-review.sh` or `scripts/doc_code_review.py` (new)

**Story Points**: 8

**Priority**: 🟠 High

**Status**: ✅ Completed

**Backlog Reference**: [US-036](../backlog/user-stories/US-036-documentation-code-consistency-review.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-006 | Create doc-code review script (file/class references, option counts, command lists) | `scripts/doc_code_review.py` | US-036 MVP | ✅ | 3 | — |
| T-007 | Implement report generation (Markdown, categories 1–3, 9) | Report schema | US-036 | ✅ | 2 | — |
| T-008 | Create Definition of Done document | `project-management/docs/definition-of-done.md` | US-036 | ✅ | 1 | — |
| T-009 | Update backlog-management-process and sprint-planning-template | Process docs | US-036 | ✅ | 1 | — |
| T-010 | Add run script (shell wrapper) and document on-demand usage | `scripts/doc-code-review.sh` | US-036 | ✅ | 1 | — |

**Total Task Points**: 8

---

## Sprint Summary

**Total Story Points**: 13 (DEF-007: 5, US-036: 8)
**Total Task Points**: 13.5
**Estimated Velocity**: 13 points

**Sprint Burndown Plan**:
- Week 1: Story 1 (DEF-007) — 5 points; Story 2 start (T-006, T-007)
- Week 2: Story 2 (US-036) — 8 points; Story 1 verification

**Sprint Review Notes**:
- [To be filled at sprint review]
- [ ] [RELEASE_NOTES.md](../../../RELEASE_NOTES.md) updated (see [release-notes-process.md](../processes/release-notes-process.md))

**Sprint Retrospective Notes**:
- **What went well?**
  - [To be filled]
- **What could be improved?**
  - [To be filled]
- **Action items for next sprint**
  - [To be filled]

---

**Last Updated**: 2026-03-06
