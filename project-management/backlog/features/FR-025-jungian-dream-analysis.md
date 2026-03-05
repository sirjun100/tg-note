# Feature Request: FR-025 - Jungian Dream Analysis with Image Generation

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 8
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Sprint 11

## Description

Provide a guided dream analysis experience through Telegram using Jungian psychology principles. Users describe their dreams, and the bot generates a symbolic image representing the dream, provides a Jungian interpretation, and facilitates deeper exploration through life associations. The session is saved as a structured note in Joplin for future reference.

## User Story

As a user interested in self-discovery and dream work,
I want to describe my dreams and receive Jungian analysis with visual representation,
so that I can understand my unconscious mind and apply insights to my waking life.

## Acceptance Criteria

- [ ] `/dream` command starts a dream analysis session
- [ ] Bot prompts user to describe their dream in detail
- [ ] LLM generates a symbolic image representing the dream
- [ ] LLM provides Jungian interpretation of key symbols and themes
- [ ] Bot asks if user wants to explore life associations
- [ ] If yes, guided discussion connecting dream to current life issues/goals
- [ ] Session saved to Joplin with image, interpretation, and associations
- [ ] `/dream_done` ends session and saves the analysis
- [ ] `/dream_cancel` cancels without saving

## Business Value

Dreams are a powerful window into the unconscious mind. Jungian dream analysis helps users:
- Understand recurring patterns and symbols
- Process emotions and experiences
- Gain insights for personal growth
- Connect unconscious content to conscious goals

By combining AI interpretation with image generation, users get both intellectual understanding and visual anchoring of their dream content.

## Technical Requirements

### 1. Dream Analysis Flow

```
User: /dream
Bot: 🌙 Welcome to Dream Analysis

     Take a moment to recall your dream...

     When you're ready, describe everything you remember:
     - What happened?
     - Who was there?
     - What did you see, hear, feel?
     - Any symbols, colors, or unusual elements?

     Take your time. The more detail, the richer the analysis.

User: [Describes dream in detail]

Bot: 🎨 Creating a symbolic image of your dream...
     [Generates and sends image]

     📖 **Jungian Analysis**

     **Key Symbols:**
     • [Symbol 1] - [Interpretation]
     • [Symbol 2] - [Interpretation]

     **Archetypes Present:**
     • [Archetype] - [Meaning]

     **Shadow Elements:**
     • [Element] - [Significance]

     **Overall Theme:**
     [Interpretation paragraph]

     ---

     Would you like to explore how this dream connects
     to your current life? (yes/no)

User: yes

Bot: Let's connect this dream to your waking life...

     🔮 **Reflection Questions:**

     1. What current situation in your life feels similar
        to [dream element]?

     2. The [archetype] in your dream might represent
        [aspect]. Who or what in your life embodies this?

     3. The [symbol] often points to [meaning].
        Is there something you're avoiding or seeking?

     Take your time to reflect. Share what resonates.

User: [Shares associations]

Bot: [Deeper exploration and insights]
     ...

     When you're ready, type /dream_done to save this analysis.
```

### 2. Jungian Persona Prompt

Create `src/prompts/jungian_analyst.txt`:

```
You are a Jungian dream analyst, trained in the tradition of Carl Gustav Jung.
Your approach combines:

## Core Jungian Concepts

**The Unconscious**: Dreams are messages from the unconscious mind,
compensating for the one-sidedness of conscious attitudes.

**Archetypes**: Universal patterns in the collective unconscious:
- The Self: Wholeness, integration
- The Shadow: Rejected aspects of personality
- The Anima/Animus: Contrasexual soul-image
- The Persona: Social mask
- The Hero: Ego development, overcoming obstacles
- The Wise Old Man/Woman: Guidance, wisdom
- The Great Mother: Nurturing, devouring aspects
- The Trickster: Chaos, transformation
- The Child: New beginnings, potential

**Symbols**: Dreams speak in symbols, not literal meanings.
Common symbols and their typical meanings:
- Water: The unconscious, emotions
- Houses: The psyche, different rooms = different aspects
- Vehicles: How we move through life
- Animals: Instincts, shadow aspects
- Death: Transformation, ending of old patterns
- Flying: Liberation, transcendence
- Falling: Loss of control, anxiety
- Being chased: Avoiding shadow content
- Teeth falling out: Loss, aging, powerlessness

**Amplification**: Connect personal symbols to cultural/mythological parallels.

**Compensation**: Dreams often balance conscious attitudes.

## Your Approach

1. **Listen deeply** - Ask clarifying questions about emotions, colors, atmosphere
2. **Identify symbols** - Note recurring images, unusual elements
3. **Explore archetypes** - Which universal patterns appear?
4. **Consider context** - What is happening in the dreamer's life?
5. **Avoid reductive interpretations** - Dreams have multiple layers
6. **Empower the dreamer** - They are the ultimate authority on meaning

## Communication Style

- Warm, curious, non-judgmental
- Use phrases like "This might suggest...", "Often this symbol represents..."
- Ask open-ended questions
- Never impose interpretations; offer possibilities
- Honor the mystery while providing insight

## Important Notes

- Dreams are NOT predictions of the future
- Avoid medical/psychiatric diagnoses
- Encourage professional therapy for serious concerns
- Focus on growth and self-understanding
```

