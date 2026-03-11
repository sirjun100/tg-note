---
template_version: 1.1.0
last_updated: 2025-01-27
compatible_with: [defect, sprint-planning, product-backlog]
requires: [markdown-support]
---

# User Story Template

This is a generic template for creating user stories (Product Backlog Items). Copy this template when adding new user stories to your product backlog.

## Usage

1. Copy this template
2. Assign unique ID (e.g., US-001, US-042, or use your ID format)
3. Fill in all sections
4. Save to: `backlog/user-stories/US-052-[story-name].md`
5. Add entry to main product backlog table

---

# User Story: US-052 - World-Class Stoic Journaling Experience

[← Back to Product Backlog](../product-backlog.md)

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 13
**Created**: 2026-03-08
**Updated**: 2026-03-08
**Assigned Sprint**: Sprint 18

## Description

Elevate `/stoic` from a structured questionnaire into a science-backed journaling system that builds emotional intelligence, resilience, and self-awareness over time — on par with best-in-class tools like Day One, Reflectly, and the Five Minute Journal, but integrated with Joplin and powered by AI.

## Science Foundation

### 1. Affect Labeling (Lieberman et al., 2007 — UCLA)
Naming emotions with granularity reduces amygdala reactivity and improves regulation. Coarse labeling ("bad day") is far less effective than precise labeling ("frustrated because my effort wasn't acknowledged"). Add a **mood check-in with granular emotion vocabulary** at session start. Research: *Lieberman, M. D. et al. (2007). Putting feelings into words. Psychological Science.*

### 2. Implementation Intentions (Gollwitzer, 1999)
"What is your #1 priority?" has ~50% follow-through. "If [situation], then I will [response]" if-then planning has 2–3× higher completion rates. Replace or augment priority questions with structured if-then prompts for high-stakes items. Research: *Gollwitzer, P. M. (1999). Implementation intentions. American Psychologist.*

### 3. Negative Visualization / Premeditatio Malorum (Stoic philosophy; Ryan Holiday, Marcus Aurelius)
The existing "What obstacle might arise?" is a weak version. True premeditatio malorum asks the user to vividly imagine worst-case scenarios, feel the loss, then return to gratitude for what exists. This inoculates against hedonic adaptation and builds resilience.

### 4. Gratitude Specificity (Emmons & McCullough, 2003)
"What are you grateful for?" produces weak results when answered generically. Specific, concrete gratitude targeting *who* helped, *why* it mattered, and *what it would be like without it* significantly amplifies benefit. Research: *Emmons, R. A., & McCullough, M. E. (2003). Counting blessings vs. burdens. Journal of Personality and Social Psychology.*

### 5. Self-Compassion (Neff, 2003)
Current evening questions jump from "What went wrong?" to correction. Research shows this creates perfectionism loops. Self-compassion — acknowledging failure with the same kindness you'd give a friend — is strongly correlated with resilience, motivation, and well-being. Research: *Neff, K. D. (2003). Self-compassion. Self and Identity.*

### 6. Expressive Writing & Pattern Recognition (Pennebaker, 1997)
Single-entry reflection has modest benefits. The large effect sizes in Pennebaker's research come from writing across multiple sessions and reviewing for patterns. Weekly AI synthesis of the user's journal ("What patterns appeared this week?") amplifies the benefit dramatically. Research: *Pennebaker, J. W. (1997). Writing about emotional experiences. Psychological Science.*

### 7. Somatic Awareness (van der Kolk, 2014)
Cognitive reflection disconnected from body state misses important signals. A brief body/energy check-in ("Where do you feel today's stress in your body? What's your energy: 1–5?") grounds the session in physical reality, which is especially valuable for detecting burnout early. Research: *van der Kolk, B. (2014). The Body Keeps the Score.*

### 8. Habit Architecture & Streaks (BJ Fogg, 2019; Clear, 2018)
Journaling benefits compound over time, but only if the habit sticks. Streak tracking, gentle nudges if no entry exists by evening, and a "minimum viable entry" path (one question, 30 seconds) ensure the chain doesn't break during busy days. Research: *Fogg, B. J. (2019). Tiny Habits; Clear, J. (2018). Atomic Habits.*

