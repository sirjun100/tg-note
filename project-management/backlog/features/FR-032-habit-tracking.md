# Feature Request: FR-032 - Habit Check-ins and Tracking

**Status**: ✅ Completed
**Priority**: 🟢 Low
**Story Points**: 5
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Sprint 11

## Description

Add simple habit tracking with daily check-ins. Users define habits they want to track (exercise, read, meditate, etc.) and check in daily with `/habits`. The bot shows their defined habits as quick yes/no options, records responses, and provides streak tracking and weekly summaries.

This keeps habit tracking lightweight and integrated into the existing Telegram workflow.

## User Story

As a user building better habits,
I want to quickly log my daily habits in Telegram,
so that I can track consistency without needing a separate habit app.

## Acceptance Criteria

- [ ] `/habits add <habit>` adds a new habit to track
- [ ] `/habits` shows today's habits with quick check-in buttons
- [ ] Inline buttons for Yes/No/Skip each habit
- [ ] Current streak displayed for each habit
- [ ] `/habits stats` shows weekly/monthly completion rates
- [ ] `/habits remove <habit>` removes a habit
- [ ] `/habits list` shows all defined habits with streaks
- [ ] Habits reset daily at user's configured timezone midnight
- [ ] Optional: Daily reminder to check in

## Business Value

Habits are the foundation of productivity. Many users:
- Want to build habits but forget to track
- Find dedicated habit apps too heavyweight
- Already check Telegram daily

Integrating habit tracking into an existing workflow removes friction and increases follow-through.

## Technical Requirements

### 1. Data Model

```python
class Habit(BaseModel):
    id: str
    user_id: int
    name: str
    created_at: datetime
    active: bool = True

class HabitEntry(BaseModel):
    id: str
    habit_id: str
    user_id: int
    date: date
    completed: bool  # True = done, False = skipped
    logged_at: datetime

class HabitStats(BaseModel):
    habit_id: str
    name: str
    current_streak: int
    longest_streak: int
    last_7_days: int  # completions
    last_30_days: int
    completion_rate: float
```

### 2. Database Schema (SQLite)

```sql
CREATE TABLE habits (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT 1,
    UNIQUE(user_id, name)
);

CREATE TABLE habit_entries (
    id TEXT PRIMARY KEY,
    habit_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    completed BOOLEAN NOT NULL,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (habit_id) REFERENCES habits(id),
    UNIQUE(habit_id, date)
);

CREATE INDEX idx_habit_entries_date ON habit_entries(user_id, date);
```

### 3. Check-in Flow

```
User: /habits
       │
       ▼
┌─────────────────────────────────────────┐
│ 🌟 Daily Habits - March 5               │
│                                         │
│ 🏃 Exercise        [✅ Yes] [❌ No]      │
│    🔥 5 day streak                      │
│                                         │
│ 📚 Read 30 min     [✅ Yes] [❌ No]      │
│    🔥 12 day streak                     │
│                                         │
│ 🧘 Meditate        [✅ Yes] [❌ No]      │
│    ⚡ Start streak!                     │
│                                         │
│ ✅ 2/3 completed today                  │
└─────────────────────────────────────────┘
```

### 4. Inline Keyboard Buttons

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def build_habit_keyboard(habits: list[Habit], today_entries: dict) -> InlineKeyboardMarkup:
    """Build inline keyboard for habit check-in."""

    keyboard = []
    for habit in habits:
        entry = today_entries.get(habit.id)

        if entry is not None:
            # Already logged today
            status = "✅" if entry.completed else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {habit.name} (logged)",
                    callback_data=f"habit_undo_{habit.id}"
                )
            ])
        else:
            # Not yet logged
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ {habit.name}",
                    callback_data=f"habit_yes_{habit.id}"
                ),
                InlineKeyboardButton(
                    "❌",
                    callback_data=f"habit_no_{habit.id}"
                )
            ])

    # Stats button at bottom
    keyboard.append([
        InlineKeyboardButton("📊 View Stats", callback_data="habit_stats")
    ])

    return InlineKeyboardMarkup(keyboard)
```

### 5. Streak Calculation

```python
def calculate_streak(entries: list[HabitEntry], today: date) -> int:
    """Calculate current streak for a habit."""

    # Sort entries by date descending
    sorted_entries = sorted(entries, key=lambda e: e.date, reverse=True)

    streak = 0
    expected_date = today

    for entry in sorted_entries:
        if entry.date == expected_date and entry.completed:
            streak += 1
            expected_date -= timedelta(days=1)
        elif entry.date == expected_date and not entry.completed:
            # Explicitly marked as skipped - breaks streak
            break
        elif entry.date < expected_date:
            # Missing day - breaks streak
            break

    return streak
```

### 6. Commands

| Command | Description |
|---------|-------------|
| `/habits` | Show today's check-in with buttons |
| `/habits add <name>` | Add a new habit |
| `/habits remove <name>` | Remove a habit |
| `/habits list` | List all habits with current streaks |
| `/habits stats` | Detailed statistics |
| `/habits stats <name>` | Stats for specific habit |
| `/habits reminder <HH:MM>` | Set daily reminder time |
| `/habits reminder off` | Disable reminders |

### 7. Stats Display

```
📊 **Habit Stats - Last 30 Days**

