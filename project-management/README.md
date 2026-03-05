# Project Management

This directory contains the backlog management structure for this project.

## Structure

```
project-management/
├── backlog/              # Active backlog items
│   ├── product-backlog.md    # Main backlog overview
│   ├── features/            # Feature requests (FR-XXX-*.md)
│   └── bugs/                # Bug fixes (BF-XXX-*.md)
├── sprints/             # Sprint planning documents
│   └── sprint-XX-*.md
└── docs/                # Reference documentation
    ├── templates/       # Template files
    └── processes/       # Process documentation
```

## Strict Structure Rules

- All FR files and FR implementation summaries stay under `backlog/features/`.
- All sprint planning and sprint follow-up documents stay under `sprints/`.
- `docs/` at repository root is reserved for product/user/developer guides, not planning artifacts.

## Quick Start

1. **View the backlog**: Open `backlog/product-backlog.md`
2. **Create a feature**: Copy `docs/templates/feature-request-template.md` to `backlog/features/FR-XXX-name.md`
3. **Create a bug fix**: Copy `docs/templates/bug-fix-template.md` to `backlog/bugs/BF-XXX-name.md`
4. **Plan a sprint**: Copy `docs/templates/sprint-planning-template.md` to `sprints/sprint-XX-name.md`

## Workflow

### Before Commit and Push
- **Run lint and tests** before every commit/push to avoid CI failures. See [Pre-Commit Checklist](docs/processes/pre-commit-checklist.md).

### Daily Work
- Update status in `backlog/product-backlog.md`
- Work on items in `backlog/features/` or `backlog/bugs/`

### Creating New Items
- Use templates from `docs/templates/`
- Add entry to `backlog/product-backlog.md`
- Follow naming: `FR-XXX-feature-name.md` or `BF-XXX-bug-name.md`

### Sprint Planning
- Create sprint document in `sprints/`
- Reference backlog items
- Update backlog with sprint assignments

## Reference Materials

- **Templates**: See `docs/templates/` for creating new items
- **Processes**: See `docs/processes/` for workflow guidance
- **Documentation**: See `docs/README.md` for detailed reference guide

## Status Values

- ⭕ **Not Started**: Item not yet started
- ⏳ **In Progress**: Item currently being worked on
- ✅ **Completed**: Item finished and verified

## Priority Levels

- 🔴 **Critical**: Must be fixed/implemented immediately
- 🟠 **High**: Should be addressed soon
- 🟡 **Medium**: Nice to have, can wait
- 🟢 **Low**: Future consideration

---

For more information, see the backlog toolkit documentation.
