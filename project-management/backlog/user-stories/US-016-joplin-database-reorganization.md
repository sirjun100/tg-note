# User Story: US-016 - Joplin Database Reorganization, Tag Management, and Entry Enrichment

**Status**: ⏳ In Progress (~55% complete)
**Priority**: 🟠 High
**Story Points**: 21
**Created**: 2025-01-23
**Updated**: 2026-03-01
**Assigned Sprint**: Sprint 9

## Description

Implement a comprehensive system to reorganize the Joplin database with strategic folder hierarchies, intelligent tag management, and entry enrichment capabilities. This feature enables users to maintain a well-structured second brain using the PARA principles (Projects, Areas, Resources, Archive) while offering flexibility to choose the most suitable sub-folder organization for their workflow. Includes automated enrichment of entries with metadata, links, and contextual information.

## User Story

As a knowledge worker managing a complex Joplin database,
I want to reorganize my notes using a proven organizational system with flexible sub-structures,
and enrich them with consistent metadata and tagging,
so that my knowledge is organized, discoverable, and more valuable over time.

## Acceptance Criteria

### Core Features

- [x] User can select from ~~3~~ 2 pre-built organizational frameworks (status, roles — time-based not implemented)
- [x] System provides migration plan for existing notes to new structure (LLM-based, samples 20 notes)
- [ ] Folder reorganization process is reversible (undo capability) — **not implemented**, no `/reorganize-rollback`
- [ ] Tags are managed systematically (create, merge, deprecate) — **partial**: create + audit only, no merge/deprecate
- [ ] Tag hierarchy is enforced (parent tags, child tags) — **not implemented**
- [x] Entry enrichment adds metadata to notes (status, priority, summary, key takeaways, suggested tags)
- [x] Automated suggestions for tag assignment to existing notes (via enrichment)
- [x] Automated suggestions for folder placement (LLM-based PARA classification)
- [x] Bulk reorganization operations supported (batch enrichment, migration execution)
- [ ] Database maintains audit trail of all reorganization changes — **partial**: in-memory `OperationLog` only, not persisted
- [ ] Organization rules can be customized and saved — **not implemented**
- [ ] Visual representation of folder structure available — **basic stats only** via `/reorg_status`
- [x] Conflict detection when moving/merging notes (duplicate titles, invalid folders, tag conflicts)
- [ ] Performance optimized for large databases (1000+ notes) — **migration samples 20 notes**, no special optimization

## Business Value

Transforms Joplin from a note repository into a strategic knowledge management system. Well-organized knowledge is more valuable—easier to find, understand connections, and retrieve when needed. Reduces cognitive load of maintaining order. Enriched entries become more useful over time through better metadata and relationships. Enables better decision-making through organized information access.

## Technical Requirements

- Folder structure analysis and mapping
- Tag hierarchy management and conflict resolution
- Batch operation processing for large-scale reorganization
- Metadata injection and enrichment
- Relationship detection between notes (bidirectional linking)
- Database versioning for audit trail
- Markdown parsing for content analysis
- Integration with existing LLM for metadata suggestion
- Performance optimization for large databases
- Backup and rollback capabilities

## Reference Documents

- PARA Method: https://fortelabs.com/blog/para/
- Joplin REST API documentation
- Current logging system (US-010)

## Technical References

- `src/joplin_client.py` - Folder and note operations
- `src/logging_service.py` - Audit trail logging
- `src/llm_orchestrator.py` - Using LLM for suggestions
- Joplin REST API v2 for bulk operations

## Dependencies

- Joplin integration (US-005)
- LLM integration for suggestions (US-006)
- Logging system for audit trail (US-010)

## Implementation Notes

### Option 1: PARA+ (Status-Based Sub-Organization)

**Best for:** Users who want traditional PARA with clear separation by project/area status