**🏃 Exercise**
├ Current streak: 5 days 🔥
├ Longest streak: 14 days
├ Last 7 days: 6/7 (86%)
└ Last 30 days: 22/30 (73%)

**📚 Read 30 min**
├ Current streak: 12 days 🔥
├ Longest streak: 12 days ⭐ (record!)
├ Last 7 days: 7/7 (100%)
└ Last 30 days: 25/30 (83%)

**🧘 Meditate**
├ Current streak: 0 days
├ Longest streak: 8 days
├ Last 7 days: 3/7 (43%)
└ Last 30 days: 12/30 (40%)

**Overall completion rate: 65%**
```

### 8. Daily Reminder

```python
async def send_habit_reminder(user_id: int, orch: TelegramOrchestrator):
    """Send daily habit check-in reminder."""

    habits = await get_user_habits(user_id)
    today_entries = await get_today_entries(user_id)

    pending = [h for h in habits if h.id not in today_entries]

    if pending:
        await orch.send_message(
            user_id,
            f"🌟 You have {len(pending)} habits to check in!\n"
            f"Use /habits to log them.",
            reply_markup=build_habit_keyboard(habits, today_entries)
        )
```

### 9. Weekly Summary (In Weekly Report)

Add habit section to weekly report:

```markdown
## 🌟 Habit Tracking

| Habit | This Week | Streak |
|-------|-----------|--------|
| 🏃 Exercise | 5/7 ⬆️ | 5 days |
| 📚 Read | 7/7 🎯 | 12 days |
| 🧘 Meditate | 3/7 ⬇️ | 0 days |

**Highlight**: Reading streak at all-time high! 🎉
**Focus**: Meditation dropped - consider shorter sessions?
```

## Implementation

### Key Files to Create

| File | Purpose |
|------|---------|
| `src/habit_service.py` | Habit CRUD and stats logic |
| `src/handlers/habits.py` | Command and callback handlers |
| `tests/test_habits.py` | Unit tests |

### Key Files to Modify

| File | Changes |
|------|---------|
| `src/handlers/__init__.py` | Register habit handlers |
| `src/scheduler_service.py` | Add reminder scheduling |
| `src/weekly_report_generator.py` | Add habit summary section |
| Database migrations | Create habits tables |

### Callback Handler

```python
async def handle_habit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks for habits."""

    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id

    if data.startswith("habit_yes_"):
        habit_id = data.replace("habit_yes_", "")
        await log_habit_entry(user_id, habit_id, completed=True)

    elif data.startswith("habit_no_"):
        habit_id = data.replace("habit_no_", "")
        await log_habit_entry(user_id, habit_id, completed=False)

    elif data.startswith("habit_undo_"):
        habit_id = data.replace("habit_undo_", "")
        await delete_today_entry(user_id, habit_id)

    elif data == "habit_stats":
        stats = await get_habit_stats(user_id)
        await query.message.reply_text(format_stats(stats))
        return

    # Refresh the check-in display
    habits = await get_user_habits(user_id)
    today_entries = await get_today_entries(user_id)

    await query.edit_message_text(
        format_checkin_message(habits, today_entries),
        reply_markup=build_habit_keyboard(habits, today_entries)
    )
```

## Testing

### Unit Tests

- [ ] Test habit creation
- [ ] Test habit deletion
- [ ] Test entry logging
- [ ] Test streak calculation (continuous)
- [ ] Test streak calculation (broken)
- [ ] Test streak calculation (skip handling)
- [ ] Test stats calculation
- [ ] Test timezone handling

### Manual Testing Scenarios

| Action | Expected |
|--------|----------|
| `/habits add Exercise` | Habit added, confirmation |
| `/habits` with 3 habits | All 3 shown with buttons |
| Click ✅ on Exercise | Logged, streak updated, button changes |
| Click ❌ on Meditate | Logged as skipped, streak resets |
| `/habits stats` | Shows all habits with rates |
| Next day `/habits` | Fresh buttons, streaks current |

## Dependencies

- FR-007: Conversation State Management (for inline callbacks)
- FR-015: Weekly Report (optional - for habit summary section)
- Database (SQLite - existing)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Timezone confusion | Use user's configured timezone |
| Too many habits | Suggest limiting to 3-5 |
| Forgotten check-ins | Optional daily reminder |
| Data entry errors | Undo capability |

## Future Enhancements

- [ ] Habit categories/grouping
- [ ] Flexible schedules (MWF only, weekdays only)
- [ ] Notes/context for each entry
- [ ] Habit templates (common habits to choose from)
- [ ] Social accountability (share streaks)
- [ ] Visual calendar heatmap
- [ ] Achievement badges
- [ ] Export data to CSV

## Notes

- Keep it simple - this isn't a full habit app, just lightweight tracking
- Streaks are motivating - display them prominently
- Consider "skip" vs "not done" - skipping shouldn't always break streak
- Integrate with stoic journal for deeper reflection on habits

## History

- 2026-03-05 - Feature request created
