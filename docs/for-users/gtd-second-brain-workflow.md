# GTD + Second Brain: The Complete Workflow

How to use **Getting Things Done** (Google Tasks) and your **Second Brain** (Joplin) together through the Telegram bot to capture, organize, and act on everything in your life.

---

## The Core Principle

**GTD and Second Brain solve different problems.**

| System | Purpose | Tool | Answers |
|--------|---------|------|---------|
| **GTD** | Manage *actions* — what you need to **do** | Google Tasks | "What's my next step?" |
| **Second Brain** | Manage *knowledge* — what you need to **know** | Joplin (PARA) | "What do I know about this?" |

Think of it this way:

- **Google Tasks** is your *to-do list* — short, actionable, verb-first items with deadlines.
- **Joplin** is your *brain extension* — notes, research, plans, references, and everything you want to remember.

They work together: tasks point you to action, notes give you the context to act.

---

## The Two-Minute Rule for Capture

When something enters your world, ask:

```
1. Is it actionable?
   → YES: Does it take less than 2 minutes?
       → YES: Do it now.
       → NO:  Create a Google Task (and optionally a note for context).
   → NO:  Is it useful knowledge or reference?
       → YES: Create a Joplin note.
       → NO:  Let it go.
```

The bot handles this naturally. Send a message, and the AI decides:

- **Action-oriented** language ("call", "email", "schedule", "follow up", "buy") → **Google Task**
- **Knowledge-oriented** language ("notes on", "idea about", "recipe for", "article about") → **Joplin note**
- **Both** ("Meeting notes with action items") → **Joplin note** + extracted **Google Tasks**

---

## Where Things Live: The Complete Map

### Google Tasks (GTD)

| What goes here | Examples |
|---------------|----------|
| Next actions | "Call the dentist to book cleaning" |
| Waiting-for items | "Waiting for John to send contract" |
| Errands | "Buy guitar strings at Long & McQuade" |
| Deadlines | "Submit tax return by April 30" |
| Follow-ups | "Follow up with Sarah about project proposal" |
| Reminders | "Remind: renew passport before June" |

**Tasks are verb-first, specific, and completable.** You can check them off.

### Joplin (Second Brain — PARA)

| PARA Bucket | What goes here | Examples |
|-------------|---------------|----------|
| **Inbox** | Quick captures before processing | Raw brain dumps, quick thoughts |
| **Projects** | Active goals with a deadline or outcome | "Learn to Sing Harmonies", "Renovate Kitchen" |
| **Areas** | Ongoing responsibilities (no end date) | Health, Finance, Work, Journaling |
| **Resources** | Reference material for later | Book notes, recipes, how-tos, cheat sheets |
| **Archive** | Completed or inactive items | Finished projects, old references |

---

## Anatomy of a Project: GTD + Second Brain Together

Every meaningful project exists in **both** systems:

```
Google Tasks                          Joplin (PARA)
─────────────                         ──────────────
☐ Next action 1                       Projects/
☐ Next action 2                         └── My Project/
☐ Next action 3                              ├── Overview (goals, vision, success criteria)
☐ Waiting for X                              ├── Research & Notes
                                             ├── Decisions & Logs
                                             └── Reference Materials
```

- **Google Tasks** = the *engine* (what moves the project forward)
- **Joplin Project folder** = the *cockpit* (where you see the big picture, store research, track decisions)

---

## Full Walkthrough: "Learn to Sing Harmonies"

Let's walk through a real personal project from first thought to completion.

### Step 1: Capture the Idea

You're listening to music and think: "I'd love to learn how to sing harmonies."

**Send to the bot:**

> I want to start a personal project to learn how to sing harmonies. I've always wanted to harmonize with songs and other singers but I don't know where to start.

**What happens:**

- **Joplin** → A note is created in `Projects/Learn to Sing Harmonies/` with title like "Learn to Sing Harmonies — Overview"
- **Tags** → `music`, `learning`, `status/planning`
- **Google Tasks** → The bot might extract: "Research beginner harmony singing resources"