```
Projects/
├── 🟢 Active
│   ├── Q1 2025 Product Roadmap
│   ├── Client Project A
│   └── Marketing Campaign
├── 🟡 Planned
│   ├── Q2 2025 Planning
│   └── Future Features
├── 🔵 On Hold
│   └── Archived Initiatives
└── ❌ Stalled
    └── Notes on why stalled

Areas/
├── 💼 Work & Career
├── 💪 Health & Fitness
├── 💰 Finance & Investing
├── 📚 Learning & Development
├── 👥 Relationships & Family
├── 🏠 Home & Personal
└── 🎯 Personal Growth

Resources/
├── 📖 Books & Articles
├── 🛠️ Tools & Software
├── 📋 Templates & Checklists
├── 🔗 Reference Materials
└── 🎓 Learning Materials

Archive/
├── Completed Projects (by year)
│   ├── 2024
│   ├── 2023
│   └── 2022
└── Historical Areas
```

**Ideal for:** Project-driven workflows, clear status tracking, visual clarity on project health

---

### Option 2: PARA with Context (Role & Domain-Based)

**Best for:** Users managing multiple roles, contexts, and domains

```
Projects/
├── By Role
│   ├── Work Projects
│   ├── Personal Projects
│   ├── Side Gig Projects
│   └── Volunteer Projects
└── By Priority
    ├── 🔴 Critical
    ├── 🟠 High
    ├── 🟡 Medium
    └── 🟢 Low

Areas/
├── By Role
│   ├── Professional
│   │   ├── Leadership
│   │   ├── Technical Skills
│   │   └── Team Management
│   ├── Personal
│   │   ├── Health & Fitness
│   │   ├── Finance
│   │   └── Relationships
│   └── Creative
│       ├── Writing
│       ├── Design
│       └── Music
└── By Timeframe
    ├── Daily Practices
    ├── Weekly Goals
    ├── Monthly Reviews
    └── Yearly Visions

Resources/
├── By Type
│   ├── Articles & Insights
│   ├── Tools & Services
│   ├── Templates & Systems
│   └── Guides & How-Tos
└── By Domain
    ├── Technical
    ├── Business
    ├── Personal Development
    └── Creative

Archive/
├── Completed Projects
├── Completed Areas
└── Deprecated Resources
```

**Ideal for:** Multi-role professionals, complex domain knowledge, context-switching workers

---

### Option 3: PARA with Time-Based Organization

**Best for:** Users planning by quarters/seasons, time-aware workflows

```
Projects/
├── 📅 This Quarter (Q1 2025)
│   ├── Critical
│   ├── Important
│   └── In Progress
├── 📅 Next Quarter (Q2 2025)
│   ├── Planned
│   └── Tentative
├── 📅 This Year (2025)
│   └── Planning
└── 📅 Future (2026+)
    └── Ideas & Concepts

Areas/
├── 🔥 Current Focus (Active)
│   ├── Primary Focus Area
│   ├── Secondary Focus Area
│   └── Supporting Areas
├── 📊 Ongoing Interests
│   ├── Evolving Areas
│   └── Regular Practices
└── ❄️ Dormant Areas
    └── Paused but Relevant

Resources/
├── 🎯 Active (Actively Used)
│   ├── Tools in Use
│   ├── Current Learning
│   └── Active References
├── 📚 Reference (Occasional Use)
│   ├── Reference Materials
│   ├── Historical Context
│   └── Archived Guides
└── 🗂️ Deprecated
    └── No Longer Relevant

Archive/
├── Completed Projects
│   ├── 2024
│   ├── 2023
│   └── Earlier
└── Historical Resources
```

**Ideal for:** Quarterly/seasonal planners, time-focused workflows, burn-out prevention through area rotation

---

### Tag Management System

#### Tag Strategy

```
Primary Tags (How to find)
├── #project-[name]        - Link to projects
├── #area-[name]           - Link to areas
├── #resource-[type]       - Link to resources
└── #status-[status]       - Current status

Contextual Tags (Context information)
├── #work / #personal / #creative
├── #urgent / #important / #routine
├── #active / #waiting / #someday
└── #focus / #reference / #archive

Meta Tags (Content information)
├── #summary-worthy       - Worth summarizing
├── #evergreen           - Timeless value
├── #time-sensitive      - Has expiration date
├── #review-needed       - Needs review
└── #needs-linking       - Link to other notes

Topic Tags (Subject matter)
├── #[topic]-101         - Basics/introduction
├── #[topic]-advanced    - Advanced content
├── #[topic]-tools       - Tools & implementations
└── #[topic]-reference   - Reference material
```

