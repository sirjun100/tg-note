# User Story: US-026 - Semantic Search and Q&A Over Notes

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 13
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Sprint 12

## Description

Enable users to ask natural language questions about their Joplin notes and receive AI-synthesized answers. Instead of keyword searching and manually reading through notes, users can ask questions like "How did I solve the caching issue last month?" or "What were the key points from my meeting with Sarah?" and get contextual answers drawn from their knowledge base.

This transforms the Second Brain from a write-only archive into a true retrieval system.

## User Story

As a user with hundreds of notes in Joplin,
I want to ask questions in natural language and get answers from my notes,
so that I can quickly retrieve knowledge without manually searching and reading.

## Acceptance Criteria

- [ ] `/ask <question>` searches notes and returns AI-synthesized answer
- [ ] Search uses semantic similarity (not just keyword matching)
- [ ] Answer includes source note references (titles + links)
- [ ] Works across all Joplin folders (respects PARA structure)
- [ ] Handles "I don't know" gracefully when no relevant notes found
- [ ] Response time < 10 seconds for typical queries
- [ ] Supports follow-up questions with conversation context
- [ ] Results limited to user's own notes (security)

## Business Value

The value of a Second Brain compounds only if you can retrieve knowledge when needed. Currently, users must:
1. Remember that they captured something
2. Guess the right keywords
3. Search in Joplin
4. Read through results to find the answer

Semantic Q&A reduces this to one step: ask a question, get an answer. This dramatically increases the ROI of note-taking and encourages more capture.

## Technical Requirements

### 1. Architecture Overview

```
User asks question
        │
        ▼
┌───────────────────┐
│ Embed question    │ (OpenAI/local embeddings)
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Vector search     │ (Find similar note chunks)
│ in note index     │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Retrieve top-k    │ (k=5-10 most relevant chunks)
│ note chunks       │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ LLM synthesizes   │ (Answer question using context)
│ answer            │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Format response   │ (Answer + source citations)
│ with sources      │
└───────────────────┘
```

### 2. Note Indexing

Index Joplin notes for semantic search:

```python
class NoteIndex:
    """Manages vector embeddings for Joplin notes."""

    def __init__(self, embedding_provider: str = "openai"):
        self.embeddings = []  # Vector store (ChromaDB, FAISS, or simple)
        self.provider = embedding_provider

    async def index_note(self, note_id: str, title: str, body: str) -> None:
        """Chunk and embed a note."""
        chunks = self._chunk_text(body, chunk_size=500, overlap=50)
        for i, chunk in enumerate(chunks):
            embedding = await self._get_embedding(chunk)
            self.embeddings.append({
                "note_id": note_id,
                "title": title,
                "chunk_index": i,
                "text": chunk,
                "vector": embedding
            })

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Find most similar note chunks to query."""
        query_embedding = await self._get_embedding(query)
        # Cosine similarity search
        results = self._cosine_search(query_embedding, top_k)
        return results
```

### 3. Embedding Options

| Provider | Pros | Cons |
|----------|------|------|
| OpenAI `text-embedding-3-small` | High quality, easy | Cost, API dependency |
| Local (sentence-transformers) | Free, private | Requires GPU/CPU resources |
| Ollama embeddings | Local, decent quality | Setup complexity |

Recommend: Start with OpenAI, add local option later.

### 4. Vector Storage Options

| Option | Pros | Cons |
|--------|------|------|
| ChromaDB | Easy, persistent, good for small-medium | Another dependency |
| FAISS | Fast, battle-tested | More setup |
| SQLite + numpy | Simple, no new deps | Manual implementation |
| In-memory | Simplest | Lost on restart |

Recommend: ChromaDB for persistence, or SQLite with manual cosine similarity for simplicity.

### 5. Q&A Prompt