### Step 2: Braindump Everything You Know

Use `/braindump` to empty your brain about this project.

**Bot asks:** "What's been on your mind about this?"

**You say things like:**
> I can sing melody fine but I always lose the harmony when the melody gets loud. I think I need to train my ear first. Maybe I should start with simple intervals. I heard about an app called Functional Ear Trainer. My friend Mike sings in a barbershop quartet, I should ask him for tips. I wonder if I need a vocal coach or if YouTube is enough to start.

**What the bot creates:**

**Joplin note** (in Inbox/Brain Dump):

> **Brain Dump — Learn to Sing Harmonies**
>
> - Can sing melody but loses harmony when melody is loud
> - Needs ear training first — start with intervals
> - App: Functional Ear Trainer
> - Friend Mike — barbershop quartet, ask for tips
> - Question: vocal coach vs YouTube for starting out

**Google Tasks** (extracted automatically):

| Task |
|------|
| ☐ Download and try Functional Ear Trainer app |
| ☐ Text Mike about harmony singing tips |
| ☐ Research vocal coaches vs YouTube for learning harmony |

### Step 3: Organize Into PARA

Now process what you captured. Here's where everything lands:

#### Joplin — Project Folder Structure

```
Projects/
  └── Learn to Sing Harmonies/
        ├── Overview
        ├── Research Notes
        ├── Practice Log
        └── Resources & Links
```

**Overview note** — the project's "home base":

```markdown
# Learn to Sing Harmonies

## Goal
Be able to sing a harmony part confidently along with songs and with other singers.

## Success Criteria
- [ ] Sing a 3rds harmony over a simple melody
- [ ] Harmonize with a song in real-time
- [ ] Sing a duet part from sheet music

## Current Status
Planning — gathering resources and building a practice plan.

## Key Decisions
- Start with ear training before attempting harmony
- Begin with YouTube/apps, revisit vocal coach after 1 month

## Timeline
- Aim: 3 months to basic competency
```

**Research Notes** — what you learn along the way:

```markdown
# Harmony Singing Research

## From Mike (barbershop tips)
- Start by learning to hear the bass note in any chord
- Practice singing 3rds above a drone note
- Barbershop uses "lock and ring" — when harmonies are perfect you hear overtones
- Recommended: "The Barbershop Tenor" channel on YouTube

## From YouTube research
- Interval training is foundational (2nds, 3rds, 5ths)
- Sing scales in 3rds with a piano
- Record yourself and listen back
- Start with songs that have obvious harmony (Simon & Garfunkel, Everly Brothers)

## Apps & Tools
- Functional Ear Trainer (free, great for intervals)
- SingSharp (pitch accuracy feedback)
- Musictheory.net (intervals lesson)
```

**Practice Log** — ongoing journal of sessions:

```markdown
# Practice Log

## Week 1 (March 3–9)
- Mon: 15 min Functional Ear Trainer — 70% accuracy on 3rds
- Wed: Tried singing 3rds over "Let It Be" — lost it at the chorus
- Fri: Sang along with Everly Brothers "All I Have to Do is Dream" — easier!

## Week 2 (March 10–16)
- Tue: Ear trainer up to 85% on 3rds, started 5ths
- Thu: Recorded myself harmonizing — pitch is close but inconsistent
```

**Resources & Links**:

```markdown
# Harmony Singing Resources

## YouTube Channels
- [The Barbershop Tenor](https://youtube.com/...)
- [Jacob Collier harmony explanation](https://youtube.com/...)

## Articles
- "How to Sing Harmony: A Beginner's Guide" — musicianwave.com

## Books
- "Harmony and Voice Leading" by Aldwell (advanced, for later)

## Apps
- Functional Ear Trainer (iOS/Android)
- SingSharp
```

#### Google Tasks — The Action List

These are the *only things in Google Tasks* — concrete next actions:

