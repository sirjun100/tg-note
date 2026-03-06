# Bug Fix: BF-023 - /ask Command Crashes on Certain Prompts

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 2
**Created**: 2026-03-06
**Updated**: 2026-03-06
**Assigned Sprint**: Sprint 15

## Description

The `/ask` command crashes when given certain prompts. User report: `/ask how did I learn how to cook` causes a crash. The user receives no answer or a generic error instead of the AI-synthesized response from their notes.

## Steps to Reproduce

1. Ensure user is whitelisted and has indexed notes (run `/reindex` if needed).
2. Send `/ask how did I learn how to cook` to the bot.
3. Observe: Command crashes; user may see "Could not answer. Please try again or run /reindex" or no response. Server logs may show an exception.

## Expected Behavior

- Bot returns an AI-synthesized answer based on relevant notes from the semantic search index.
- Answer is displayed with sources (note titles).
- User receives the full response in Telegram.

## Actual Behavior

- Command crashes.
- User does not receive the answer.
- May see generic error: "Could not answer. Please try again or run /reindex."

## Environment

- **Platform**: Telegram
- **Bot**: Deployed on Fly.io (or local)
- **Trigger**: `/ask how did I learn how to cook` (and possibly other prompts)
- **Feature**: FR-026 Semantic Search Q&A

## Root Cause (Hypothesis)

Two likely causes:

### 1. Telegram Markdown Parse Error (most likely)

The `/ask` response is built and sent with `parse_mode="Markdown"`:

```python
lines = [f"🔍 **{question}**\n", answer]
if sources:
    lines.append("\n📚 **Sources:**")
    for s in sources[:5]:
        lines.append(f"• \"{s['title']}\"")
response = "\n".join(lines)
await msg.reply_text(response, parse_mode="Markdown")
```

The `answer` comes from the LLM and is inserted **without escaping**. LLM output often contains Markdown-special characters (`*`, `_`, `` ` ``, `[`, `]`) that Telegram interprets as entity delimiters. Unpaired or malformed sequences cause:
- `BadRequest: Can't parse entities: can't find end of the entity starting at byte offset X`
- Same pattern as BF-010 (greeting), BF-014/BF-016 (dream), BF-022 (find).

Source titles from Joplin notes can also contain special characters.

### 2. Other Failures

- **Embedding/search**: Note index search or Gemini embedding API could fail for some queries.
- **LLM synthesis**: `generate_text_for_qa` could raise (provider error, timeout).
- **Message too long**: Answer + sources could exceed Telegram's 4096-char limit (BF-019).

## Solution

1. **Safe message send** (primary): Switch to `parse_mode="HTML"` with `html.escape()` for the answer and source titles, or add a try/except with plain-text fallback when sending (same pattern as BF-010, BF-022).
2. **Split long messages**: If response exceeds 4096 chars, split into multiple messages (BF-019 pattern).
3. **Improve error handling**: Ensure all exceptions are caught and user receives a helpful message; log full traceback for debugging.

## Affected Code

- `src/handlers/ask.py`:
  - `_ask()` handler — lines 50–74: builds response with Markdown, sends with `parse_mode="Markdown"`
  - No escaping of `answer` or source titles
- `src/qa_service.py` — returns `answer` and `sources`; caller is responsible for safe display

## References

- [BF-010: Greeting Parse Entities Error](BF-010-greeting-parse-entities-error.md) — HTML + plain-text fallback
- [BF-014: /dream Parse Entities Error](BF-014-dream-parse-entities-error.md)
- [BF-022: /find Command Error](BF-022-find-command-flyio-error.md) — same fix pattern
- [FR-026: Semantic Search Q&A](../features/FR-026-semantic-search-qa.md)
- [Telegram Bot API: Formatting options](https://core.telegram.org/bots/api#formatting-options)

## Technical References

- File: `src/handlers/ask.py` — `_ask()` handler, lines 50–74
- File: `src/qa_service.py` — `ask_question()`, `generate_text_for_qa`
- File: `src/llm_orchestrator.py` — `generate_text_for_qa()`

## Testing

- [ ] `/ask how did I learn how to cook` returns answer without crash
- [ ] `/ask` with question that would produce answer containing `*`, `_` in response — no parse error
- [ ] Verify in production (Fly.io) after deploy

## Notes

- User-provided repro: "ask how did I learn how to cook"
- If Fly.io logs are available, include the exact exception/traceback to confirm root cause
- Consider adding a generic "safe send" helper for LLM-generated content used across /ask, /dream, etc.

## Implementation Guide

**Sprint 15**: See [sprint-15-implementation-guide.md](../../sprints/sprint-15-implementation-guide.md) § BF-023 for exact code changes: `html.escape`, `_send_ask_response_safe`, `split_message_for_telegram`. Copy pattern from `src/handlers/search.py` `_send_search_results_safe`.

## History

- 2026-03-06 - Created (user report: /ask crashes on "how did I learn how to cook")
