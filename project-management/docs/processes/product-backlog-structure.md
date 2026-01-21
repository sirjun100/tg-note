# Product Backlog Structure

## Overview

This document defines the structure and templates for the product backlog, including feature requests and bug fixes. The backlog is managed using markdown files with structured templates.

## Backlog Organization

### Backlog File Structure

```
project-management/
├── backlog/
│   ├── product-backlog.md (main backlog file)
│   ├── features/
│   │   ├── FR-001-feature-name.md
│   │   ├── FR-002-feature-name.md
│   │   └── ...
│   └── bugs/
│       ├── BF-001-bug-description.md
│       ├── BF-002-bug-description.md
│       └── ...
└── sprints/
    └── sprint-XX-*.md
```

**Note**: Adjust file paths and ID format (FR-XXX, BF-XXX) to match your project structure.

## Product Backlog Table

### Main Backlog Table Format

See [../templates/product-backlog-table-template.md](../templates/product-backlog-table-template.md) for the complete table template.

The main backlog table tracks:
- Feature Requests (with status, priority, points, sprint assignment)
- Bug Fixes (with status, priority, points, sprint assignment)

### Status Values

- ⭕ **Not Started**: Item not yet started
- ⏳ **In Progress**: Item currently being worked on
- ✅ **Completed**: Item finished and verified

### Priority Levels

- 🔴 **Critical**: Blocks core functionality, must be fixed immediately
- 🟠 **High**: Important feature, should be addressed soon
- 🟡 **Medium**: Nice to have, can wait
- 🟢 **Low**: Future consideration, low priority

## Feature Request Template

### Feature Request Form

See [../templates/feature-request-template.md](../templates/feature-request-template.md) for the complete template.

**Key Sections**:
- Status, Priority, Story Points, Dates
- Description
- User Story (As a... I want... So that...)
- Acceptance Criteria
- Business Value
- Technical Requirements
- Reference Documents
- Technical References
- Dependencies
- Notes
- History

**ID Format**: FR-XXX (or your custom format)

**File Path**: `backlog/features/FR-XXX-feature-name.md`

## Bug Fix Template

### Bug Fix Form

See [../templates/bug-fix-template.md](../templates/bug-fix-template.md) for the complete template.

**Key Sections**:
- Status, Priority, Story Points, Dates
- Description
- Steps to Reproduce
- Expected Behavior
- Actual Behavior
- Environment
- Screenshots/Logs
- Technical Details
- Root Cause
- Solution
- Reference Documents
- Technical References
- Testing Checklist
- Notes
- History

**ID Format**: BF-XXX (or your custom format)

**File Path**: `backlog/bugs/BF-XXX-bug-description.md`

## Backlog Prioritization

### Prioritization Criteria

1. **Business Value**: How important is this to users?
2. **Technical Risk**: How risky is the implementation?
3. **Dependencies**: What other work depends on this?
4. **Effort**: How much work is required?
5. **Urgency**: How time-sensitive is this?

### Priority Matrix

| Priority | Business Value | Technical Risk | Urgency |
|----------|----------------|----------------|---------|
| 🔴 Critical | High | Low-Medium | Immediate |
| 🟠 High | High | Medium | Soon |
| 🟡 Medium | Medium | Low-Medium | Normal |
| 🟢 Low | Low | Low | Future |

## Backlog Refinement

### Refinement Process

1. **Review Backlog**: Review all backlog items
2. **Clarify Requirements**: Ensure items are well-defined
3. **Estimate Points**: Assign story points using Fibonacci
4. **Prioritize**: Order items by priority
5. **Break Down**: Split large items into smaller tasks
6. **Update Status**: Update status of items

### Refinement Checklist

- [ ] Item has clear description
- [ ] Acceptance criteria are defined
- [ ] Story points are estimated
- [ ] Priority is assigned
- [ ] Technical references are included
- [ ] Dependencies are identified
- [ ] Business value is documented

## Story Points Estimation

### Fibonacci Sequence

Use Fibonacci sequence for story point estimation:
- **1 Point**: Trivial task, < 1 hour
- **2 Points**: Simple task, 1-4 hours
- **3 Points**: Small task, 4-8 hours
- **5 Points**: Medium task, 1-2 days
- **8 Points**: Large task, 2-3 days
- **13 Points**: Very large task, 3-5 days (should be broken down)

### Estimation Factors

Consider:
- **Complexity**: How complex is the task?
- **Uncertainty**: How much is unknown?
- **Effort**: How much work is required?
- **Risk**: What are the risks?

## Template Usage

### Creating a New Feature Request

1. Copy the Feature Request Template from [../templates/feature-request-template.md](../templates/feature-request-template.md)
2. Assign unique ID: FR-XXX (use next available number)
3. Fill in all required fields
4. Save to: `backlog/features/FR-XXX-feature-name.md`
5. Add entry to `backlog/product-backlog.md` table

### Creating a New Bug Fix

1. Copy the Bug Fix Template from [../templates/bug-fix-template.md](../templates/bug-fix-template.md)
2. Assign unique ID: BF-XXX (use next available number)
3. Fill in all required fields, especially:
   - Steps to reproduce
   - Expected vs. actual behavior
   - Environment details
4. Save to: `backlog/bugs/BF-XXX-bug-description.md`
5. Add entry to `backlog/product-backlog.md` table

### Creating a New Sprint

1. Copy the Sprint Planning Template from [../templates/sprint-planning-template.md](../templates/sprint-planning-template.md)
2. Update sprint number: `sprint-XX-*.md`
3. Fill in sprint header (goal, duration, velocity, dates)
4. Add user stories from backlog
5. Break down into tasks
6. Save to: `sprints/sprint-XX-sprint-name.md`

## File Naming Conventions

### Feature Requests
- Format: `FR-XXX-feature-name.md`
- Example: `FR-001-user-authentication.md`
- Use kebab-case for feature names

### Bug Fixes
- Format: `BF-XXX-bug-description.md`
- Example: `BF-001-login-crash-on-special-chars.md`
- Use kebab-case for descriptions

### Sprints
- Format: `sprint-XX-sprint-name.md`
- Example: `sprint-01-foundation.md`
- Use zero-padding for numbers (01, 02, etc.)

## Best Practices

### Writing Good Backlog Items

1. **Clear Titles**: Descriptive, concise (50 characters or less)
2. **User Stories**: Follow "As a... I want... So that..." format
3. **Acceptance Criteria**: Specific, testable, measurable
4. **Technical References**: Link to code, docs, specs
5. **Business Value**: Explain why it matters

### Managing Backlog

1. **Keep It Updated**: Regular refinement and status updates
2. **Prioritize Regularly**: Review priorities frequently
3. **Break Down Large Items**: Keep items manageable (aim for < 8 points)
4. **Document Decisions**: Record why items are prioritized
5. **Communicate Changes**: Keep team informed of updates

## References

- **Feature Request Template**: [../templates/feature-request-template.md](../templates/feature-request-template.md)
- **Bug Fix Template**: [../templates/bug-fix-template.md](../templates/bug-fix-template.md)
- **Product Backlog Table Template**: [../templates/product-backlog-table-template.md](../templates/product-backlog-table-template.md)
- **Sprint Planning Template**: [../templates/sprint-planning-template.md](../templates/sprint-planning-template.md)
- **Backlog Management Process**: [backlog-management-process.md](backlog-management-process.md)

---

**Last Updated**: [Date]  
**Version**: 1.0  
**Status**: Product Backlog Structure Complete