| Task | Status |
|------|--------|
| ☐ Download Functional Ear Trainer app | |
| ☐ Text Mike about harmony tips | |
| ☐ Watch 3 beginner harmony YouTube videos and take notes | |
| ☐ Buy a simple keyboard/piano app for practice | |
| ☐ Set up 15-min daily ear training habit | |
| ☐ Try singing harmony on "All I Have to Do Is Dream" | |
| ☐ Record first harmony attempt and review | |
| ☐ Research local vocal coaches (after 1 month) | |

Notice: **Tasks are actions. Notes are knowledge.** The task says *what to do*. The note in Joplin says *what you learned when you did it*.

### Step 4: The Weekly Review Cycle

Each week, review both systems:

**Google Tasks:**
- What did I complete? Check them off.
- What's my next action? Make sure there's always at least one.
- Anything waiting on someone else? Mark as waiting.

**Joplin:**
- Update the Practice Log with this week's sessions.
- Add any new research to Research Notes.
- Update the Overview note's status and decisions.
- Move the project status tag (`status/planning` → `status/building`).

### Step 5: Project Completion

After 3 months, you can confidently sing harmonies.

**Google Tasks:** All tasks checked off. No more next actions needed.

**Joplin:**
- Update Overview: mark goal as achieved, add reflection.
- Move project folder to `Archive/Learn to Sing Harmonies/`.
- Keep the Research Notes and Resources — they're still valuable reference.
- Tag with `status/done`.

---

## More Examples: GTD + Second Brain Split

### Example: Planning a Vacation to Japan

**Google Tasks (actions):**

| Task |
|------|
| ☐ Check passport expiration date |
| ☐ Research flights Tokyo for October |
| ☐ Ask coworker Yuki for restaurant recommendations |
| ☐ Book Airbnb in Kyoto for Oct 10–14 |
| ☐ Buy Japan Rail Pass online |
| ☐ Download Google Translate offline Japanese |

**Joplin (knowledge):**

```
Projects/
  └── Japan Vacation October/
        ├── Overview (dates, budget, goals)
        ├── Itinerary Draft
        ├── Restaurant & Food List
        ├── Packing List
        └── Travel Tips & Phrases
```

### Example: Renovate the Home Office

**Google Tasks:**

| Task |
|------|
| ☐ Measure office dimensions |
| ☐ Browse IKEA for standing desk options |
| ☐ Get 3 quotes from painters |
| ☐ Order cable management kit from Amazon |
| ☐ Schedule painter for weekend of April 12 |

**Joplin:**

```
Projects/
  └── Home Office Renovation/
        ├── Overview (budget: $2000, deadline: end of April)
        ├── Inspiration & Ideas (photos, Pinterest saves)
        ├── Measurements & Floor Plan
        ├── Product Research (desk comparisons, monitor arm reviews)
        └── Receipts & Costs
```

### Example: Learn a New Programming Framework (Laravel)

**Google Tasks:**

| Task |
|------|
| ☐ Install Laravel and create hello-world app |
| ☐ Complete Laracasts "Laravel from Scratch" episodes 1–10 |
| ☐ Build a simple CRUD app for practice |
| ☐ Read Laravel docs on Eloquent ORM |
| ☐ Deploy practice app to Forge |

**Joplin:**

```
Projects/
  └── Learn Laravel/
        ├── Overview (goal: build a side project in Laravel by June)
        ├── Course Notes — Laracasts
        ├── Cheat Sheet (routes, migrations, Eloquent syntax)
        ├── Project Ideas
        └── Gotchas & Troubleshooting
```

When complete, the course notes and cheat sheet move to `Resources/Reference/Laravel/` — they become permanent reference material.

### Example: Ongoing Health (Area, not a Project)

Health doesn't have a deadline, so it's an **Area**, not a Project.

