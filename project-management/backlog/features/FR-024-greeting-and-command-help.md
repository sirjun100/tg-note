# Feature Request: FR-024 - Greeting Response and Command Discovery

**Status**: ⭕ Not Started
**Priority**: 🟡 Medium
**Story Points**: 3
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Sprint 10

## Description

When users send greetings like "hello", "hi", or "hey", the LLM should recognize this as a social interaction rather than a note creation request. Instead of asking clarifying questions or attempting to create a note, the bot should respond with a friendly greeting and surface the most useful commands available.

Currently, sending "hello" triggers the note creation flow, resulting in a confusing "What would you like me to note?" response.

## User Story

As a new or returning user,
I want to say hello and get a friendly response with available commands,
so that I can quickly learn what the bot can do and start using it effectively.

## Acceptance Criteria

- [ ] LLM recognizes common greetings (hello, hi, hey, good morning, etc.)
- [ ] Bot responds with a friendly greeting
- [ ] Response includes top 5-7 most useful commands with brief descriptions
- [ ] Response is concise (not overwhelming)
- [ ] Works in multiple languages (at minimum: English, French)
- [ ] Does NOT trigger note creation flow
- [ ] Greeting detection has high confidence (avoid false positives)

## Business Value

First impressions matter. When users first interact with the bot or return after time away, a greeting is natural. A helpful response that shows available commands:
- Reduces friction for new users
- Reminds returning users of capabilities
- Creates a more human-like interaction
- Prevents confusion from the note creation prompt

## Technical Requirements

### 1. Greeting Detection

Add greeting recognition to the system prompt or as a pre-classification step:

```python
GREETING_PATTERNS = [
    r"^(hi|hello|hey|howdy|greetings)\b",
    r"^good (morning|afternoon|evening|day)\b",
    r"^(bonjour|salut|coucou|bonsoir)\b",  # French
    r"^what('s| is) up\b",
    r"^yo\b",
]
```

### 2. Extended Content Types

Add `greeting` as a content type in the classification:

```python
class ContentDecision(BaseModel):
    content_type: str  # "note", "task", "both", "greeting"
    # ...
```

Or handle separately before LLM call (simpler, saves tokens).

### 3. Greeting Response Template

```
👋 Hello! I'm your Second Brain assistant.

Here's what I can help you with:

📝 **Capture**
• Send any text → I'll save it as a Joplin note
• `/tasks <text>` → Create a Google Task
• `/notes <text>` → Force note creation

🧠 **Productivity**
• `/braindump` → 15-min GTD brain dump session
• `/stoic` → Guided morning/evening reflection
• `/recipe` → Save and organize recipes

📊 **Review**
• `/report` → Today's priorities
• `/weekly_report` → Weekly productivity review

💡 Type anything to get started, or use a command above!
```

### 4. Command Priority

Display commands in order of usefulness:
1. Basic capture (notes/tasks)
2. Guided sessions (braindump, stoic)
3. Reports (daily, weekly)
4. Settings/help (optional, can mention /help exists)

### 5. Time-Aware Greeting (Optional Enhancement)

Respond contextually based on time:
- Morning (5am-12pm): "Good morning! ☀️"
- Afternoon (12pm-5pm): "Good afternoon! 👋"
- Evening (5pm-9pm): "Good evening! 🌆"
- Night (9pm-5am): "Hello! 🌙"

## Implementation

### Option A: Pre-LLM Detection (Recommended)

Detect greetings before calling the LLM to save tokens:

```python
# In core.py, before LLM call
async def _handle_text_message(...):
    if _is_greeting(text):
        await _send_greeting_response(message, user_id, orch)
        return

    # Continue with normal LLM flow...
```

### Option B: LLM Classification

Add to system prompt:

```
### Greetings
When the user sends a greeting (hello, hi, hey, good morning, etc.):
- Set content_type to "greeting"
- Do NOT create a note or task
- Respond with a friendly greeting and command list
```

### Key Files to Modify

| File | Changes |
|------|---------|
| `src/handlers/core.py` | Add `_is_greeting()` and `_send_greeting_response()` |
| `src/prompts/greeting_response.txt` | Template for greeting message (optional) |
| `tests/test_greeting.py` | Test greeting detection and response |

### Greeting Detection Function

```python
import re

GREETING_PATTERNS = [
    r"^(hi|hello|hey|howdy|greetings|yo)[\s!?.]*$",
    r"^good\s+(morning|afternoon|evening|day|night)[\s!?.]*$",
    r"^(bonjour|salut|coucou|bonsoir|bonne\s+journée)[\s!?.]*$",
    r"^what'?s?\s+up[\s!?.]*$",
    r"^(hola|buenos\s+días|buenas\s+tardes)[\s!?.]*$",
]

def _is_greeting(text: str) -> bool:
    """Check if text is a simple greeting."""
    text_lower = text.strip().lower()
    return any(re.match(pattern, text_lower) for pattern in GREETING_PATTERNS)
```

### Greeting Response Function

```python
from src.timezone_utils import get_user_timezone_aware_now

async def _send_greeting_response(
    message: Message,
    user_id: int,
    orch: TelegramOrchestrator
) -> None:
    """Send a friendly greeting with available commands."""
    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    hour = now.hour

    if 5 <= hour < 12:
        time_greeting = "Good morning! ☀️"
    elif 12 <= hour < 17:
        time_greeting = "Good afternoon! 👋"
    elif 17 <= hour < 21:
        time_greeting = "Good evening! 🌆"
    else:
        time_greeting = "Hello! 🌙"

    response = f"""{time_greeting} I'm your Second Brain assistant.

**📝 Capture**
• Send any text → Save as Joplin note
• `/tasks <text>` → Create Google Task
• `/notes <text>` → Force note creation

**🧠 Productivity**
• `/braindump` → GTD brain dump session
• `/stoic` → Morning/evening reflection
• `/recipe` → Save and organize recipes

**📊 Review**
• `/report` → Today's priorities
• `/weekly_report` → Weekly review

Type anything to get started!"""

    await message.reply_text(response)
```

## Testing

### Unit Tests

- [ ] Test English greetings (hello, hi, hey, good morning)
- [ ] Test French greetings (bonjour, salut)
- [ ] Test greetings with punctuation (Hello!, Hi?, Hey...)
- [ ] Test non-greetings don't match ("hello world", "say hello to John")
- [ ] Test time-aware greeting selection
- [ ] Test response includes key commands

### Test Cases

| Input | Expected |
|-------|----------|
| "hello" | Greeting response |
| "Hi!" | Greeting response |
| "Good morning" | Greeting response (morning variant) |
| "Bonjour" | Greeting response |
| "Hello, please create a note" | NOT a greeting (continue to LLM) |
| "Say hello to the team" | NOT a greeting (continue to LLM) |
| "hello world" | NOT a greeting (continue to LLM) |

## Dependencies

- None (standalone feature)

## Future Enhancements

- [ ] Personalized greeting with user's name (if available)
- [ ] Show different commands based on user's usage patterns
- [ ] "What's new" section for recently added features
- [ ] Onboarding flow for first-time users
- [ ] Remember user's language preference

## Notes

- Keep response concise - users want quick info, not a wall of text
- Use markdown formatting for readability in Telegram
- Consider rate limiting greeting responses to avoid spam

## History

- 2026-03-05 - Feature request created
