# Bug Report: BF-008 - Stoic Journal: Evening Reflection Deletes Morning Reflection

**Status**: 🔴 Open
**Priority**: 🔴 Critical
**Story Points**: 5
**Created**: 2026-03-04
**Updated**: 2026-03-04
**Assigned Sprint**: Backlog
**Impact**: Data Loss

## Description

When a user completes both a morning and evening Stoic journal reflection on the same day, the evening reflection is accidentally deleting or overwriting the morning reflection in the note. Users lose their morning reflections when they attempt to save the evening reflection.

This is a critical data loss issue that destroys user content without warning.

## Steps to Reproduce

1. User sends `/stoic morning` to start morning reflection
2. User answers all morning questions and sends `/stoic_done` to save
3. Bot creates a note in Stoic Journal with morning reflection (✓ note created successfully)
4. Later same day, user sends `/stoic evening` to start evening reflection
5. User answers all evening questions and sends `/stoic_done`
6. Bot attempts to save evening reflection
7. **Result**: The note is corrupted or the morning section is deleted
8. User's morning reflection is lost 🔥

## Expected Behavior

When saving a reflection to a note that already has a reflection from the same day:
1. **Check for duplicate sections** (morning or evening already exists)
2. **Prompt user with options**:
   - `/stoic_replace` - Replace the existing section
   - `/stoic_append` - Add as another section below
   - `/stoic_cancel` - Discard and keep existing
3. **Preserve all content** - Do not delete or overwrite user data
4. **Save both reflections** to the same note without data loss

## Root Cause Analysis

Likely cause in `src/handlers/stoic.py` `_finish_stoic_session()` function (~lines 432-575):

The function appears to:
1. Get or create a note for the date
2. Check if note exists
3. **Possible issue**: When appending evening content, it might be:
   - Not properly checking for existing morning section
   - Using wrong body replacement logic
   - Overwriting instead of appending
   - Clearing the entire note body when it should only update one section

Key code sections to investigate:
- `_check_section_exists()` (line 424) - Duplicate detection
- `_replace_section()` (line 176) - Section replacement logic
- Note update logic (line 504) - Body merging

## Affected Scenarios

**Data Loss Confirmed When:**
- User has existing morning reflection for today
- User tries to save evening reflection same day
- Note exists but logic incorrectly handles dual reflections

**Safe Scenarios:**
- Only morning OR evening saved (not both)
- Different dates (no conflict)
- First reflection for the day

## Impact

- 🔴 **Severity**: CRITICAL - Data Loss
- **User Impact**: Users lose morning reflections when saving evening reflections
- **Frequency**: Happens when user does both morning + evening same day (common use case!)
- **Recovery**: No recovery - content deleted permanently

## Proposed Solution

### 1. Fix Section Replacement Logic

Review `_replace_section()` and body merging:

```python
# In _finish_stoic_session(), line ~471-502
if existing:
    # CRITICAL FIX: Properly handle dual reflections

    # Check what section already exists
    has_morning = _check_section_exists(existing_body, "morning")
    has_evening = _check_section_exists(existing_body, "evening")

    if _check_section_exists(existing_body, mode):
        # Section already exists - prompt for action
        await message.reply_text(
            f"⚠️ You already have a {mode.capitalize()} reflection for today.\n\n"
            f"What would you like to do?\n"
            f"  /stoic_replace - Replace the existing reflection\n"
            f"  /stoic_append - Add another reflection to the note"
        )
        # Store state for pending action
        state["pending_action"] = "duplicate_detected"
        state["existing_note_id"] = note_id
        state["existing_body"] = existing_body
        state["new_section_content"] = section_content
        orch.state_manager.update_state(user_id, state)
        return False
    else:
        # No duplicate - safely append
        new_body = f"{existing_body}\n\n{section_content}"
        await orch.joplin_client.update_note(note_id, {"body": new_body})
```

### 2. Add Unit Tests

Create comprehensive tests to verify both reflections coexist:

```python
def test_morning_and_evening_both_saved():
    """Verify morning and evening reflections coexist in same note"""
    # Create morning note
    # Add evening reflection
    # Verify both sections present in final note

def test_evening_appends_to_existing_morning():
    """Evening reflection appends to existing morning reflection"""

def test_duplicate_morning_asks_for_action():
    """Saving duplicate morning section prompts for action"""

def test_duplicate_evening_asks_for_action():
    """Saving duplicate evening section prompts for action"""
```

### 3. Add Data Loss Prevention

- Log note body before and after update
- Add validation to ensure content not lost
- Show user preview of final note structure

## Technical References

- File: `src/handlers/stoic.py:432-575` - `_finish_stoic_session()`
- File: `src/handlers/stoic.py:176-190` - `_replace_section()`
- File: `src/handlers/stoic.py:424-429` - `_check_section_exists()`
- File: `tests/test_stoic.py` - Existing tests

## Testing Checklist

- [ ] Create test note with morning reflection
- [ ] Add evening reflection to same note
- [ ] Verify morning section still present
- [ ] Verify evening section added
- [ ] Verify both sections properly formatted
- [ ] Test `/stoic_replace` action on duplicate
- [ ] Test `/stoic_append` action on duplicate
- [ ] Test error message when saving duplicate
- [ ] Verify state manager stores pending actions correctly

## Dependencies

- Fix depends on reviewing actual note body output (need to inspect failing case)
- Tests depend on test fixtures for note creation

## Notes

This is blocking users who want to do complete daily reflections (morning + evening). The data loss is unacceptable and needs immediate investigation and fix.

**Severity**: Cannot reliably use stoic journal feature for daily routine until fixed.

## History

- 2026-03-04 - Reported by user: "stoic evening deleted my morning stoic"
- 2026-03-04 - Created as BF-008 - Critical data loss issue
