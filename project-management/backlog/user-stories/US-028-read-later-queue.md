# User Story: US-028 - Read Later Queue

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 5
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Sprint 11

## Description

Add a "Read Later" queue for saving URLs to read when you have time. Users can quickly save articles with `/readlater <url>`, view their reading queue with `/reading`, and mark items as read. The system leverages existing URL enrichment to fetch titles and summaries, making the queue scannable.

This extends the existing URL handling capability into a proper reading workflow.

## User Story

As a user who encounters interesting articles throughout the day,
I want to quickly save them for later reading,
so that I don't lose track of content I want to consume without interrupting my current work.

## Acceptance Criteria

- [ ] `/readlater <url>` saves URL to reading queue
- [ ] Automatic title and summary extraction (using existing URL enrichment)
- [ ] `/reading` shows queue with titles and short summaries
- [ ] `/reading done <id>` marks item as read (moves to archive or deletes)
- [ ] Queue stored in Joplin folder: `03 - Resources/📚 Reading List/`
- [ ] Each item is a note with metadata (source, date saved, read status)
- [ ] Optional: `/reading random` picks a random unread item
- [ ] Optional: Periodic reminder "You have X unread articles"
- [ ] Queue supports pagination for large lists

## Business Value

Information capture is already solved, but consumption is a gap. Users save articles but:
- Forget they saved them
- Can't find them when they have reading time
- Don't have a sense of queue size or prioritization

A dedicated reading queue with visibility creates a better reading habit and ensures captured content actually gets consumed.

## Technical Requirements

### 1. Reading List Folder Structure

```
03 - Resources/
└── 📚 Reading List/
    ├── [2026-03-05] Article Title Here.md
    ├── [2026-03-04] Another Article.md
    └── ...
```

### 2. Note Format

```markdown
# Article Title Here

**Source**: https://example.com/article
**Saved**: 2026-03-05 14:32
**Status**: 📖 Unread

## Summary
{AI-generated summary from URL enrichment}

## Key Points
- Point 1
- Point 2
- Point 3

---
*Saved via /readlater*
```

### 3. Commands

| Command | Description |
|---------|-------------|
| `/readlater <url>` | Save URL to reading queue |
| `/rl <url>` | Shortcut for /readlater |
| `/reading` | Show unread items (most recent first) |
| `/reading all` | Show all items including read |
| `/reading done <id>` | Mark item as read |
| `/reading delete <id>` | Remove from queue |
| `/reading random` | Pick random unread item |
| `/reading stats` | Show queue statistics |

### 4. Queue Display Format

```
📚 **Reading Queue** (5 unread)

1️⃣ **How to Build Better Habits**
   _jamesclear.com • Saved 2 days ago_
   Building habits requires understanding the habit loop...

2️⃣ **The Future of AI Development**
   _techcrunch.com • Saved 1 week ago_
   Recent advances in large language models have...

3️⃣ **Cooking the Perfect Steak**
   _seriouseats.com • Saved 2 weeks ago_
   The reverse sear method produces consistently...

Reply with number to open, or `/reading done 1` to mark as read.
```

### 5. Data Model

```python
class ReadingItem(BaseModel):
    id: str  # Joplin note ID
    url: str
    title: str
    domain: str
    summary: str
    saved_at: datetime
    read_at: datetime | None = None
    status: str = "unread"  # "unread", "read", "archived"
    tags: list[str] = []
```

### 6. Implementation Flow

```
/readlater <url>
       │
       ▼
┌──────────────────────┐
│ Fetch URL content    │ (existing URL enrichment)
│ Extract title/summary│
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│ Create Joplin note   │
│ in Reading List folder│
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│ Tag with "reading",  │
│ "unread", domain     │
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│ Confirm to user      │
│ "Added: {title}"     │
└──────────────────────┘
```

### 7. Status Tracking

Use tags or note metadata to track status:

```python
# Option A: Tags
READING_TAGS = {
    "unread": "reading/unread",
    "read": "reading/read",
    "archived": "reading/archived"
}

# Option B: Note body status field
# Parse and update "**Status**: 📖 Unread" line
```

### 8. Reminder System (Optional)

```python
async def send_reading_reminder(user_id: int, orch: TelegramOrchestrator):
    """Send weekly reminder about unread items."""
    unread_count = await _get_unread_count(user_id, orch)

    if unread_count > 0:
        await orch.send_message(
            user_id,
            f"📚 You have {unread_count} unread articles in your reading queue.\n"
            f"Use /reading to see them or /reading random for a suggestion!"
        )
```

## Implementation

### Key Files to Create

| File | Purpose |
|------|---------|
| `src/handlers/reading.py` | Reading queue handlers |
| `src/reading_service.py` | Queue management logic |
| `tests/test_reading.py` | Unit tests |

### Key Files to Modify

| File | Changes |
|------|---------|
| `src/handlers/__init__.py` | Register reading handlers |
| `src/url_enrichment.py` | Ensure reusable for reading queue |
| `config.py` | Add reading config (folder name, reminder settings) |

### Folder Setup

Ensure Reading List folder exists:

```python
async def _ensure_reading_folder(orch: TelegramOrchestrator) -> str:
    """Get or create the Reading List folder."""
    folders = await orch.joplin_client.get_folders()

    # Find Resources folder
    resources = next((f for f in folders if "Resources" in f.title), None)
    if not resources:
        resources = await orch.joplin_client.create_folder("03 - Resources")

    # Find or create Reading List subfolder
    reading_list = next(
        (f for f in folders if f.parent_id == resources.id and "Reading" in f.title),
        None
    )
    if not reading_list:
        reading_list = await orch.joplin_client.create_folder(
            "📚 Reading List",
            parent_id=resources.id
        )

    return reading_list.id
```

## Testing

### Unit Tests

- [ ] Test URL saving creates correct note format
- [ ] Test queue retrieval and sorting
- [ ] Test mark as read updates status
- [ ] Test delete removes note
- [ ] Test random selection
- [ ] Test stats calculation

### Manual Testing Scenarios

| Input | Expected |
|-------|----------|
| `/readlater https://example.com/article` | Note created, confirmation shown |
| `/reading` with empty queue | "Your reading queue is empty" |
| `/reading` with 10 items | Show first 5, pagination hint |
| `/reading done 1` | First item marked read, confirmation |
| `/reading random` | Random unread item shown |

## Dependencies

- US-010: URL Enrichment (required - for title/summary extraction)
- US-005: Joplin REST API Client (required)
- US-003: PARA Folder Structure (recommended - for Resources folder)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| URL fetching fails | Save with URL only, note to try enrichment later |
| Queue grows unbounded | Show queue age, suggest cleanup |
| Duplicate URLs | Check before adding, warn if exists |
| Paywall/login-required content | Note limitation in summary |

## Future Enhancements

- [ ] Priority/star important articles
- [ ] Estimated read time based on content length
- [ ] Category/topic tagging
- [ ] Import from Pocket/Instapaper
- [ ] Weekly digest email with queue summary
- [ ] Integration with e-reader (send to Kindle)
- [ ] Highlights/annotations during reading

## Notes

- Leverage existing URL enrichment - don't duplicate logic
- Keep the `/reading` display concise - users scan, not read
- Consider archiving rather than deleting read items
- Domain extraction helps users identify source quickly

## History

- 2026-03-05 - Feature request created