#### Tag Hierarchy

Parent-child tag relationships:
```
#work
├── #work/project-management
├── #work/technical
├── #work/leadership
└── #work/admin

#learning
├── #learning/reading
├── #learning/courses
├── #learning/practice
└── #learning/projects

#health
├── #health/fitness
├── #health/nutrition
├── #health/mental
└── #health/medical
```

---

### Entry Enrichment

#### Metadata to Add

Each note should be enriched with:

```markdown
---
Status: Active | Waiting | Someday | Done | Archived
Priority: Critical | High | Medium | Low
Created: 2025-01-23
Updated: 2025-01-23
Review Date: 2025-02-23
Source: [Where this note came from]
Related Notes: [Links to related notes]
---
```

#### Enrichment Categories

1. **Relationships**
   - Links to related notes
   - Bidirectional linking
   - Parent/child relationships

2. **Metadata**
   - Review dates for evergreen content
   - Source attribution
   - Expiration dates if time-sensitive
   - Time to read/complete

3. **Summaries**
   - One-line summary
   - Key takeaways (bullet points)
   - Action items
   - Decision history

4. **Accessibility**
   - Key phrases for searching
   - Alternative names/aliases
   - Synonyms in tags

---

### Migration Process

#### Phase 1: Analysis
- Scan all existing notes
- Analyze content and tags
- Map to recommended organizational structure
- Identify conflicts and duplicates

#### Phase 2: Planning
- Generate migration plan
- Identify manual decisions needed
- Calculate impact (which notes move, what tags change)
- Create rollback plan

#### Phase 3: Execution
- Create new folder structure
- Move notes with LLM suggestions for validation
- Apply new tag hierarchy
- Enrich notes with metadata

#### Phase 4: Verification
- Validate all notes in new locations
- Check tag consistency
- Verify no data loss
- Update note links if necessary

#### Phase 5: Cleanup
- Merge duplicate tags
- Remove deprecated folders (optional)
- Archive old structure (backup)
- Document new organization

---

### Database Schema

```sql
CREATE TABLE folder_structures (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  structure_name VARCHAR(100),
  structure_type VARCHAR(50),
  definition JSON,
  is_active BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);

CREATE TABLE tag_hierarchy (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  parent_tag VARCHAR(100),
  child_tag VARCHAR(100),
  hierarchy_level INTEGER,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);

CREATE TABLE note_metadata (
  id INTEGER PRIMARY KEY,
  joplin_note_id VARCHAR(100) NOT NULL,
  user_id INTEGER NOT NULL,
  status VARCHAR(50),
  priority VARCHAR(20),
  review_date DATE,
  source VARCHAR(255),
  summary TEXT,
  key_takeaways TEXT,
  time_to_read_minutes INTEGER,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);

CREATE TABLE note_relationships (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  source_note_id VARCHAR(100) NOT NULL,
  target_note_id VARCHAR(100) NOT NULL,
  relationship_type VARCHAR(50),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);

CREATE TABLE reorganization_history (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  action_type VARCHAR(50),
  note_id VARCHAR(100),
  old_value VARCHAR(255),
  new_value VARCHAR(255),
  reason VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(100),
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);

CREATE TABLE tag_suggestions (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  note_id VARCHAR(100) NOT NULL,
  suggested_tag VARCHAR(100),
  confidence_score DECIMAL(3,2),
  reason VARCHAR(255),
  accepted BOOLEAN,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);
```

---

### Implementation Workflow

#### Telegram Commands