```python
QA_SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the user's personal notes.

You have access to relevant excerpts from the user's Joplin notes. Use ONLY this context to answer questions.

Guidelines:
- Answer based solely on the provided context
- If the context doesn't contain enough information, say "I couldn't find information about that in your notes"
- Cite which notes the information came from
- Be concise but complete
- If multiple notes are relevant, synthesize the information

Context from notes:
{context}
"""

QA_USER_PROMPT = """Question: {question}

Please answer based on the note excerpts above."""
```

### 6. Response Format

```
Based on your notes, here's what I found:

[Synthesized answer here...]

📚 **Sources:**
• "Meeting Notes - Q3 Planning" (2026-02-15)
• "Project Alpha Technical Decisions" (2026-01-20)
```

### 7. Indexing Strategy

**Option A: On-demand indexing**
- Index notes when `/ask` is first used
- Re-index periodically or on `/reindex`
- Simpler but slower first query

**Option B: Incremental indexing**
- Index new notes after creation
- Background job updates index
- Faster queries, more complexity

**Option C: Webhook-based**
- Joplin doesn't support webhooks natively
- Would need polling for changes

Recommend: Option A for MVP, upgrade to B later.

## Implementation

### Key Files to Create

| File | Purpose |
|------|---------|
| `src/note_index.py` | Vector embedding and search |
| `src/qa_service.py` | Q&A orchestration |
| `src/handlers/search.py` | Command handlers |
| `tests/test_semantic_search.py` | Unit tests |

### Key Files to Modify

| File | Changes |
|------|---------|
| `src/handlers/core.py` | Register search commands |
| `requirements.txt` | Add chromadb, openai (if not present) |
| `config.py` | Add embedding config |

### Commands

| Command | Description |
|---------|-------------|
| `/ask <question>` | Ask a question about your notes |
| `/reindex` | Rebuild the note index |
| `/search_status` | Show index stats (note count, last updated) |

### Index Storage

Store embeddings in SQLite or ChromaDB:

```python
# SQLite approach
CREATE TABLE note_embeddings (
    id INTEGER PRIMARY KEY,
    note_id TEXT NOT NULL,
    title TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding BLOB NOT NULL,  -- numpy array serialized
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(note_id, chunk_index)
);
```

## Testing

### Unit Tests

- [ ] Test note chunking (correct sizes, overlap)
- [ ] Test embedding generation
- [ ] Test similarity search (returns relevant results)
- [ ] Test Q&A synthesis (uses context correctly)
- [ ] Test "not found" case
- [ ] Test source citation formatting

### Integration Tests

- [ ] End-to-end `/ask` command
- [ ] Index rebuild with `/reindex`
- [ ] Large note handling (> 10k words)

### Manual Testing Scenarios

| Question | Expected Behavior |
|----------|-------------------|
| "What did I decide about the database?" | Finds tech decision notes, synthesizes |
| "When is Sarah's birthday?" | Finds if captured, says "not found" otherwise |
| "Summarize my meeting notes from last week" | Aggregates recent meeting notes |
| "How do I deploy to production?" | Finds deployment documentation |

## Dependencies

- US-005: Joplin REST API Client (required - for fetching notes)
- US-006: LLM Integration (required - for answer synthesis)
- OpenAI API or local embedding model

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Slow indexing for large note collections | Background job, progress indicator |
| Embedding API costs | Cache embeddings, batch requests |
| Poor search quality | Tune chunk size, use reranking |
| Privacy concerns with cloud embeddings | Offer local embedding option |
| Index gets stale | Periodic re-index, manual trigger |

## Future Enhancements

- [ ] Conversation memory for follow-up questions
- [ ] Filter by folder/tag in search
- [ ] "Related notes" suggestions when creating new notes
- [ ] Hybrid search (semantic + keyword)
- [ ] Local embedding support (Ollama, sentence-transformers)
- [ ] Auto-index on note creation

## Notes

- Start with OpenAI embeddings for simplicity
- Chunk size of 500 tokens with 50 token overlap works well
- Consider caching frequent queries
- Index only note body, not metadata (faster, more relevant)

## History

- 2026-03-05 - Feature request created
