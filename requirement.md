# Intelligent Joplin Librarian

Implementing this "Intelligent Joplin Librarian" requires a multi-layered Python architecture that combines an asynchronous Telegram handler, an LLM orchestrator for structured output, and a REST client for the Joplin Data API.

🛠️ **The Technical Implementation Plan**

The solution follows a Stateful Orchestrator pattern. The script maintains a conversation state for each user to allow the "talk back" (clarification) logic before committing data to Joplin.

## 1. The Technology Stack

- **Telegram Interface**: python-telegram-bot (v20+) for the asynchronous event loop.
- **LLM Integration**: openai or langchain with Structured Outputs (Pydantic models) to enforce the JSON schema.
- **Joplin Interface**: requests or httpx to communicate with http://localhost:41184.
- **State Management**: A simple Python dict (or SQLite for persistence) to track pending_notes and conversation history.

## 2. Implementation Modules

### A. The Joplin REST Client

This module abstracts the complexity of port 41184. It needs methods to:

- `fetch_tags()`: Gets existing tags to feed the LLM.
- `Notes(folder_id, title, body)`: Posts the finalized note.
- `apply_tags(note_id, tags)`: Handles the logic of checking for/creating tags.
- `append_log(log_row)`: Updates the centralized AI-Decision-Log note using a PUT request.

### B. The LLM Logic (The "Brain")

Using Pydantic, define the exact schema the LLM must return.

```python
from pydantic import BaseModel
from typing import List, Optional

class JoplinNoteSchema(BaseModel):
    status: str  # "SUCCESS" or "NEED_INFO"
    confidence_score: float
    question: Optional[str]
    log_entry: str
    note: Optional[dict]  # Contains title, body, parent_id, tags
```

### C. The Telegram Orchestrator (The "Controller")

- **Incoming Message**: Check if user_id has a pending state.
- **Context Building**: If pending, merge the new reply with the previous message.
- **Inference**: Send the context + Existing Tags to the LLM.
- **Decision Gate**:
  - IF confidence < 0.8 OR status == "NEED_INFO": Store context in state and reply to user with the LLM's question.
  - IF SUCCESS: Send note data to Joplin. Append the log_entry to the Joplin Log Note. Clear the user state.

## 3. Step-by-Step Execution Plan

| Step | Action | Objective |
|------|--------|-----------|
| 1 | Setup Env | Install python-telegram-bot, openai, and requests. |
| 2 | Folder Discovery | Run a script to map your 00-04 folder names to their Joplin IDs. |
| 3 | Prompt Engineering | Implement the TCREI prompt as the "System Message" for your LLM. |
| 4 | Tag Sync | Write the function that retrieves your Joplin tags every 10 minutes to keep the LLM updated. |
| 5 | The Log Note | Create a note in Joplin titled AI-Decision-Log and copy its ID into your script. |
| 6 | Deployment | Run the script locally on the machine where Joplin is open. |

🔍 **Error Handling & Security**

- **Port 41184 Check**: Before every operation, the script should "ping" the Joplin API. If Joplin is closed, the bot should tell you: "I'm ready, but Joplin isn't open on your computer!"
- **Whitelist**: Ensure the handle_message function checks update.message.from_user.id against your personal Telegram ID to prevent others from accessing your Joplin.

## Building a Telegram bot with Python-Telegram-Bot

This video provides a practical walkthrough of setting up the asynchronous handlers and conversation logic required to make your bot "remember" context and ask follow-up questions.

Would you like me to provide the specific Python Pydantic model and System Prompt code for the LLM component of this plan?