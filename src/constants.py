"""
Application-wide constants.

Centralises magic numbers, strings, and thresholds that were
previously scattered across multiple modules.
"""

# --- LLM ---
LLM_DEFAULT_TEMPERATURE = 0.3
LLM_LOW_TEMPERATURE = 0.1
LLM_CREATIVE_TEMPERATURE = 0.5
LLM_DEFAULT_MAX_TOKENS = 1000
LLM_STRUCTURED_MAX_TOKENS = 1500
LLM_AUGMENT_MAX_TOKENS = 800
LLM_CLASSIFY_MAX_TOKENS = 500

# --- Confidence thresholds ---
CONFIDENCE_HIGH = 0.8
CONFIDENCE_MEDIUM = 0.5

# --- Note limits ---
NOTE_TITLE_MAX_LENGTH = 100
NOTE_BODY_MAX_LENGTH = 100_000
MESSAGE_MAX_LENGTH = 10_000
SANITIZE_MAX_LENGTH = 5_000

# --- API pagination ---
TAGS_DISPLAY_LIMIT = 20
RECENT_MESSAGES_LIMIT = 10
DECISIONS_QUERY_LIMIT = 50
LLM_INTERACTIONS_LIMIT = 20
CONVERSATION_HISTORY_LIMIT = 3

# --- Timeouts (seconds) ---
JOPLIN_PING_TIMEOUT = 5
JOPLIN_REQUEST_TIMEOUT = 10
LLM_REQUEST_TIMEOUT = 60
GOOGLE_AUTH_TIMEOUT = 10

# --- Data retention ---
STATE_CLEANUP_DAYS = 7
LOG_CLEANUP_DAYS = 30

# --- Action-item detection ---
ACTION_INDICATORS = frozenset([
    "todo",
    "task",
    "follow",
    "call",
    "email",
    "schedule",
    "remind",
])

# Phrases that mean the user explicitly wants a Joplin note (not a Google Task)
NOTE_INTENT_PHRASES = frozenset([
    "joplin note",
    "add note",
    "save to joplin",
    "add to joplin",
    "save to notes",
    "add to notes",
    "add url",
    "save url",
    "save link",
])


def has_explicit_note_intent(text: str) -> bool:
    """Return True if the user clearly asked for a note (e.g. 'add a joplin note', 'add url')."""
    lower = text.lower().strip()
    return any(phrase in lower for phrase in NOTE_INTENT_PHRASES)


def is_action_item(text: str) -> bool:
    """Return True if *text* looks like it contains an action item (and not explicit note intent)."""
    if has_explicit_note_intent(text):
        return False
    lower = text.lower()
    return any(indicator in lower for indicator in ACTION_INDICATORS)


# --- Priority tags ---
PRIORITY_TAGS = frozenset(["urgent", "critical", "important", "high"])
