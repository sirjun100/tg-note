# /stoic command – brainstorm

You already have a **Stoic Journal** template in PARA: **Areas → 📓 Journaling → Stoic Journal**, and an example note structure. Here are concrete options for a `/stoic` command.

---

## 1. What the command could do (pick one or combine)

| Option | Description | Complexity |
|--------|-------------|------------|
| **A. One-shot entry** | `/stoic` or `/stoic [your text]` → create **one note** in Stoic Journal with today’s date and your text (and optional template). | Low |
| **B. Template drop** | `/stoic` → create a **new note** in Stoic Journal with your **existing template** (from file or constant), title e.g. `Stoic Journal - 2025-02-28`. User fills sections in Joplin. | Low |
| **C. Guided flow** | `/stoic` → bot asks prompts (Morning/Evening? What did you control? Grateful for? etc.) → you reply over several messages → **one note** created at the end (like /braindump). | Medium |
| **D. Append to today** | `/stoic [line]` → if a note for **today** exists in Stoic Journal, append the line; otherwise create today’s note with that line. | Medium |

---

## 2. Your existing structure (for template)

From your example note, the structure is:

- **Title:** `Stoic Journal Entry - September 27, 2025` (or `Stoic Journal - YYYY-MM-DD`)
- **Sections:**
  - Stoic State Assessment (Internal Control, Emotional Regulation, Daily Virtue Focus)
  - Morning Reflection
  - Challenges Faced
  - Lessons Learned
  - Evening Reflection

So a **template** could be a markdown file (e.g. `prompts/stoic_journal_template.md`) or a constant in code with these headings and empty placeholders.

---

## 3. Technical anchors in the codebase

- **Folder:** Resolve Stoic Journal via  
  `get_or_create_folder_by_path(["Areas", "📓 Journaling", "Stoic Journal"])`  
  (or `["📓 Journaling", "Stoic Journal"]` if you don’t use an "Areas" parent). Then create the note in that folder.
- **Create note:** Same as elsewhere: `joplin_client.create_note(folder_id, title, body)` or reuse `create_note_in_joplin(orch, note_data)` if we pass a **folder path** or a known folder id. Today `create_note_in_joplin` resolves folder by **title** (flat list); for a nested path we’d either:
  - add a special case for `parent_id = "Stoic Journal"` / `"📓 Journaling/Stoic Journal"` that calls `get_or_create_folder_by_path`, or
  - resolve the Stoic Journal folder id once in the /stoic handler and pass that id in `note_data["parent_id"]`.
- **State (for guided flow):** Reuse the same pattern as `/braindump`: `state_manager` with e.g. `active_persona: "STOIC_JOURNAL"`, collect answers, then build body and call `create_note_in_joplin` with a final `note_data` (title + body + parent_id = Stoic Journal folder id).

---

## 4. Suggested first step (MVP)

- **Command:** `/stoic` or `/stoic [optional one-line reflection]`
- **Behaviour:**
  1. Resolve Stoic Journal folder (path above).
  2. Title: `Stoic Journal - YYYY-MM-DD`.
  3. Body: **your template** (from file or constant) with today’s date filled in; if user sent text (e.g. `/stoic Had a calm morning`), append it to a “Quick reflection” section or at the end.
  4. Create the note in that folder, reply e.g. “✅ Stoic journal entry created for today.”

No LLM, no multi-turn flow. Once that works, you can add:
- **Guided flow** (like braindump) with prompts for each section, or
- **Append to today** so multiple `/stoic ...` messages in one day add to the same note.

---

## 5. Open choices

- **Template source:** Repo file (`prompts/stoic_journal_template.md`) vs constant in code vs “no template, just title + user text”.
- **Morning vs evening:** One template vs two (e.g. `/stoic morning` vs `/stoic evening` with different section order or prompts).
- **Tags:** e.g. `stoic`, `journal` (optional).
- **Conflict with existing note:** If a note for “today” already exists, do we create a second one (e.g. “Stoic Journal - 2025-02-28 (2)”) or try to append (needs lookup by title/date)?

If you tell me your preferred option (A/B/C/D or MVP + one addition), I can outline the exact handler and data flow next (e.g. new handler in `handlers/` and how it calls Joplin + optional state).