### 9. Question Variety (Habit Fatigue, Csikszentmihalyi Flow Theory)
Fixed questions produce rote answers within weeks. A rotating question bank — surfacing different but thematically consistent questions — maintains cognitive engagement and prevents automatic, low-quality responses. The flow state requires appropriate challenge.

### 10. Philosophical Priming (Stoic tradition — Aurelius, Seneca, Epictetus)
Starting each session with a relevant Stoic quote primes the reflective mindset. Research on mental contrasting shows that priming with values improves subsequent reflection quality (Oettingen, 2014).

## Current State (Baseline)

- **Morning**: 7 fixed questions (professional/personal objective, obstacle, greater goals, 3 priorities)
- **Evening**: 8 fixed questions (priorities review, wins, what went wrong, control, progress, gratitude, tomorrow task)
- **Save**: Structured Markdown note in Joplin, tags, optional Google Task for tomorrow
- **AI**: LLM formats the reflection prose; no AI-generated insight
- **No**: mood tracking, streak, question rotation, weekly synthesis, self-compassion, priming quotes, body check-in, pattern analysis

## Key Files

| File | Purpose |
|------|---------|
| `src/handlers/stoic.py` | Core handler, all commands |
| `src/prompts/stoic_journal_template.md` | Question bank + note template |
| `src/state_manager.py` | Session + user preferences |
| `src/llm_orchestrator.py` | Add: format_stoic_reflection, generate_stoic_insight |
| `tests/test_stoic.py` | New test file |

## User Story

As a user who journals with /stoic daily,
I want a science-backed journaling experience that adapts to my mood, rotates questions to prevent rote answers, surfaces weekly AI-generated insights from my entries, and builds long-term self-awareness,
so that my daily reflection practice compounds into genuine growth rather than a checkbox habit.

**Tips**:
- Start with user role
- Use action verbs (filter, create, delete, view)
- Focus on value, not implementation
- Be specific about the benefit

**Examples**:
- As a registered user, I want to filter search results by date, so that I can quickly find recent items.
- As an admin, I want to export user data to CSV, so that I can generate reports.
- As a mobile app user, I want to save items offline, so that I can access them without internet.

## Acceptance Criteria