```
/reorganize-start
  → Present 3 organization options
  → User selects preferred structure

/reorganize-preview
  → Show migration plan
  → Highlight potential conflicts
  → Ask for confirmation

/reorganize-execute
  → Begin migration
  → Show progress
  → Create backup
  → Execute changes
  → Verify completion

/reorganize-rollback
  → Revert to previous state
  → Restore backup
  → Verify integrity

/tag-audit
  → Show current tags
  → Identify duplicates/conflicts
  → Suggest consolidation
  → Apply changes

/enrich-notes
  → Scan notes
  → Suggest metadata
  → Generate summaries
  → Add relationships
  → Apply enrichments

/show-structure
  → Display current folder hierarchy
  → Show statistics
  → Display tag cloud
  → Show organization health
```

---

### Performance Considerations

For large databases (1000+ notes):
- Batch operations with progress tracking
- Asynchronous processing with status updates
- Database indexing on frequently queried fields
- Caching for folder structure
- Rate limiting on Joplin API calls

### Conflict Resolution

When reorganizing:
- Detect duplicate notes in new locations
- Suggest merge vs. keeping separate
- Handle circular relationships gracefully
- Track all conflicts in database
- Require user approval for merges

### Safety & Rollback

- Automatic backup before reorganization
- Maintain complete audit trail
- Enable reverting individual actions
- Preserve original creation dates
- Track who made changes and when

---

## Success Metrics

- User satisfaction with new organization
- Reduction in time to find notes (before/after measurement)
- Increase in note discovery (cross-referencing)
- Tag consistency and coverage
- Database health score
- Engagement with enriched metadata

## Notes

This is a transformational feature that converts Joplin from a note dump into a knowledge management system. The three organizational options respect the PARA principles while allowing flexibility:

- **Option 1**: Best for traditional project managers
- **Option 2**: Best for complex multi-role professionals
- **Option 3**: Best for time-conscious planners

All three maintain PARA's proven structure while allowing customization. The enrichment component adds lasting value—metadata makes notes exponentially more useful over time.

Consider implementing this as a guided wizard with undo capability at each step to reduce user anxiety about reorganizing a large database.

## Implementation Status (as of 2026-03-01)

### What's Done (~55%)
- **Reorg handlers**: 9 of 10 commands registered (`/reorg_init`, `/reorg_preview`, `/reorg_execute`, `/reorg_status`, `/reorg_detect_conflicts`, `/reorg_audit_tags`, `/reorg_history`, `/reorg_help`, `/enrich_notes`)
- **PARA structure creation**: 2 templates (status, roles) with full folder creation via `get_or_create_folder_by_path`
- **Migration plan + execution**: LLM-based note classification, `execute_migration_plan()` with dry-run support
- **Enrichment service**: Full pipeline — YAML front matter injection (status, priority, summary, key takeaways, tags), batch processing, `augment_note_with_research()`
- **Conflict detection**: Duplicate titles, invalid folders, tag conflicts
- **Tag audit**: Case-insensitive duplicate detection

### What's Missing (~45%)
- **Rollback/undo**: No `/reorganize-rollback`, no automatic backup before migration
- **Third PARA template**: Time-based/quarterly template not implemented
- **Tag hierarchy**: No parent/child tag relationships
- **Tag merge/deprecate**: Only audit exists, no systematic management
- **Full enrichment metadata**: Missing Created, Updated, Review Date, Source, Related Notes, bidirectional linking
- **Persistent audit trail**: History is in-memory `OperationLog` only, 6 planned DB tables not created
- **Custom organization rules**: Not implemented
- **Visual folder tree**: Only basic stats in `/reorg_status`
- **Large-DB optimization**: Migration plan samples 20 notes only

### Key Files
- `src/handlers/reorg.py` — Command handlers
- `src/reorg_orchestrator.py` (414 lines) — Core orchestration logic
- `src/enrichment_service.py` (250 lines) — Note enrichment pipeline
- `src/prompts/para_classifier.txt` — LLM classification prompt
- `src/prompts/note_enricher.txt` — LLM enrichment prompt

## History

- 2025-01-23 - Created
- 2026-03-01 - Status updated to ⏳ In Progress (~55%) based on code review