**Google Tasks (only when there's a specific action):**

| Task |
|------|
| ☐ Book annual physical with Dr. Chen |
| ☐ Refill vitamin D prescription |
| ☐ Research gym memberships near office |

**Joplin:**

```
Areas/
  └── Health & Fitness/
        ├── Workout Routine (current program)
        ├── Supplements & Medications
        ├── Doctor Visit Notes
        └── Health Goals 2026
```

No task list for "be healthy" — that's an *area*. Tasks only appear when there's a concrete next action.

---

## Using Bot Commands in the Workflow

### Capture Phase

| What you want to do | How |
|---------------------|-----|
| Quick thought or idea | Send a message → bot creates a note |
| Explicit task | `/task Buy guitar strings` → Google Task only |
| Full brain dump | `/braindump` → guided capture → note + tasks |
| Save a URL | Paste a link → bot fetches, summarizes, creates note |

### Organize Phase

| What you want to do | How |
|---------------------|-----|
| Reorganize into PARA | `/reorg_init` → `/reorg_preview` → `/reorg_execute` |
| Enrich notes with metadata | `/enrich_notes` → adds status, priority, summary |
| Check project status | `/project_status` → see counts by status tag |

### Review Phase

| What you want to do | How |
|---------------------|-----|
| Daily priorities | `/daily_report` or configure auto-report |
| See what's active | `/project_status` |
| Weekly reflection | `/stoic evening` for reflective journaling |

---

## Decision Framework: Task or Note?

When you're unsure where something goes, use this quick test:

```
Can I check it off when it's done?
  → YES → Google Task
  → NO  → Joplin Note

Will I need this information again in a week?
  → YES → Joplin Note
  → NO  → Maybe just a task is enough

Is it a single action or a body of knowledge?
  → Single action → Google Task
  → Body of knowledge → Joplin Note
  → Both → Joplin Note + Google Task(s) extracted from it
```

### The Overlap Zone

Sometimes things live in both places. That's not only fine — it's the design:

| Scenario | Google Task | Joplin Note |
|----------|------------|-------------|
| "Research harmony singing" | ☐ Watch 3 YouTube videos on harmony | Research Notes with what you learned |
| "Call the plumber" | ☐ Call ABC Plumbing at 555-1234 | (no note needed — action only) |
| "Meeting with client" | ☐ Prepare slides for Thursday meeting | Meeting Notes with decisions, action items |
| "Read Atomic Habits" | ☐ Read chapters 1–4 this week | Book notes with highlights and takeaways |
| "Interesting article on AI" | (no task — reference only) | Resources/Books & Articles note |

---

## The Golden Rules

1. **Capture everything.** Don't trust your brain. Send it to the bot.
2. **Tasks are verbs.** Every Google Task starts with an action verb: call, buy, email, research, build, write, schedule.
3. **Notes are nouns.** Every Joplin note is about a *thing*: a project overview, research findings, a recipe, a decision log.
4. **One next action.** Every active project should have at least one task in Google Tasks. If it doesn't, it's stalled.
5. **Review weekly.** Spend 15 minutes updating both systems. The `/braindump` and `/daily_report` commands help.
6. **Archive, don't delete.** When a project is done, move it to Archive. Your future self will thank you.
7. **Trust the system.** The whole point is to stop carrying things in your head. If it's captured, you can let it go.

---

## Quick Reference: Common Scenarios

| Life event | Send to bot | Result |
|-----------|-------------|--------|
| "I need to renew my passport" | `I need to renew my passport before it expires in June` | Task: "Renew passport before June" |
| "Great article on productivity" | Paste the URL | Note in Resources with summary |
| "Meeting notes from standup" | `Standup notes: decided to prioritize the auth bug, John will handle deploy, need to update docs by Friday` | Note in Projects + Tasks: "Update docs by Friday" |
| "Random idea at 2am" | `Idea: what if the app could also track habits` | Note in Inbox for later processing |
| "Recipe from a friend" | `Mike's BBQ rub recipe: 2 tbsp paprika, 1 tbsp brown sugar...` | Note in Resources/🍽️ Recipe |
| "I'm overwhelmed" | `/braindump` | Guided session → Note + extracted tasks |
| "Need to call mom" | `/task Call mom about Sunday dinner` | Task only — no note needed |
| "Book highlights" | `Notes from Atomic Habits chapter 3: habit stacking means...` | Note in Resources/Books & Articles |
