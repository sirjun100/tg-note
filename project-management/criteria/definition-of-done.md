# Definition of Done

**Purpose**: Quality gate for completed work. All items must satisfy these criteria before being marked ✅ Completed.

**Related**: [US-036 Documentation-Code Consistency Review](../backlog/user-stories/US-036-documentation-code-consistency-review.md)

---

## Per-Item Criteria

### Feature Requests & Bug Fixes

- [ ] Acceptance criteria met
- [ ] Code changes implemented and tested
- [ ] Unit tests added/updated (where applicable)
- [ ] Documentation updated (README, docs/, feature spec)
- [ ] No new linter errors introduced
- [ ] Backlog item status updated to ✅ Completed
- [ ] RELEASE_NOTES.md updated (see [release-notes-process.md](../processes/release-notes-process.md))

### Sprint Completion

- [ ] All sprint stories completed or moved to backlog
- [ ] Sprint review notes filled in
- [ ] Sprint retrospective completed
- [ ] Product backlog updated
- [ ] **Documentation-Code Consistency Review** run this sprint (or since last sprint); no unresolved high-priority contradictions

---

## Documentation-Code Consistency Review

**When**: Before sprint planning (required) and on-demand (e.g. before major release).

**How**:
```bash
./scripts/doc-code-review.sh
# Or: python scripts/doc_code_review.py --trigger "Pre-sprint planning"
```

**Output**: `project-management/reports/doc-code-consistency-latest.md`

**Human review**: For each flagged item, decide: fix docs, fix code, or mark False Positive. Resolve high-priority items before sprint planning proceeds.

---

## References

- [Backlog Management Process](../processes/backlog-management-process.md) — Sprint Planning Checklist
- [Sprint Planning Template](../docs/templates/sprint-planning-template.md) — Checklist
- [Release Notes Process](../processes/release-notes-process.md)