- [ ] ### Core (Must Have)
- [ ] #### AC-1: Mood & Energy Check-in at Session Start
- [ ] - [ ] Morning and evening sessions open with a mood check-in: "How are you feeling right now? (e.g. energized, anxious, hopeful, frustrated, calm)" — free text, not multiple choice
- [ ] - [ ] Energy level prompt: "Energy today: 1 (exhausted) → 5 (peak)" — single digit reply accepted
- [ ] - [ ] Mood + energy stored in state and persisted in the note under a `## Check-in` section
- [ ] - [ ] Longitudinal data queryable: 30-day mood/energy averages available in `/stoic stats`
- [ ] #### AC-2: Gratitude with Specificity Prompting
- [ ] - [ ] Evening gratitude question upgraded to: "What are you genuinely grateful for today? Name something specific — who was involved, why it matters, and what life would look like without it."
- [ ] - [ ] If user gives a generic answer (< 10 words), bot responds with a gentle follow-up: "Can you say more about why that matters to you?"
- [ ] - [ ] Follow-up fires at most once per session (not a loop)
- [ ] #### AC-3: Self-Compassion on Failure Reflection
- [ ] - [ ] After "What went wrong / what will you correct?", add: "If a close friend told you this happened to them, what would you say to comfort them?"
- [ ] - [ ] This question appears only in the evening session
- [ ] - [ ] Answer stored under `**Self-Compassion:**` in the note
- [ ] #### AC-4: Question Rotation (Morning & Evening)
- [ ] - [ ] `stoic_journal_template.md` expanded to include at least 3 alternate question variants per slot
- [ ] - [ ] Bot selects questions pseudo-randomly per session (seeded by date so the same day always gives the same questions; not random between two /stoic starts on the same day)
- [ ] - [ ] Core structure (check-in → objective → obstacle → priorities for morning; priorities review → wins → wrong → compassion → control → gratitude → tomorrow for evening) preserved regardless of variant
- [ ] #### AC-5: Stoic Quote Priming
- [ ] - [ ] Each session opens with a Stoic quote before the first question
- [ ] - [ ] Quote is relevant to the time of day (morning: action/courage; evening: reflection/acceptance)
- [ ] - [ ] Minimum 20 quotes per time-of-day in a static bank in `stoic_journal_template.md` or a separate `stoic_quotes.md`
- [ ] - [ ] Quote rotates daily (not randomly mid-day)
- [ ] #### AC-6: Weekly AI Insight Synthesis — `/stoic review`
- [ ] - [ ] `/stoic review` command fetches last 7 days of Stoic Journal notes from Joplin
- [ ] - [ ] LLM generates a 150–300 word synthesis: dominant themes, emotional patterns, wins, growth edges, and one Stoic principle that applies to the week
- [ ] - [ ] Synthesis saved as a note `YYYY-WW - Weekly Stoic Review` in the same Joplin folder
- [ ] - [ ] If fewer than 3 entries exist for the week, bot responds: "You have X entries this week. A review works best with 3+. Add more entries first."
- [ ] #### AC-7: Streak Tracking
- [ ] - [ ] Bot tracks journaling streak (consecutive days with at least one /stoic entry) in `user_preferences`
- [ ] - [ ] Streak shown after saving: "🔥 Day 5 streak! Consistency is the foundation of growth."
- [ ] - [ ] If user completes both morning AND evening: "✨ Full day — morning + evening complete."
- [ ] - [ ] If no entry exists by 20:00 user local time, send a single gentle nudge (not more than once/day): "No Stoic entry yet today. Even one question counts. /stoic"
- [ ] #### AC-8: Minimum Viable Entry — `/stoic quick`
- [ ] - [ ] `/stoic quick` asks only 3 questions total (1 morning: "What's your intention today?" + mood; 1 evening: "One win today?" + gratitude)
- [ ] - [ ] Same save/note behavior as full session
- [ ] - [ ] Streak counted the same as full session
- [ ] - [ ] `quick` mode noted in the note header so it's distinguishable from a full session
- [ ] ### Optional (Nice to Have)
- [ ] #### AC-9: Body Check-in (somatic)
- [ ] - [ ] Optional follow-up after mood: "Where do you feel today's stress or energy in your body? (e.g. tight shoulders, restless, settled)" — skippable with "skip"
- [ ] - [ ] Answer stored under `**Body:**` in the note
- [ ] #### AC-10: Implementation Intentions for Top Priority
- [ ] - [ ] After "What is your #1 priority?", bot prompts: "If you hit resistance or distraction, what will you do? (e.g. 'If I feel like checking email, I'll do 10 min of work first')"
- [ ] - [ ] Skippable; stored under the priority if answered
- [ ] #### AC-11: Premeditatio Malorum Enhancement
- [ ] - [ ] Existing obstacle question deepened: "Vividly imagine this obstacle derailing today. What's the worst outcome? Now — what specifically will you do if it happens?"
- [ ] - [ ] Two-part answer (worst case + response plan) stored together
- [ ] #### AC-12: `/stoic stats` — 30-day Dashboard
- [ ] - [ ] Shows: current streak, longest streak, total entries this month, average morning energy (1–5), most common mood words (word frequency), days with both morning + evening
- [ ] - [ ] Rendered as a Telegram message (not a file)

**Tips for Good Acceptance Criteria**:
- Be specific and testable
- Use measurable outcomes
- Include edge cases if relevant
- Cover both happy path and error scenarios

## Business Value

[Why this user story is important and what problem it solves. Include user impact and business benefits.]

