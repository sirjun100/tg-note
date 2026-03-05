# Brain Dump Prompt Tuning Guide

**For:** LLMs tuning the GTD expert persona for better session quality
**Target Files:** `src/prompts/gtd_expert.txt`, `src/llm_orchestrator.py`
**Goal:** Achieve high-quality brain dumps in ~15 minutes with good question pacing

---

## Table of Contents

1. [Current Prompt Structure](#current-prompt-structure)
2. [Prompt Design Principles](#prompt-design-principles)
3. [Session Phases Deep Dive](#session-phases-deep-dive)
4. [Tuning Techniques](#tuning-techniques)
5. [Response Format Constraints](#response-format-constraints)
6. [Testing & Iteration](#testing--iteration)
7. [Common Issues & Fixes](#common-issues--fixes)

---

## Current Prompt Structure

**File:** `src/prompts/gtd_expert.txt`

The prompt is **not** a simple instruction list; it's a **persona definition** that the LLM internalizes and applies autonomously throughout the conversation.

```
[Role Definition]
    ↓
[Flow & Pacing Rules]
    ↓
[Session Structure (3 Phases)]
    ↓
[Response Format (JSON Schema)]
    ↓
[Ending Behavior]
    ↓
[First Question]
```

**Key Insight:** The prompt sets the LLM up to **self-govern** the session without explicit turn limits. The LLM decides when to ask for clarification, when to move to the next phase, and when to finalize.

---

## Prompt Design Principles

### 1. **Be Prescriptive About Behavior, Not Structure**

❌ **BAD:** "Ask 10 questions about work, then 8 about home, then 5 about health..."
- Rigid, repetitive, predictable
- Forces artificial boundaries

✅ **GOOD:** "Focus on the Quick Sweep phase (8-10 min). Guide the user through work, home, paperwork, health, projects."
- LLM decides pacing within the phase
- Feels conversational, not formulaic

---

### 2. **Use Role & Energy Over Explicit Instructions**

❌ **BAD:** "When the user says nothing, acknowledge briefly and MOVE ON IMMEDIATELY."
- Tells, doesn't inspire

✅ **GOOD:** "You are like a good coach who keeps things moving without being pushy. Your energy is warm and brisk."
- The LLM internalizes the persona
- Behaviors flow naturally from the role

---

### 3. **Highlight What NOT To Do**

The prompt explicitly tells the LLM:
- "You are NOT a therapist" (don't analyze or provide advice)
- "Focus only on CAPTURE" (don't organize or prioritize)
- "Don't editorialize, prioritize, or add next actions" (stay neutral)

This constrains the LLM's tendency to over-solve.

---

### 4. **Response Format is JSON, Not Prose**

The LLM is instructed to **always return structured JSON**, even when asking a simple question:

```json
{
  "status": "NEED_INFO",
  "confidence_score": 1.0,
  "question": "Got it. What else is feeling urgent or overdue?",
  "log_entry": "In Pressure Release phase, moving to third item",
  "note": null
}
```

This ensures **parsing reliability** in the code layer.

---

## Session Phases Deep Dive

### Phase 1: Pressure Release (2-3 min)

**Goal:** Identify the most stressful/urgent items first

**Questions to Ask:**
1. "What is the thing that has been poking at you the most lately?"
2. "What's almost overdue or overdue right now?"
3. "What's taking up mental energy?"

**Why This Order:**
- Emotional relief first (lower stress, helps user think clearly)
- Sets tone as empathetic, not clinical
- Gets the urgent stuff captured early

**Prompt Guidance:**
> "Ask ONLY ONE short, punchy question at a time."
> "Briefly acknowledge the user's input before moving on (Got it, Noted, On the list)."

**LLM Behavior:** Should wrap up in 2-3 turns, then move to Quick Sweep.

---

### Phase 2: Quick Sweep (8-10 min)

**Goal:** Systematically capture from different life areas

**Categories (in order):**
1. Work tasks and projects
2. Commitments to other people
3. Waiting-fors (things from others)
4. Home and household
5. Errands
6. **Paperwork** (SPEND EXTRA TIME HERE)
7. Finances and money stuff
8. Health and appointments
9. Personal projects or ideas

**Why Paperwork Gets Special Attention:**
> "Users tend to forget about paperwork (taxes, lease renewals, contracts, etc.)."

The prompt tells the LLM to be **specific and thorough** here:
- Ask about renewals
- Ask about official documents
- Ask about anything with a deadline and a signature

**Prompt Guidance:**
```
Ask specific sub-questions within each category:
- Paperwork: "Any tax or legal stuff? Renewing licenses, contracts?"
- Finances: "Bills due? Investment decisions? Insurance reviews?"
- Health: "Appointments needed? Prescriptions? Checkups?"
```

**LLM Behavior:** Should spend 8-10 min going through categories, adapting questions based on user responses.

---

### Phase 3: Stragglers (2-3 min)

**Goal:** Give user final chance to remember anything

**Questions:**
- "What else?"
- "Anything we missed?"
- "What was I forgetting?"

**Prompt Guidance:**
> "Give the user a final chance to add more before wrapping."

**LLM Behavior:** Should ask open-ended questions to catch last-minute items, then signal readiness to end.

---

## Tuning Techniques

### 1. **Adjust Phase Timing**

Current: 2-3 min pressure + 8-10 min sweep + 2-3 min stragglers = ~15 min total

**If sessions are too short:**
- Expand Quick Sweep categories ("Add personal relationships, spiritual/philosophical items")
- Add more sub-questions per category ("Any issues with family? Friends? Colleagues?")
- Increase the depth of follow-ups

**If sessions are too long:**
- Reduce categories (combine Errands + Home)
- Use more concise follow-ups
- Move to stragglers faster

### 2. **Improve Category Coverage**

Add new categories if users frequently mention them:
- **Relationships:** family, friends, romantic partner
- **Learning:** courses, books, skills to develop
- **Hobbies:** projects, creative endeavors
- **Car/Travel:** maintenance, trips planned

Add to "Quick Sweep" section:
```
- Relationships and personal connections.
- Learning and skill development.
- Hobbies and creative projects.
- Car maintenance and travel planning.
```

### 3. **Refine Paperwork Questions**

The prompt emphasizes paperwork, but the questions can be more specific:

Current:
> "Ask about renewals, official documents, and anything with a deadline and a signature."

Improved (more specific):
```
Paperwork sub-questions:
- "Any licenses or registrations that need renewing?"
- "Insurance policies to review or renew?"
- "Tax documents or receipts you need to organize?"
- "Contracts to sign or review?"
- "Official forms or applications pending?"
- "Warranty or guarantee information to file?"
```

### 4. **Adjust Tone & Energy**

Current: "Warm and brisk"

**If users say sessions feel rushed:**
- Change to: "Warm and unhurried"
- Add: "Take your time, no pressure"
- Reduce follow-ups per category

**If users say sessions feel stalled:**
- Change to: "Warm and brisk, keeping momentum"
- Add: "Let's move forward"
- Increase follow-ups, tighten questions

**If users say sessions feel too clinical:**
- Add human touches: "I hear you" instead of "Got it"
- Use more encouraging language: "Great catch" instead of "Noted"
- Add: "How are you feeling now? Any lighter?"

### 5. **Control Confidence Score**

The LLM returns `confidence_score` (0.0 - 1.0) indicating certainty about completeness.

**Add guidance:**
```
Before deciding to finish (status="SUCCESS"):
- Use confidence_score to reflect how complete the brain dump feels
- If user is still engaged and thinking, keep status="NEED_INFO" even if 15 min has passed
- Only set status="SUCCESS" when:
  - User says "I think that's everything"
  - User repeats "I don't know" 3+ times in stragglers
  - You've covered all categories and user has nothing to add
```

### 6. **Handle User Tangents**

The prompt says:
> "If the user goes on a tangent or starts processing/organizing, gently redirect: 'Let's just capture that for now and keep moving.'"

**Enhance with examples:**

```
Examples of tangents to watch for:
1. User starts organizing: "Should I do this before that?"
   → "Let's just capture both and sort later."

2. User starts analyzing: "Why do I even need to do this?"
   → "Good question for later. For now, let's capture it."

3. User starts solving: "I could call them on Tuesday..."
   → "Got it, we'll capture 'Call them' and figure out when later."

4. User gets emotional: "I'm so stressed about this..."
   → "I hear you. Let's get it all out. What else is stressful?"
```

---

## Response Format Constraints

### JSON Schema

Every response must be valid JSON matching this schema:

```python
class JoplinNoteSchema(BaseModel):
    status: str  # "NEED_INFO" or "SUCCESS"
    confidence_score: float  # 0.0 - 1.0
    question: str | None  # Next question (required if NEED_INFO)
    log_entry: str  # Internal note about the phase/decision
    note: dict[str, Any] | None  # Final note (required if SUCCESS)
```

### During Session (status="NEED_INFO")

```json
{
  "status": "NEED_INFO",
  "confidence_score": 0.6,  // Still gathering info
  "question": "What else is on your plate at work?",
  "log_entry": "In Quick Sweep phase, Work category, item 3 of 4",
  "note": null  // Never include during session
}
```

### At Session End (status="SUCCESS")

```json
{
  "status": "SUCCESS",
  "confidence_score": 0.95,  // High confidence, comprehensive
  "question": null,  // No more questions
  "log_entry": "Session complete, compiled 23 items across 7 categories",
  "note": {
    "title": "Brain Dump - March 4, 2026",
    "body": "## Work\n- Email redesign\n- Q1 budget\n\n## Home\n- ...",
    "parent_id": "Inbox",
    "tags": ["brain-dump", "mindsweep"]
  }
}
```

### Note Body Format

The LLM compiles items into a structured note:

```markdown
## Work
- Email redesign meeting prep
- Review Q1 budget
- Follow up with client

## Home
- Schedule vet appointment for dog
- Buy groceries
- Fix leaky faucet

## Paperwork
- Renew car registration (expires June)
- Review insurance renewal
- File tax receipts

## Finances
- Review credit card bill
- Check 401k contribution

## Health
- Annual checkup needed
- Refill prescription

## Personal
- Learn Blender (3D modeling)
- Plan summer vacation
```

**Key Rules:**
- Use `##` headers for categories
- Use `-` for items (not numbers)
- Keep items concise (1 line each)
- Don't add priority, due dates, or implementation details
- Just capture what was said

---

## Testing & Iteration

### A/B Testing Framework

**Session Quality Metrics:**
1. **Comprehensiveness:** How many categories covered? (target: 7-9)
2. **Item Count:** Total items captured (target: 15-30)
3. **Session Duration:** Minutes taken (target: 12-18)
4. **User Satisfaction:** "Did this feel thorough?" (target: 4/5 or higher)
5. **Follow-up Completeness:** What % of items got done? (measure over 1 week)

**To A/B test a prompt change:**

1. Create variant: `src/prompts/gtd_expert_variant.txt`
2. Load variant for 50% of users
3. Log which prompt was used in decision record
4. Track metrics for both groups
5. Compare after 20+ sessions per variant
6. Keep the one with better scores

**Example Variant 1: Shorter Sessions**
```
Change:
- "approximately 15 minutes" → "approximately 10 minutes"
- Remove Paperwork emphasis
- Reduce Quick Sweep categories to 6

Expect:
- Faster sessions (9-12 min)
- Fewer items (12-20 items)
- Might miss important items
```

**Example Variant 2: Longer Sessions with More Detail**
```
Change:
- "approximately 15 minutes" → "approximately 20-25 minutes"
- Add follow-up questions per item ("What's blocking this?")
- Expand Paperwork section

Expect:
- Longer sessions (20-25 min)
- More items (30-40 items)
- Better action clarity
```

---

## Common Issues & Fixes

### Issue 1: LLM Keeps Asking the Same Question

**Symptom:**
```
Q: "What else at work?"
A: "Email redesign"
Q: "What else at work?"  ← Repeats instead of moving on
```

**Root Cause:** Prompt doesn't emphasize phase transitions clearly

**Fix:** Add explicit phase transition rules:
```
Phase Transitions:
- After 3-4 items in a category, move to next category (unless user adds more)
- If user says "Nothing else", move immediately
- Don't ask "What else?" more than 2x per category
```

### Issue 2: LLM Tries to Organize Instead of Capture

**Symptom:**
```
User: "I need to email my boss, update the spreadsheet, and call finance"
LLM: "So that's 3 work tasks. Should you do them in this order?"
```

**Root Cause:** LLM's default is to help solve; prompt needs stronger constraints

**Fix:** Make the "don't organize" rule more prominent:
```
CRITICAL:
- You are NOT organizing, prioritizing, or problem-solving
- You are ONLY capturing
- If the user proposes solutions, say: "Let's just capture that and keep moving"
- Do NOT ask "Do you want to tackle this first?" or similar
```

### Issue 3: Sessions End Too Early

**Symptom:** LLM finishes after 5 min with only 8 items captured

**Root Cause:** Prompt doesn't emphasize thoroughness

**Fix:** Add confidence thresholds:
```
Only set status="SUCCESS" when:
- User explicitly says "I think that's everything"
- You've asked about all 9 categories
- You've done at least 2 follow-up rounds
- confidence_score >= 0.85
```

### Issue 4: Sessions Run Too Long

**Symptom:** User gets frustrated after 30+ minutes

**Root Cause:** LLM doesn't know when to wrap up

**Fix:** Add time guidance:
```
You have approximately 15 minutes. Keep track:
- 0-3 min: Pressure Release (2-3 items)
- 3-11 min: Quick Sweep (15-25 items)
- 11-15 min: Stragglers and wrapping up

If more than 13 min has passed and you've covered all categories,
transition to stragglers even if user is still talking.
```

### Issue 5: Missing Important Categories

**Symptom:** User's brain dump never mentions finances; later they realize a bill is due

**Root Cause:** LLM skipped Finances category

**Fix:** Make categories more obvious and require explicit coverage:
```
REQUIRED Categories (you MUST ask about each):
1. Work tasks and projects
2. Commitments to others
3. Waiting-fors
4. Home and household
5. Errands
6. Paperwork (EXTRA THOROUGH)
7. Finances
8. Health and medical
9. Personal projects and learning

Don't move to "Done" until you've covered all 9.
```

### Issue 6: Note Title/Format Inconsistent

**Symptom:** Some notes are "Brain Dump - March 4" others are "My Brain Dump (Morning Session)"

**Root Cause:** LLM makes up titles

**Fix:** Mandate title format:
```
When setting status="SUCCESS":
- title: MUST be "Brain Dump - {DATE}" (use format: Month Day, Year)
  Example: "Brain Dump - March 4, 2026"
- tags: MUST include ["brain-dump", "mindsweep"]
- body: MUST use ## Category headers with - bullet points
```

### Issue 7: LLM Returns Text Instead of JSON

**Symptom:** Response is plain English, not JSON

**Root Cause:** LLM (especially Ollama) generates prose instead of structured output

**Fix:**
1. In prompt, use **bold** for critical requirement:
   ```
   **YOU MUST RESPOND IN STRUCTURED JSON FORMAT.**
   Even when asking the next question, wrap it in JSON.
   Do NOT respond in plain English.
   ```

2. Add example at bottom of prompt (already done)

3. In code, add fallback in llm_orchestrator.py (already done for personas):
   ```python
   # If JSON parsing fails but we have a persona, treat as conversational
   if persona:
       return JoplinNoteSchema(
           status="NEED_INFO",
           question=content_as_plain_text,
           ...
       )
   ```

---

## Prompt Maintenance Checklist

When updating the prompt:

- [ ] Test with 3-5 real users before deploying
- [ ] Check that all 9 categories are still mentioned
- [ ] Verify response format examples are valid JSON
- [ ] Ensure tone/role is consistent throughout
- [ ] Update this tuning guide if you change behavior
- [ ] Log all changes in `PROMPT_CHANGELOG.md`
- [ ] Keep old prompts in `src/prompts/gtd_expert_v*.txt` for A/B testing
- [ ] Monitor decision logs for completion rates on items captured

---

## Prompt Version History

```
gtd_expert.txt (Current)
├─ Last Updated: 2026-03-04
├─ 3 Phases (Pressure Release, Quick Sweep, Stragglers)
├─ 9 Categories in Quick Sweep
├─ Emphasis on Paperwork
├─ JSON response format
├─ Estimated 15 minute duration
└─ Status: Stable, in production

Proposed Variants:
├─ gtd_expert_quick.txt (10 min, 6 categories)
├─ gtd_expert_thorough.txt (25 min, 12 categories)
└─ gtd_expert_relationships.txt (adds personal relationships focus)
```

