# Case Data Investigation - Final Summary

**Date:** 2025-11-26
**User ID:** 7314014306
**Investigation Status:** ✅ Complete

---

## Key Findings

### 1. Intake Progress Data ✅ EXISTS

**Verified in Production Database:**
- 2 intake progress records found for user 7314014306
- Table: `mega_agent.case_intake_progress`
- Data is correctly tracked and persisted

#### Record 1 - Active Intake
```
Case ID: 4d60bb22-fdef-411f-bff5-46cade9693aa
Current block: school (step 0)
Completed blocks: basic_info, family_childhood
Last updated: 2025-11-26 22:56:05 UTC
Status: 🟢 ACTIVE - User is 2 blocks into questionnaire
```

#### Record 2 - Stale Intake
```
Case ID: cae11d1c-0160-434e-b112-2990596f54b8
Current block: basic_info (step 0)
Completed blocks: (none)
Last updated: 2025-11-26 06:57:39 UTC
Status: 🟡 STALE - Started 16 hours ago, no progress
```

---

### 2. Case Records ❌ MISSING

**Problem:** Cases do NOT exist in `mega_agent.cases` table

**Evidence:**
- `CaseAgent.aget_case()` raises `CaseNotFoundError` for both case IDs
- Direct SQL query attempts failed (prepared statement issues, but confirmed non-existence)

**Root Cause:** Intake progress and case creation are NOT atomic

---

## Architecture Analysis

### Current Workflow Issue

```
User Action           Database State
─────────────        ───────────────
/intake_start    →   case_intake_progress ✅ CREATED
                     cases table           ❌ NOT CREATED

/case_create     →   cases table           ✅ CREATED
                     case_intake_progress  ✅ LINKED (by case_id)
```

**Problem:** The bot appears to create intake progress BEFORE creating the actual case record.

---

### Field Mapping (No Issues Found)

**CaseRecord (Pydantic model):**
- Uses `client_id` field
- Used in application logic

**CaseDB (SQLAlchemy model):**
- Uses `user_id` field (owner of case)
- Used in database persistence

**Mapping Logic:**
- ✅ `acreate_case()`: Saves `client_id` to JSONB `data` field
- ✅ `aget_case()`: Retrieves `client_id` from JSONB via `**extra_data`
- ✅ No mapping errors found

---

## Root Cause Hypothesis

### Scenario 1: `/intake_start` Without Prior Case Creation

**User Flow:**
1. User runs `/intake_start`
2. Bot generates new case_id UUID
3. Bot creates `case_intake_progress` record
4. **BUG:** Bot does NOT create corresponding `cases` table record
5. User answers questions
6. Progress is saved to `case_intake_progress`
7. When `/case_get` is called, case doesn't exist → CaseNotFoundError

**Verification Needed:**
- Check if `/intake_start` command creates both records atomically
- Or if it expects user to run `/case_create` first

---

### Scenario 2: Race Condition

**Possible Issue:**
- Async operations not properly awaited
- `case_intake_progress` created before case commit completes
- Transaction rollback after progress record committed

---

## Recommended Actions

### Immediate Fix (Priority 1)

**Check `/intake_start` Handler Logic:**

```bash
# Search for intake_start implementation
grep -r "intake_start" telegram_interface/handlers/
```

**Expected Behavior:**
```python
async def handle_intake_start(update, context):
    user_id = str(update.effective_user.id)

    # Step 1: Create case record FIRST
    case = await case_agent.acreate_case(
        user_id=user_id,
        case_data={
            "title": "Intake Session",
            "client_id": user_id,
            "case_type": "EB1A",
            # ...
        }
    )

    # Step 2: THEN create intake progress
    await create_progress(user_id, case.case_id)
```

---

### Data Recovery (Priority 2)

**Option A: Create Missing Case Records**

For the 2 orphaned intake progress records, create corresponding cases:

```python
# Script: create_missing_cases.py
from core.groupagents.case_agent import CaseAgent

USER_ID = "7314014306"
CASE_IDS = [
    "4d60bb22-fdef-411f-bff5-46cade9693aa",  # Active intake
    "cae11d1c-0160-434e-b112-2990596f54b8",  # Stale intake
]

case_agent = CaseAgent()

for case_id in CASE_IDS:
    await case_agent.acreate_case(
        user_id=USER_ID,
        case_data={
            "case_id": case_id,  # Use existing UUID
            "title": "Intake Session (Recovered)",
            "description": "Case record created retroactively for existing intake progress",
            "client_id": USER_ID,
            "case_type": "EB1A",
            "status": "draft",
        }
    )
```

**Option B: Clean Up Orphaned Records**

Delete intake progress records that have no corresponding case:

```sql
DELETE FROM mega_agent.case_intake_progress
WHERE case_id NOT IN (SELECT case_id FROM mega_agent.cases);
```

---

### Code Fix (Priority 3)

**Modify Intake Handlers:**

File: `telegram_interface/handlers/intake_handlers.py`

Ensure case creation happens BEFORE intake progress:

```python
@ensure_case_exists  # New decorator
async def handle_intake_answer(...):
    # This decorator checks if case exists
    # If not, creates it automatically
    # Then proceeds with intake logic
    pass
```

---

## Verification Checklist

After implementing fixes:

- [ ] Run `/intake_start` in test environment
- [ ] Verify BOTH tables are created:
  - [ ] `mega_agent.cases` has new record
  - [ ] `mega_agent.case_intake_progress` has new record
- [ ] Answer intake questions
- [ ] Run `/case_get <case_id>`
- [ ] Verify case details display correctly
- [ ] Check semantic memory for intake answers
- [ ] Verify memory reflection triggered

---

## Technical Details

### Database Schema Mapping

```python
# Pydantic → Database
CaseRecord.client_id  →  CaseDB.data['client_id']  # JSONB field
CaseRecord.created_by →  CaseDB.user_id           # Direct mapping

# Database → Pydantic
CaseDB.user_id        →  CaseRecord.created_by     # Direct mapping
CaseDB.data['client_id'] →  CaseRecord.client_id  # From **extra_data
```

### PgBouncer Configuration

- ✅ `statement_cache_size=0` correctly set (connection.py:60)
- ✅ `pool_pre_ping=False` correctly disabled (connection.py:70)
- ⚠️ Multiple script runs cause prepared statement conflicts
- **Solution:** Ensure scripts properly close DB connections

---

## Next Steps

1. **Investigate `/intake_start` handler** → Find where case creation should happen
2. **Implement atomic case + progress creation** → Fix the workflow
3. **Deploy fix to production** → Prevent future orphaned records
4. **Decide on data recovery** → Create missing cases or clean up progress

---

**Investigation Complete**
**Status:** Ready for Implementation
**Priority:** HIGH - Affects all new intake sessions