Examples:
- Improves user experience by reducing steps from 5 to 2
- Increases user engagement by enabling key workflow
- Reduces support tickets by 30%
- Enables new revenue stream

## Technical Requirements

[Technical implementation details and requirements. Include any constraints, performance requirements, or technical considerations.]

Examples:
- Must support 1000+ concurrent users
- Response time < 200ms
- Requires database migration
- Must be backward compatible
- API rate limits: 1000 requests/hour

## Reference Documents

- [Document Name 1] - [Section/Page/Section Name]
- [Document Name 2] - [Section/Page/Section Name]

**Examples**:
- Architecture documentation - Design section
- UI/UX wireframes - Mockups
- API documentation - Endpoint specifications
- Requirements document - Requirements

## Technical References

[Links to specific code locations, classes, or technical specifications. Adapt format to your tech stack.]

**Format examples**:
- Handler: `src/handlers/stoic.py` — `_format_morning_content()`, `_finish_stoic_session()`
- Service: `src/task_service.py` — `create_task_with_metadata()`
- Client: `src/joplin_client.py` — `get_note()`, `update_note()`
- Tests: `tests/test_stoic_sprint18.py`

## Dependencies

- - US-019: Stoic Journal (baseline implementation) ✅
- - US-007: Conversation State Management ✅
- - US-042: Stoic "What I Learned Today" (related; may overlap with question bank)
- - US-005: Joplin REST API Client ✅ (needed for /stoic review note fetch)

Examples:
- Authentication system must be implemented
- Database schema migration must be deployed
- External API integration must be completed
- User story X must be merged first

## Clarifying Questions

*AI: Before starting implementation, ask the user clarifying questions. Document questions and answers here after the user responds.*

- **Q**: [Question 1]
- **A**: [User answer]
- **Date**: 2026-03-08

## Notes

[Additional notes, considerations, context, or open questions.]

Examples:
- This is a critical user story for MVP
- Alternative approach discussed but rejected because...
- User research shows high demand for this capability
- Technical spike needed to evaluate performance impact

## Acceptance Verification

**Complete before marking status as Done.** Verify each acceptance criterion is met, then mark with `[x]`.

- [ ] All acceptance criteria above verified as met
- [ ] Each criterion tested or inspected and confirmed

## History

- 2026-03-08 - Created
- 2026-03-08 - Status changed to ⏳ In Progress
- 2026-03-08 - Assigned to Sprint 13
- 2026-03-08 - Status changed to ✅ Done

---

## Status Values

- ⭕ **To Do**: Item not yet started
- ⏳ **In Progress**: Item currently being worked on
- ✅ **Done**: Item finished and verified

## Priority Levels

- 🔴 **Critical**: Blocks core functionality, must be fixed immediately
- 🟠 **High**: Important feature/defect, should be addressed soon
- 🟡 **Medium**: Nice to have, can wait
- 🟢 **Low**: Future consideration, low priority

## Story Points Guide (Fibonacci)

- **1 Point**: Trivial task, < 1 hour
- **2 Points**: Simple task, 1-4 hours
- **3 Points**: Small task, 4-8 hours
- **5 Points**: Medium task, 1-2 days
- **8 Points**: Large task, 2-3 days
- **13 Points**: Very large task, 3-5 days (consider breaking down)

---

## Template Validation Checklist

Before submitting, ensure:

- [ ] All required fields are filled (Status, Priority, Story Points, Dates)
- [ ] User story follows "As a... I want... So that..." format
- [ ] At least 3 acceptance criteria are defined
- [ ] Acceptance criteria are specific and testable
- [ ] Business value is clearly documented
- [ ] Technical requirements are specified (if applicable)
- [ ] Dependencies are identified (if any)
- [ ] Story points are estimated using Fibonacci sequence
- [ ] Priority is assigned based on business value and urgency
- [ ] Technical references are included (if applicable)
- [ ] Links to related documents are correct
- [ ] File is saved with correct naming convention: `US-XXX-story-name.md`
- [ ] Entry is added to product backlog table
