# State Management — Business Overview

This document explains how the bot "remembers" conversations from a product and user-experience perspective.

## What Is State?

**State** is the bot's memory of an ongoing conversation. When you send a message, the bot may need to:

- Ask a follow-up question before creating a note
- Continue a multi-turn session (e.g. brain dump, Stoic journal)
- Track your choices in a guided flow (e.g. search, planning)

State stores the context so your next message is interpreted correctly.

## User-Facing Behaviors

### 1. Clarification Questions

**Scenario**: You send "Meeting with John" and the bot isn't sure whether it's a project note, a contact, or something else.

**What happens**:

1. Bot asks: *"What kind of note is this — project update, contact, or something else?"*
2. Bot stores your original message and waits for your reply.
3. You reply: *"Project update for the Q1 initiative."*
4. Bot combines both and creates the note.

**State role**: The bot remembers your original message and merges it with your clarification.

### 2. Persona Sessions

**Scenario**: You run `/braindump` for a 15-minute mind sweep.

**What happens**:

1. Bot starts a guided session and asks the first question.
2. You type several items; the bot asks follow-ups.
3. When done, you use `/braindump_stop` and the bot creates a summary note.

**State role**: The bot remembers you're in a brain dump session and routes all your messages to that flow until you stop.

**Other persona sessions**:

- `/stoic` — Stoic journal prompts
- `/dream` — Dream analysis
- `/planning` — Planning coach
- Search flows — Guided search and selection

### 3. Escape Hatch

**Scenario**: You're in the middle of a clarification or session and want to start fresh.

**What happens**:

- Send a greeting like *"hello"* or *"hi"* — the bot clears any pending state and shows the main menu.
- Use `/start` — same effect.

**State role**: Greetings and `/start` always reset the conversation so you're never "stuck" in a flow.

## When State Is Cleared

| Situation | Result |
|-----------|--------|
| Note created successfully | State cleared; next message starts a new request |
| You send a greeting | State cleared; menu shown |
| You use `/start` | State cleared; welcome message |
| Persona session ends (e.g. `/braindump_stop`) | State cleared |
| You answer a clarification and the bot creates the note | State cleared |

## Business Value

- **Accuracy**: Follow-up questions reduce wrong folder/tag choices.
- **Engagement**: Multi-turn sessions (brain dump, journal) feel like guided conversations.
- **Flexibility**: Users can always "reset" with a greeting or `/start`.
- **Context**: The bot can reference earlier messages in the same session.

## Status Indicator

The `/status` command shows whether you have a **pending clarification**:

- **Pending clarification: Yes** — The bot is waiting for your reply.
- **Pending clarification: No** — No ongoing flow; your next message starts a new request.

## Privacy and Retention

- State is stored per user in a local SQLite database.
- State can be cleaned up automatically after a period of inactivity (e.g. 7 days).
- No state is shared between users.

## Summary

| Concept | Meaning |
|---------|---------|
| **State** | Bot's memory of an ongoing conversation |
| **Clarification** | Bot asked a question; your reply is merged with the original message |
| **Persona session** | Guided flow (brain dump, journal, etc.) where messages are routed to that flow |
| **Escape hatch** | Greeting or `/start` clears state and shows the menu |
| **Pending clarification** | Shown in `/status` when the bot is waiting for your reply |
