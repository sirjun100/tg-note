# Reference Documentation

This directory contains reference materials for backlog management.

## Contents

### Templates (`templates/`)

Template files for creating backlog items:

- **feature-request-template.md** - For new features and enhancements
- **bug-fix-template.md** - For bug reports and fixes
- **sprint-planning-template.md** - For sprint planning
- **product-backlog-table-template.md** - For the main backlog table

**Usage:**
1. Copy the appropriate template
2. Fill in all sections
3. Save to the appropriate directory (`backlog/features/` or `backlog/bugs/`)
4. Add entry to `backlog/product-backlog.md`

### Processes (`processes/`)

Process documentation explaining workflows:

- **backlog-management-process.md** - How to manage the backlog
- **product-backlog-structure.md** - Backlog structure and conventions

**Usage:**
- Reference when learning the process
- Review during backlog refinement
- Share with new team members

## Quick Reference

### Creating a Feature Request

```bash
cp docs/templates/feature-request-template.md backlog/features/FR-001-feature-name.md
# Edit FR-001-feature-name.md
# Add entry to backlog/product-backlog.md
```

### Creating a Bug Fix

```bash
cp docs/templates/bug-fix-template.md backlog/bugs/BF-001-bug-description.md
# Edit BF-001-bug-description.md
# Add entry to backlog/product-backlog.md
```

### Planning a Sprint

```bash
cp docs/templates/sprint-planning-template.md sprints/sprint-01-sprint-name.md
# Edit sprint-01-sprint-name.md
# Add user stories from backlog
```

## File Naming Conventions

- **Features**: `FR-XXX-feature-name.md` (e.g., `FR-042-user-authentication.md`)
- **Bugs**: `BF-XXX-bug-description.md` (e.g., `BF-015-email-validation.md`)
- **Sprints**: `sprint-XX-sprint-name.md` (e.g., `sprint-05-user-auth.md`)

Use kebab-case (lowercase with hyphens) for names.

## Best Practices

1. **Always use templates** - Don't create files from scratch
2. **Fill all sections** - Complete templates ensure consistency
3. **Update regularly** - Keep status and dates current
4. **Link properly** - Use correct relative paths in links
5. **Follow naming** - Use consistent ID formats and naming

---

For more help, see the main backlog toolkit documentation.
