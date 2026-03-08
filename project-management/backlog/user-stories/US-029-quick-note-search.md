# User Story: US-029 - Quick Note Search

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 3
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Sprint 10

## Description

Add simple keyword search for Joplin notes directly from Telegram. Users can search with `/find <query>` and get a list of matching notes with snippets, without leaving the chat. This provides basic retrieval capability for when users need to find a specific note.

This is a simpler alternative to semantic search (US-026) - keyword matching rather than AI-powered Q&A.

## User Story

As a user who has captured many notes,
I want to quickly search my notes from Telegram,
so that I can find information without opening Joplin.

## Acceptance Criteria

- [ ] `/find <query>` searches note titles and bodies
- [ ] Returns up to 5-10 matching notes
- [ ] Shows note title, folder, and content snippet
- [ ] Snippet highlights matching text
- [ ] Results sorted by relevance (match quality) or recency
- [ ] Search is case-insensitive
- [ ] Supports multi-word queries
- [ ] Empty results shows helpful message
- [ ] `/find` without query shows usage help

## Business Value

Quick retrieval reduces friction. Users often know they captured something but can't remember where. Being able to search without switching apps or devices:
- Saves time during conversations/calls
- Encourages more note-taking (confidence in retrieval)
- Keeps users in their Telegram workflow

## Technical Requirements

### 1. Joplin Search API

Joplin has built-in search:

```python
async def search_notes(self, query: str, limit: int = 10) -> list[dict]:
    """Search notes using Joplin's search API."""
    response = await self._get(
        "/search",
        params={
            "query": query,
            "type": "note",
            "limit": limit,
            "fields": "id,title,body,parent_id,updated_time"
        }
    )
    return response.get("items", [])
```

### 2. Search Result Format

```
🔍 **Search results for "meeting notes"** (5 found)

1️⃣ **Q3 Planning Meeting Notes**
   📁 Projects/Product Launch
   _...discussed the **meeting notes** format and decided..._

2️⃣ **Team Standup Meeting Notes Template**
   📁 Resources/Templates
   _Template for daily **meeting notes**: Attendees, Agenda..._

3️⃣ **Client Call - March 1**
   📁 Projects/Acme Corp
   _**Meeting notes** from call with Sarah about renewal..._

Reply with number for full note, or search again.
```

### 3. Snippet Extraction

```python
def extract_snippet(body: str, query: str, context_chars: int = 100) -> str:
    """Extract snippet around first match."""
    body_lower = body.lower()
    query_lower = query.lower()

    # Find first occurrence
    pos = body_lower.find(query_lower)
    if pos == -1:
        # If not found in body, return start of note
        return body[:context_chars * 2] + "..."

    # Extract context around match
    start = max(0, pos - context_chars)
    end = min(len(body), pos + len(query) + context_chars)

    snippet = body[start:end]

    # Add ellipsis if truncated
    if start > 0:
        snippet = "..." + snippet
    if end < len(body):
        snippet = snippet + "..."

    # Bold the match (Telegram markdown)
    # Note: Need to escape other markdown in snippet
    return snippet
```

### 4. Folder Name Resolution

Include human-readable folder name:

```python
async def _get_folder_path(folder_id: str, orch: TelegramOrchestrator) -> str:
    """Get folder name for display."""
    folders = await orch.joplin_client.get_folders()
    folder = next((f for f in folders if f.id == folder_id), None)
    return folder.title if folder else "Unknown"
```

### 5. Commands

| Command | Description |
|---------|-------------|
| `/find <query>` | Search notes by keyword |
| `/search <query>` | Alias for /find |
| `/f <query>` | Shortcut for /find |

### 6. Interactive Results

Allow viewing full note:

```python
# When user replies with number
async def handle_search_result_selection(
    message: Message,
    selection: int,
    search_results: list[dict]
) -> None:
    """Handle user selecting a search result."""
    if 1 <= selection <= len(search_results):
        note = search_results[selection - 1]

        # Format full note for display
        response = f"**{note['title']}**\n\n{note['body'][:3000]}"

        if len(note['body']) > 3000:
            response += "\n\n_Note truncated. View full note in Joplin._"

        await message.reply_text(response)
```

### 7. State for Result Selection

Store recent search results in state:

```python
class SearchState(BaseModel):
    query: str
    results: list[dict]  # Store IDs and titles
    timestamp: datetime
```

## Implementation

### Key Files to Create

| File | Purpose |
|------|---------|
| `src/handlers/search.py` | Search command handlers |
| `tests/test_search.py` | Unit tests |

### Key Files to Modify

| File | Changes |
|------|---------|
| `src/handlers/__init__.py` | Register search handlers |
| `src/joplin_client.py` | Add search_notes method if missing |
| `src/state_manager.py` | Add SearchState |

### Handler Implementation

```python
from telegram import Update
from telegram.ext import ContextTypes

async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /find command."""
    message = update.effective_message
    user_id = update.effective_user.id

    # Extract query from command
    query = " ".join(context.args) if context.args else ""

    if not query:
        await message.reply_text(
            "🔍 **Search Notes**\n\n"
            "Usage: `/find <query>`\n"
            "Example: `/find meeting notes`"
        )
        return

    orch = get_orchestrator()

    # Search Joplin
    results = await orch.joplin_client.search_notes(query, limit=5)

    if not results:
        await message.reply_text(
            f"No notes found for \"{query}\".\n"
            "Try different keywords or check spelling."
        )
        return

    # Store results for selection
    await orch.state_manager.set_search_state(user_id, query, results)

    # Format and send results
    response = await format_search_results(query, results, orch)
    await message.reply_text(response)
```

## Testing

### Unit Tests

- [ ] Test search with single word
- [ ] Test search with multiple words
- [ ] Test empty query handling
- [ ] Test no results case
- [ ] Test snippet extraction
- [ ] Test result selection
- [ ] Test folder name resolution

### Manual Testing Scenarios

| Query | Expected |
|-------|----------|
| `/find meeting` | Finds notes with "meeting" in title or body |
| `/find "exact phrase"` | Finds exact phrase matches |
| `/find nonexistent` | "No notes found" message |
| `/find` | Shows usage help |
| Reply "2" after search | Shows full content of result #2 |

## Dependencies

- US-005: Joplin REST API Client (required)
- US-007: Conversation State Management (optional - for result selection)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Large notes exceed Telegram limit | Truncate with "view in Joplin" note |
| Slow search on large collections | Joplin search is fast; add timeout |
| Markdown in snippets breaks formatting | Escape/strip markdown in snippets |
| Too many results | Limit to 5, mention total count |

## Future Enhancements

- [ ] Filter by folder: `/find meeting in:Projects`
- [ ] Filter by tag: `/find meeting tag:work`
- [ ] Filter by date: `/find meeting after:2026-01-01`
- [ ] Sort options: relevance, date, alphabetical
- [ ] Fuzzy matching for typos
- [ ] Recent searches history

## Notes

- This is simpler than semantic search (US-026) - implement this first
- Joplin's built-in search is powerful (supports operators)
- Keep results concise - this is quick lookup, not deep search
- Consider caching folder names to speed up display

## History

- 2026-03-05 - Feature request created
