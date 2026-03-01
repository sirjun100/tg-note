# Improving Your Resources Folder (Second Brain / PARA)

This doc helps you tidy and structure the **Resources** bucket so it stays useful and consistent with Second Brain / PARA.

## What Resources is for

In PARA, **Resources** are **reference material** — things you might use later, not active projects or responsibilities:

- Topics you’re interested in (books, articles, courses)
- Tools, templates, checklists
- How‑tos, docs, links
- No deadlines; you dip in when relevant

If something has a **due date or outcome**, it belongs in **Projects** or **Areas**, not Resources.

---

## 1. See what you have

From the project root (or on Fly.io inside the app):

```bash
# Local (Joplin running, .env with JOPLIN_URL set)
python scripts/inspect_resources_folder.py

# On Fly.io (Joplin in same machine)
fly ssh console -C "cd /app && python scripts/inspect_resources_folder.py"
```

This prints:

- The Resources folder and how many notes sit in the root
- All subfolders and their note counts
- Up to 20 note titles in the root

Use this to spot clutter (too many notes in root, vague subfolder names, or no subfolders).

---

## 2. Suggested structure (align with the bot)

The bot’s PARA templates already define subfolders under Resources. You can match them so new notes land in the right place.

**Option A – Status-style (emojis, good for quick scanning)**

- `📖 Books & Articles`
- `📋 Templates`
- `🔗 Reference`

**Option B – Role-style (simpler names)**

- `Tools`
- `Templates`
- `Knowledge`

Create any missing subfolders in Joplin (by hand or via `/reorg_init status` or `/reorg_init roles` — that creates the full PARA tree, including Resources subfolders).

---

## 3. Practical improvements

| Issue | Suggestion |
|--------|------------|
| **Too many notes in the root** | Move them into subfolders (e.g. Books, Templates, Reference). Use `/reorg_preview` then `/reorg_execute` to let the bot suggest and apply moves. |
| **Vague or duplicate subfolders** | Merge or rename (e.g. "Stuff", "Misc" → "Reference" or "Knowledge"). Prefer the names from the templates so the bot’s classification stays consistent. |
| **Mixed content** | Keep “how I do X” and templates in **Templates**, links and references in **Reference**, books/courses in **Books & Articles** or **Knowledge**. |
| **Project/area stuff in Resources** | Move notes that are tied to a project or an area of responsibility into **Projects** or **Areas**; leave only reference material in Resources. |
| **Naming** | Use "Resources" as the main folder (with or without subfolders); the bot looks for that name. |

---

## 4. Optional: re-run PARA init

If you want a clean, template-based tree (including Resources subfolders):

1. **Back up** your Joplin data.
2. In Telegram: `/reorg_init status` or `/reorg_init roles`.
3. This creates/ensures **Projects**, **Areas**, **Resources**, **Archive** and their subfolders (e.g. under Resources: 📖 Books & Articles, 📋 Templates, 🔗 Reference).
4. Then use `/reorg_preview` and `/reorg_execute` to move existing notes into the new structure.

If you already have a Resources folder you like, you can keep it and only add the **subfolders** from the template (by hand in Joplin) so the bot has clear targets when classifying new notes.

---

## 5. Quick checklist

- [ ] Run `scripts/inspect_resources_folder.py` and review root vs subfolder counts.
- [ ] Reduce root clutter: move notes into 3–5 clear subfolders.
- [ ] Align subfolder names with the bot’s templates (Books & Articles, Templates, Reference or Tools, Templates, Knowledge).
- [ ] Move project/area-related notes out of Resources into Projects/Areas.
- [ ] Optionally run `/reorg_init status` or `roles` and then `/reorg_preview` + `/reorg_execute` to tidy with the bot.

If you paste the script output here, we can tailor the next steps (e.g. exact subfolder names or a small custom script to move notes by tag/folder).