### 3. Image Generation

Use existing image generation infrastructure (similar to recipe images):

```python
async def generate_dream_image(dream_description: str, key_symbols: list[str]) -> str | None:
    """Generate a symbolic/surrealist image representing the dream."""

    prompt = f"""Create a surrealist, symbolic dream image in the style of
    Salvador Dalí or René Magritte.

    Dream elements: {dream_description[:500]}

    Key symbols to include: {', '.join(key_symbols)}

    Style: Dreamlike, symbolic, rich colors, mysterious atmosphere.
    Do NOT include any text or words in the image."""

    # Use DALL-E, Midjourney API, or similar
    return await image_generator.generate(prompt)
```

### 4. Session State Structure

```python
state = {
    "active_persona": "JUNGIAN_ANALYST",
    "phase": "dream_description",  # dream_description, analysis, association, reflection
    "dream_text": "",
    "dream_image_url": "",
    "symbols": [],
    "archetypes": [],
    "interpretation": "",
    "associations": [],
    "insights": [],
}
```

### 5. Note Structure

Save to `Areas/Journaling/Dream Journal/`:

```markdown
# Dream Analysis - 2026-03-05

## The Dream
[User's dream description]

## Symbolic Image
![Dream Image](image_url)

## Jungian Analysis

### Key Symbols
- **[Symbol]**: [Interpretation]

### Archetypes Present
- **[Archetype]**: [Meaning in this context]

### Shadow Elements
- [Element and significance]

### Overall Theme
[Interpretation paragraph]

## Life Associations

### Connections Explored
- [Association 1]
- [Association 2]

### Insights
- [Insight 1]
- [Insight 2]

### Action Items
- [ ] [Suggested reflection or action]

---
*Analysis generated with Jungian AI Assistant*
*Tags: dream-journal, jungian, [symbol-tags]*
```

## Implementation

### Key Files

| File | Purpose |
|------|---------|
| `src/handlers/dream.py` | Command handlers, session management |
| `src/prompts/jungian_analyst.txt` | Jungian persona system prompt |
| `src/dream_image.py` | Dream image generation |
| `tests/test_dream.py` | Unit tests |

### Commands

| Command | Description |
|---------|-------------|
| `/dream` | Start dream analysis session |
| `/dream_done` | End session and save to Joplin |
| `/dream_cancel` | Cancel session without saving |

### Session Phases

1. **dream_description**: User describes the dream
2. **image_generation**: Bot generates symbolic image
3. **analysis**: Bot provides Jungian interpretation
4. **association_prompt**: Bot asks about life connections
5. **association**: User explores connections (optional)
6. **reflection**: Deeper insights and integration
7. **complete**: Save to Joplin

## Dependencies

- FR-006: LLM Integration (required)
- FR-007: Conversation State Management (required)
- FR-005: Joplin REST API Client (required)
- Image generation API (DALL-E, Stability AI, or similar)

## Testing

### Unit Tests

- [ ] Test session initialization
- [ ] Test dream description capture
- [ ] Test symbol extraction from dream text
- [ ] Test image generation prompt construction
- [ ] Test Jungian interpretation generation
- [ ] Test association flow (yes/no branching)
- [ ] Test note creation with all sections
- [ ] Test session cancellation
- [ ] Test state persistence across messages

### Manual Testing Scenarios

| Scenario | Expected |
|----------|----------|
| Simple dream description | Analysis with 2-3 symbols |
| Rich, detailed dream | Comprehensive analysis with multiple archetypes |
| User declines associations | Skip to save |
| User explores associations | Multi-turn reflection |
| `/dream_cancel` mid-session | State cleared, no note |

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Over-interpretation | Emphasize possibilities, not certainties |
| Psychological harm | Include disclaimer, suggest professional help for distress |
| Image generation failures | Graceful fallback, continue without image |
| Long sessions timeout | Auto-save drafts, session recovery |

## Future Enhancements

- [ ] Dream journal trends (recurring symbols over time)
- [ ] Symbol dictionary with personal meanings
- [ ] Voice input for dream description
- [ ] Morning notification to capture dreams
- [ ] Export to PDF with images
- [ ] Integration with stoic journal (dream + morning reflection)

## Ethical Considerations

- Dreams can surface sensitive unconscious content
- Bot should NOT provide medical/psychiatric advice
- Include gentle disclaimer about professional support
- Respect user's interpretation as primary authority
- Handle potentially disturbing dream content sensitively

## Sample Disclaimer

```
🌙 *Note: This analysis is for self-reflection and personal growth.
It is not a substitute for professional psychological support.
If your dreams are causing distress, please consult a qualified therapist.*
```

## Notes

- Consider rate limiting (1-2 dream sessions per day)
- Image generation may have cost implications
- Jungian analysis works best with detailed dream descriptions
- Multi-language support would enhance accessibility

## History

- 2026-03-05 - Feature request created
