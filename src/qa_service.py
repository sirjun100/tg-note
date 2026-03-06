"""
Q&A service for semantic search over notes (FR-026).

Orchestrates: embed question → search index → retrieve chunks → LLM synthesize → format.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.joplin_client import JoplinClient
    from src.llm_orchestrator import LLMOrchestrator
    from src.note_index import NoteIndex

logger = logging.getLogger(__name__)

QA_SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the user's personal notes.

You have access to relevant excerpts from the user's Joplin notes. Use ONLY this context to answer questions.

Guidelines:
- Answer based solely on the provided context
- If the context doesn't contain enough information, say "I couldn't find information about that in your notes"
- Cite which notes the information came from (use the note titles provided)
- Be concise but complete
- If multiple notes are relevant, synthesize the information

Context from notes:
{context}
"""

QA_USER_PROMPT = """Question: {question}

Please answer based on the note excerpts above."""


async def ask_question(
    question: str,
    note_index: NoteIndex,
    joplin_client: JoplinClient,
    llm_orchestrator: LLMOrchestrator,
    top_k: int = 8,
) -> dict[str, Any]:
    """
    Ask a question and get an AI-synthesized answer from notes.

    Returns:
        dict with keys: answer (str), sources (list of {title, note_id}), not_found (bool)
    """
    question = (question or "").strip()
    if not question:
        return {
            "answer": "Please provide a question.",
            "sources": [],
            "not_found": True,
        }

    try:
        results = await note_index.search(question, top_k=top_k)
    except RuntimeError as exc:
        logger.warning("Note index search failed: %s", exc)
        return {
            "answer": str(exc),
            "sources": [],
            "not_found": True,
        }

    if not results:
        return {
            "answer": "I couldn't find any relevant notes. Try rephrasing your question or run /reindex to rebuild the search index.",
            "sources": [],
            "not_found": True,
        }

    # Build context from chunks (dedupe by note, keep best chunk per note)
    seen: set[str] = set()
    context_parts: list[str] = []
    sources: list[dict[str, str]] = []
    for r in results:
        note_id = r["note_id"]
        title = r["title"]
        chunk = r["chunk_text"]
        if note_id not in seen:
            seen.add(note_id)
            sources.append({"note_id": note_id, "title": title})
        context_parts.append(f"--- From \"{title}\" ---\n{chunk}")

    context = "\n\n".join(context_parts)

    system = QA_SYSTEM_PROMPT.format(context=context)
    user = QA_USER_PROMPT.format(question=question)

    try:
        answer = await llm_orchestrator.generate_text_for_qa(system, user)
        if not answer:
            answer = "I couldn't generate an answer from the available context."
    except Exception as exc:
        logger.error("Q&A LLM failed: %s", exc)
        return {
            "answer": "Sorry, I had trouble generating an answer. Please try again.",
            "sources": sources,
            "not_found": False,
        }

    return {
        "answer": answer.strip(),
        "sources": sources,
        "not_found": False,
    }
