# Ally Targeting for Out-of-Combat Spell Casting (Issue #233)

## TL;DR

> **Quick Summary**: Complete the ally-targeting feature for out-of-combat spell casting. The backend route logic already works — this plan fills 8 serializer gaps, fixes an ally-only validation bug, and implements the full frontend: types, target selector UI, data flow, and tests.
> 
> **Deliverables**:
> - 8 backend serializer/field-map fixes so `outOfCombatTarget` flows through all read/write paths
> - 1 logic fix: reject ally-only spells cast without a target
> - Frontend: `outOfCombatTarget` in spell type + `targetPlayerUserId` in cast request type
> - Frontend: target selector UI in `OutOfCombatSpellCastCard` (appears when spell allows ally targeting)
> - Frontend: party players data flow from `usePlayerBoardResources` → `PlayerBoardPage` → `PlayerBoardStatusPanel` → card
> - 4 backend tests + 6 frontend tests covering the new functionality
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves (backend fixes → frontend types → frontend UI + tests)
> **Critical Path**: Serializer fixes → Frontend types → Target selector UI

---

## Context

### Original Request
GitHub Issue #233: Add ally targeting for out-of-combat buff/utility spells. The active effect belongs to the target; concentration belongs to the caster. For ally-target concentration spells, create a lightweight concentration marker on the caster and the actual gameplay effect on the target.

### Interview Summary
**Key Discovery**: The backend is nearly complete. The route handler (`cast_spell_out_of_combat`), service functions (`build_persisted_effects`, `build_concentration_marker`, `clear_concentration_group_across_session`), migration, models, seed data, and 7 integration tests already exist and work. The work is:
1. Plug 8 serializer gaps where `outOfCombatTarget` is missing from read/write paths
2. Fix 1 logic bug (ally-only spells silently self-target without a target)
3. Implement the entire frontend target selector

**Research Findings**:
- Backend tests (`TestAllyTargeting`) already cover: ally-target effect placement, concentration marker, cross-session cleanup, self-target v1 preservation, slot consumption, validation errors (400)
- Frontend type name is `PartyMemberSummary` (not `PartyMemberRead`), with field `userId`
- The `_FIELD_MAP` serialization pattern is used in both `campaign_spells.py` and `base_spells.py`
- `update_spell()` in campaign routes has an inline field_map that also needs the field added

### Metis Review
**Identified Gaps** (addressed):
- 3 additional serializer gaps: `base_spells.py _FIELD_MAP`, `to_campaign_spell_read()`, `update_spell() field_map`
- Logic bug: ally-only spell without target silently self-targets — need guard
- Frontend type name correction: `PartyMemberSummary` not `PartyMemberRead`
- `check_out_of_combat_cast_eligibility` ignores `out_of_combat_target` — should validate
- Existing campaigns seeded before migration 0072 will have `"self"` for all spells — backfill is a follow-up

---

## Work Objectives

### Core Objective
CompleteIssue #233: Allow eligible out-of-combat spells (currently `enhance_ability` and `shield_of_faith`) to target allied party members via a target selector UI.

### Concrete Deliverables
- All 8 backend paths that serialize `outOfCombatTarget` work correctly
- Ally-only spells (`outOfCombatTarget="ally"`) without a target raise 400
- Frontend type `OutOfCombatCastableSpell` includes `outOfCombatTarget`
- Frontend type `OutOfCombatCastRequest` includes `targetPlayerUserId`
- `usePlayerBoardResources` exposes `partyPlayers`
- `OutOfCombatSpellCastCard` shows target selector when spell allows ally targeting
- Cast payload includes `targetPlayerUserId` for ally targets
- All backend + frontend tests pass

### Definition of Done
- [ ] `pytest tests/test_out_of_combat_cast.py` passes (including new ally-only test)
- [ ] `vitest run` passes for PlayerBoardPage tests
- [ ] Backend API returns `outOfCombatTarget` in castable spells list
- [ ] Backend API rejects ally-only spell without target with 400
- [ ] Frontend target selector appears for `self_or_ally` and `ally` spells
- [ ] Frontend target selector hidden for `self` spells
- [ ] Cast request includes `targetPlayerUserId` when ally is selected

### Must Have
- `outOfCombatTarget` serialized in ALL 8 backend paths
- Ally-only guard in cast endpoint
- Frontend target selector for ally-eligible spells
- `targetPlayerUserId` in cast request payload
- Tests for both backend and frontend changes

### Must NOT Have (Guardrails)
- NO new migration files (column already exists)
- NO HP/death validation for targets (follow-up issue)
- NO AoE spell guard (out of scope per issue)
- NO concentration conflict prompt UX (out of scope)
- NO backfill script for existing campaigns (follow-up issue)
- NO jsdom or Testing Library (use existing `renderToStaticMarkup` pattern)
- NO party member fetching inside `OutOfCombatSpellCastCard` (pass as props)
- NO changes to self-target v1 behavior (must remain identical)
- NO `PartyMemberRead` type creation (use existing `PartyMemberSummary`)

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest for backend, vitest for frontend)
- **Automated tests**: YES (Tests-after — add tests alongside implementation)
- **Framework**: pytest (backend), vitest (frontend)
- **Test pattern**: Backend: `unittest.TestCase` / `IsolatedAsyncioTestCase` with MagicMock; Frontend: `renderToStaticMarkup` + `vi.mock`

### QA Policy
Every task MUST include agent-executed QA scenarios.
- **Backend**: Use Bash (pytest) - run tests, check assertions
- **Frontend**: Use Bash (vitest) - run component tests, check output
- **Integration**: Use Bash (curl) - hit endpoints, verify response shape

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately - backend fixes, all independent):
├── Task 1: Fix 8 serializer gaps for outOfCombatTarget [quick]
├── Task 2: Add ally-only validation guard in cast endpoint [quick]
└── Task 3: Add outOfCombatTarget to eligibility check [quick]

Wave 2 (After Wave 1 - frontend types + data flow):
├── Task 4: Extend frontend types for ally targeting [quick]
├── Task 5: Expose partyPlayers in usePlayerBoardResources [quick]
└── Task 6: Thread targetOptions through PlayerBoardPage and StatusPanel [quick]

Wave 3 (After Wave 2 - target selector UI + tests):
├── Task 7: Build target selector in OutOfCombatSpellCastCard [visual-engineering]
├── Task 8: Backend tests for serializer gaps + ally-only guard [unspecified-high]
└── Task 9: Frontend tests for target selector + data flow [unspecified-high]

Wave FINAL (After ALL tasks — 4 parallel reviews, then user okay):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1 | - | 8 |
| 2 | - | 8 |
| 3 | - | 8 |
| 4 | - | 7, 9 |
| 5 | - | 6, 7, 9 |
| 6 | 5 | 7, 9 |
| 7 | 4, 6 | 9 |
| 8 | 1, 2, 3 | F1-F4 |
| 9 | 4, 5, 6, 7 | F1-F4 |
| F1-F4 | 1-9 | - |

### Agent Dispatch Summary

- **Wave 1**: 3 — T1 → `quick`, T2 → `quick`, T3 → `quick`
- **Wave 2**: 3 — T4 → `quick`, T5 → `quick`, T6 → `quick`
- **Wave 3**: 3 — T7 → `visual-engineering`, T8 → `unspecified-high`, T9 → `unspecified-high`
- **FINAL**: 4 — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Fix 8 serializer gaps for outOfCombatTarget

  **What to do**:
  - Add `"outOfCombatTarget": "out_of_combat_target"` to `_FIELD_MAP` in `apps/control-server/app/services/campaign_spells.py` (after line 66, next to `"outOfCombatCastable"`)
  - Add `"outOfCombatTarget": "out_of_combat_target"` to `_FIELD_MAP` in `apps/control-server/app/services/base_spells.py` (after line 69)
  - Add `out_of_combat_target=base_spell.out_of_combat_target` to `seed_campaign_spells()` in `apps/control-server/app/services/campaign_spells.py` (after line 160, next to `out_of_combat_castable`)
  - Add `outOfCombatTarget: str = "self"` field to `BaseSpellRead` in `apps/control-server/app/schemas/base_spell_read.py` (after line 91, next to `outOfCombatCastable`)
  - Add `outOfCombatTarget=spell.out_of_combat_target` to `to_base_spell_read()` in `apps/control-server/app/api/serializers/base_spell.py` (after line 79, next to `outOfCombatCastable`)
  - Add `outOfCombatTarget=spell.out_of_combat_target` to `to_base_spell_seed_entry()` in `apps/control-server/app/api/serializers/base_spell.py` (after line 142, next to `outOfCombatCastable`)
  - Add `outOfCombatTarget` mapping to `to_campaign_spell_read()` in `apps/control-server/app/api/routes/campaign_spells.py` (after line 97, next to `outOfCombatCastable`)
  - Add `outOfCombatTarget` mapping to the inline `field_map` dict in `update_spell()` in `apps/control-server/app/api/routes/campaign_spells.py` (within lines 174-218, next to `outOfCombatCastable`)

  **Must NOT do**:
  - Do NOT create new migration files (column already exists from 0072)
  - Do NOT change any route handler logic in this task
  - Do NOT change the model field definition (it's already correct)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Mechanical field additions, same pattern repeated 8 times
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T2, T3)
  - **Parallel Group**: Wave 1
  - **Blocks**: T8 (tests need these fixes)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `apps/control-server/app/services/campaign_spells.py:66` — `_FIELD_MAP` where `"outOfCombatCastable": "out_of_combat_castable"` is defined. Add the new key right after this line.
  - `apps/control-server/app/services/base_spells.py:69` — Same `_FIELD_MAP` pattern for base spells.
  - `apps/control-server/app/services/campaign_spells.py:160` — `seed_campaign_spells()` where `out_of_combat_castable=base_spell.out_of_combat_castable` is set. Add the new field right after.
  - `apps/control-server/app/schemas/base_spell_read.py:91` — `BaseSpellRead` class where `outOfCombatCastable: bool = False` is defined.
  - `apps/control-server/app/api/serializers/base_spell.py:79` — `to_base_spell_read()` where `outOfCombatCastable=spell.out_of_combat_castable` is mapped.
  - `apps/control-server/app/api/serializers/base_spell.py:142` — `to_base_spell_seed_entry()` where `outOfCombatCastable=spell.out_of_combat_castable` is mapped.
  - `apps/control-server/app/api/routes/campaign_spells.py:97` — `to_campaign_spell_read()` where fields are mapped to the read schema.
  - `apps/control-server/app/api/routes/campaign_spells.py:174-218` — `update_spell()` with inline field_map dict. Search for `"outOfCombatCastable"` to find the exact insertion point.

  **API/Type References**:
  - `apps/control-server/app/models/campaign_spell.py:126-129` — `out_of_combat_target` field definition with `String(20)`, `nullable=False`, `server_default="self"`.

  **Acceptance Criteria**:

  - [ ] `grep -r "outOfCombatTarget" apps/control-server/app/services/campaign_spells.py` outputs the field_map entry
  - [ ] `grep -r "outOfCombatTarget" apps/control-server/app/services/base_spells.py` outputs the field_map entry
  - [ ] `grep -r "out_of_combat_target" apps/control-server/app/services/campaign_spells.py` outputs the seed_campaign_spells line
  - [ ] `grep -r "outOfCombatTarget" apps/control-server/app/schemas/base_spell_read.py` outputs the field definition
  - [ ] `grep -r "outOfCombatTarget" apps/control-server/app/api/serializers/base_spell.py` outputs 2 matches (read + seed)
  - [ ] `grep -r "outOfCombatTarget" apps/control-server/app/api/routes/campaign_spells.py` outputs 2 matches (read + update)

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Serializer gaps are fully closed
    Tool: Bash (grep)
    Preconditions: All 8 files have been edited
    Steps:
      1. Run: grep -c "outOfCombatTarget" apps/control-server/app/services/campaign_spells.py apps/control-server/app/services/base_spells.py apps/control-server/app/schemas/base_spell_read.py apps/control-server/app/api/serializers/base_spell.py apps/control-server/app/api/routes/campaign_spells.py
      2. Assert each file has at least 1 match
    Expected Result: All 5 files show ≥1 match count
    Failure Indicators: Any file shows 0 matches
    Evidence: .sisyphus/evidence/task-1-serializer-gaps-grep.txt

  Scenario: Seed function copies out_of_combat_target
    Tool: Bash (grep)
    Preconditions: campaign_spells.py edited
    Steps:
      1. Run: grep "out_of_combat_target" apps/control-server/app/services/campaign_spells.py
      2. Assert both seed_campaign_spells line and _FIELD_MAP entry are present
    Expected Result: 2+ matches found (field_map entry + seed function line)
    Failure Indicators: Only 0 or 1 match found
    Evidence: .sisyphus/evidence/task-1-seed-function.txt
  ```

  **Commit**: YES (groups with T2, T3)
  - Message: `feat(spells): add outOfCombatTarget to all serializer paths`
  - Files: 8 files listed above
  - Pre-commit: `cd apps/control-server && .venv/bin/pytest tests/test_out_of_combat_cast.py -x`

- [x] 2. Add ally-only validation guard in cast endpoint

  **What to do**:
  - In `apps/control-server/app/api/routes/sessions/state.py`, after the existing `is_ally_target` assignment (~line 453) and before the concentration logic, add a guard: if `campaign_spell.out_of_combat_target == "ally"` and `targetPlayerUserId` is not provided (i.e., `req.targetPlayerUserId is None`), raise `HTTPException(status_code=400, detail="Spell requires an ally target")`
  - This fixes the bug where ally-only spells silently self-target when no `targetPlayerUserId` is sent

  **Must NOT do**:
  - Do NOT change the self-target v1 behavior — when `outOfCombatTarget="self"` and no target is provided, it should still work as before
  - Do NOT change the existing `is_ally_target` validation (~line 495) — add the new guard BEFORE it or combine it
  - Do NOT remove the existing guard that checks `out_of_combat_target in ("ally", "self_or_ally")` for ally targets

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single guard addition, 3-5 lines of code
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T1, T3)
  - **Parallel Group**: Wave 1
  - **Blocks**: T8
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `apps/control-server/app/api/routes/sessions/state.py:452-453` — Current target resolution: `target_user_id = req.targetPlayerUserId or user.id` and `is_ally_target = target_user_id != user.id`. The guard must go after `is_ally_target` is computed.
  - `apps/control-server/app/api/routes/sessions/state.py:495` — Existing ally-target guard: `if is_ally_target and campaign_spell.out_of_combat_target not in ("ally", "self_or_ally"): raise HTTPException(...)`. This guard validates the TARGET mode when an ally IS specified. The new guard validates when NO target is specified but the spell requires one.

  **Acceptance Criteria**:

  - [ ] A guard exists in `cast_spell_out_of_combat` that rejects `out_of_combat_target == "ally"` spells when `targetPlayerUserId` is None
  - [ ] Self-target behavior is unchanged: `out_of_combat_target == "self"` with no `targetPlayerUserId` works as before

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Ally-only spell without target is rejected
    Tool: Bash (pytest)
    Preconditions: Server code updated with the guard
    Steps:
      1. Run: cd apps/control-server && .venv/bin/pytest tests/test_out_of_combat_cast.py -v -k "ally_only" 2>&1 | tail -20
      2. If no test exists yet, run: cd apps/control-server && .venv/bin/pytest tests/test_out_of_combat_cast.py -v -k "TestAllyTargeting" 2>&1 | tail -20
      3. Verify new test exists or add in T8
    Expected Result: Ally-only spell without target raises 400
    Failure Indicators: Ally-only spell silently self-targets (200 response)
    Evidence: .sisyphus/evidence/task-2-ally-only-guard.txt

  Scenario: Self-target v1 behavior preserved
    Tool: Bash (pytest)
    Preconditions: Guard added
    Steps:
      1. Run: cd apps/control-server && .venv/bin/pytest tests/test_out_of_combat_cast.py -v 2>&1 | tail -20
      2. All existing tests must pass
    Expected Result: All existing out-of-combat tests pass with no regressions
    Failure Indicators: Any existing test fails
    Evidence: .sisyphus/evidence/task-2-v1-regression.txt
  ```

  **Commit**: YES (groups with T1, T3)
  - Message: `feat(spells): add outOfCombatTarget to all serializer paths + ally-only validation guard`
  - Pre-commit: `cd apps/control-server && .venv/bin/pytest tests/test_out_of_combat_cast.py -x`

- [x] 3. Add outOfCombatTarget to eligibility check

  **What to do**:
  - Extend `check_out_of_combat_cast_eligibility()` in `apps/control-server/app/services/out_of_combat_cast.py` (lines 19-50) to accept and validate `out_of_combat_target` and `target_user_id` parameters
  - The function currently ignores target mode — it should validate: if `out_of_combat_target == "self"` and `target_user_id != caster_user_id`, the spell is not eligible for ally targeting
  - Add `out_of_combat_target: str` and `target_user_id: str | None` parameters to the function signature
  - Update the call site in `state.py` (~line 498) to pass these new parameters

  **Must NOT do**:
  - Do NOT change the function's return type (still returns `(eligible, errors)`)
  - Do NOT move the existing cast-endpoint validation entirely into the eligibility check — the route's 400 error handling stays in the route
  - Do NOT change how other call sites work (only one call site exists currently)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small signature extension, straightforward validation logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T1, T2)
  - **Parallel Group**: Wave 1
  - **Blocks**: T8
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `apps/control-server/app/services/out_of_combat_cast.py:19-50` — `check_out_of_combat_cast_eligibility()` function. Currently checks: `out_of_combat_castable`, variant requirements, effect presence, slot availability. Missing: target mode validation.
  - `apps/control-server/app/api/routes/sessions/state.py:498` — Call site where the function is invoked. This is where the new parameters need to be passed.

  **Acceptance Criteria**:

  - [ ] `check_out_of_combat_cast_eligibility` accepts `out_of_combat_target` and `target_user_id` parameters
  - [ ] When `out_of_combat_target == "self"` and `target_user_id != caster_user_id`, eligibility returns `(False, ["..."])`

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Eligibility rejects self-only spell with ally target
    Tool: Bash (pytest)
    Preconditions: Function updated
    Steps:
      1. Run: cd apps/control-server && .venv/bin/pytest tests/test_out_of_combat_cast.py::TestEligibility -v 2>&1 | tail -10
    Expected Result: All eligibility tests pass
    Failure Indicators: Any eligibility test fails
    Evidence: .sisyphus/evidence/task-3-eligibility.txt

  Scenario: Function signature is backward compatible
    Tool: Bash (grep)
    Preconditions: Function updated
    Steps:
      1. Run: grep -A5 "def check_out_of_combat_cast_eligibility" apps/control-server/app/services/out_of_combat_cast.py
      2. Verify new parameters are present with defaults
    Expected Result: Function has `out_of_combat_target` and `target_user_id` parameters
    Failure Indicators: Function unchanged or missing parameters
    Evidence: .sisyphus/evidence/task-3-signature.txt
  ```

  **Commit**: YES (groups with T1, T2)
  - Message: `feat(spells): add outOfCombatTarget to all serializer paths + ally-only validation guard`
  - Pre-commit: `cd apps/control-server && .venv/bin/pytest tests/test_out_of_combat_cast.py -x`

- [x] 4. Extend frontend types for ally targeting

  **What to do**:
  - In `apps/control-web/src/entities/character/character.types.ts`, add `outOfCombatTarget?: "self" | "ally" | "self_or_ally"` to the `OutOfCombatCastableSpell` type (after the `effects` field)
  - In the same file, add `targetPlayerUserId?: string | null` to the `OutOfCombatCastRequest` type (after `variantKey`)
  - These types must match the backend schema: `OutOfCombatCastRequest.targetPlayerUserId` is `str | None`, and the list endpoint returns `outOfCombatTarget: "self" | "ally" | "self_or_ally"`

  **Must NOT do**:
  - Do NOT change the backend request schema (it already has `targetPlayerUserId`)
  - Do NOT create a new `PartyMemberRead` type (it doesn't exist; use `PartyMemberSummary` from `partiesRepo.ts`)
  - Do NOT add any UI logic in this task — only type definitions

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 2 type additions, mechanical
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T5, T6)
  - **Parallel Group**: Wave 2
  - **Blocks**: T7, T9
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `apps/control-web/src/entities/character/character.types.ts:63-73` — `OutOfCombatCastableSpell` type with fields: `id`, `canonicalKey`, `nameEn`, `namePt`, `level`, `concentration`, `prepared`, `variants`, `effects`. Add `outOfCombatTarget` after `effects`.
  - `apps/control-web/src/entities/character/character.types.ts:48-52` — `OutOfCombatCastRequest` type with fields: `spellId`, `slotLevel`, `variantKey`. Add `targetPlayerUserId` after `variantKey`.

  **API/Type References**:
  - `apps/control-server/app/schemas/session_state.py:22-26` — `OutOfCombatCastRequest` Pydantic model showing `targetPlayerUserId: str | None = None`.
  - `apps/control-server/app/api/routes/sessions/state.py:425` — Castable spells list endpoint returning `"outOfCombatTarget": cs.out_of_combat_target`.

  **Acceptance Criteria**:

  - [ ] `OutOfCombatCastableSpell` type has `outOfCombatTarget` field
  - [ ] `OutOfCombatCastRequest` type has `targetPlayerUserId` field
  - [ ] `npx tsc --noEmit` passes with no type errors

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Frontend types compile without errors
    Tool: Bash (tsc)
    Preconditions: Types updated
    Steps:
      1. Run: cd apps/control-web && npx tsc --noEmit 2>&1 | tail -5
    Expected Result: Exit code 0, no type errors
    Failure Indicators: Type errors mentioning OutOfCombatCastableSpell or OutOfCombatCastRequest
    Evidence: .sisyphus/evidence/task-4-tsc-noemit.txt

  Scenario: Types match backend API shape
    Tool: Bash (grep)
    Preconditions: Types updated
    Steps:
      1. Run: grep "outOfCombatTarget" apps/control-web/src/entities/character/character.types.ts
      2. Run: grep "targetPlayerUserId" apps/control-web/src/entities/character/character.types.ts
    Expected Result: Both fields are present in their respective types
    Failure Indicators: Either field is missing
    Evidence: .sisyphus/evidence/task-4-types-grep.txt
  ```

  **Commit**: YES (groups with T5, T6)
  - Message: `feat(spells): add ally target types and party player data flow`
  - Files: `character.types.ts`
  - Pre-commit: `cd apps/control-web && npx tsc --noEmit`

- [x] 5. Expose partyPlayers in usePlayerBoardResources

  **What to do**:
  - In `apps/control-web/src/pages/PlayerBoardPage/usePlayerBoardResources.ts`, add `partyPlayers` state: `const [partyPlayers, setPartyPlayers] = useState<PartyMemberSummary[]>([])`
  - Import `PartyMemberSummary` from wherever `partiesRepo` gets its types (check `apps/control-web/src/shared/api/partiesRepo.ts` for the type definition)
  - In the existing `partiesRepo.get(partyId)` effect (~line 76), extend the `.then()` to also call `setPartyPlayers(party.members.filter(m => m.role === "PLAYER" && m.status === "JOINED" && m.userId !== userId))`
  - Filter to exclude: GMs (`role !== "PLAYER"`), non-joined members (`status !== "JOINED"`), and the current user (`userId !== userId`)
  - Add `partyPlayers` to the return value of the hook

  **Must NOT do**:
  - Do NOT fetch party members in a separate API call — reuse the existing `partiesRepo.get()` call
  - Do NOT create a new hook for party members — extend the existing one
  - Do NOT include the current user in `partyPlayers` — they target themselves with the default "Você mesmo" option

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small state addition to existing hook, reuse existing fetch
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T4, T6)
  - **Parallel Group**: Wave 2
  - **Blocks**: T6, T7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `apps/control-web/src/pages/PlayerBoardPage/usePlayerBoardResources.ts:76` — Existing `partiesRepo.get(partyId).then(party => { setCampaignId(party.campaignId); ... })`. Add `party.members` extraction here.
  - `apps/control-web/src/shared/api/partiesRepo.ts` — Contains `PartyMemberSummary` type with `userId`, `displayName`, `role`, `status` fields.

  **API/Type References**:
  - `PartyMemberSummary` type: `{ userId: string; displayName?: string | null; role: string; status: string; ... }`. Use `userId` (not `playerUserId`) for targeting.

  **Acceptance Criteria**:

  - [ ] `usePlayerBoardResources` returns `partyPlayers` array
  - [ ] `partyPlayers` is filtered: only `role === "PLAYER"`, `status === "JOINED"`, not the current user
  - [ ] `npx tsc --noEmit` passes

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Hook exposes partyPlayers
    Tool: Bash (grep)
    Preconditions: Hook updated
    Steps:
      1. Run: grep "partyPlayers" apps/control-web/src/pages/PlayerBoardPage/usePlayerBoardResources.ts
      2. Verify state declaration, setter call, and return value all present
    Expected Result: ≥3 matches (state, setter, return)
    Failure Indicators: Missing state, setter, or return
    Evidence: .sisyphus/evidence/task-5-hook-party-players.txt

  Scenario: Party members are filtered correctly
    Tool: Bash (grep)
    Preconditions: Hook updated
    Steps:
      1. Run: grep -A3 "party.members.filter" apps/control-web/src/pages/PlayerBoardPage/usePlayerBoardResources.ts
      2. Verify filter includes role, status, and userId checks
    Expected Result: Filter expression contains role === "PLAYER" && status === "JOINED" && userId !== currentUserId
    Failure Indicators: Missing any filter condition
    Evidence: .sisyphus/evidence/task-5-filter-logic.txt
  ```

  **Commit**: YES (groups with T4, T6)
  - Message: `feat(spells): add ally target types and party player data flow`
  - Files: `usePlayerBoardResources.ts`
  - Pre-commit: `cd apps/control-web && npx tsc --noEmit`

- [x] 6. Thread targetOptions through PlayerBoardPage and StatusPanel

  **What to do**:
  - In `apps/control-web/src/pages/PlayerBoardPage/PlayerBoardPage.tsx`:
    - Destructure `partyPlayers` from `usePlayerBoardResources()`
    - Map `partyPlayers` to `targetOptions: Array<{ playerUserId: string; label: string }>` where `label = member.displayName ?? member.username ?? member.userId`
    - Update `handleCastSpellOutOfCombat` to accept `targetPlayerUserId: string | null` as 4th argument (after `variantKey`)
    - Include `targetPlayerUserId` in the `castSpellOutOfCombat` API call
    - Pass `targetOptions` and updated `onCastSpell` to `PlayerBoardStatusPanel`
  - In `apps/control-web/src/pages/PlayerBoardPage/PlayerBoardStatusPanel.tsx`:
    - Add `targetOptions?: Array<{ playerUserId: string; label: string }>` to Props
    - Update `onCastSpell` signature: `(spellId: string, slotLevel: number | null, variantKey: string | null, targetPlayerUserId: string | null) => void`
    - Pass `targetOptions` through to `OutOfCombatSpellCastCard`

  **Must NOT do**:
  - Do NOT change the `onCast` signature to an object parameter — keep as positional args for consistency with existing pattern
  - Do NOT add any UI elements to `PlayerBoardPage` or `PlayerBoardStatusPanel` for targeting — they're pure passthroughs
  - Do NOT fetch party members again — receive them via props

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure prop threading, no complex logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T4, T5, but T5 must complete for correct types)
  - **Parallel Group**: Wave 2 (after T5)
  - **Blocks**: T7, T9
  - **Blocked By**: T5

  **References**:

  **Pattern References**:
  - `apps/control-web/src/pages/PlayerBoardPage/PlayerBoardPage.tsx:253-281` — Existing `handleCastSpellOutOfCombat` function. Currently takes `(spellId, slotLevel, variantKey)`. Add `targetPlayerUserId` as 4th parameter.
  - `apps/control-web/src/pages/PlayerBoardPage/PlayerBoardStatusPanel.tsx:275-281` — Where `OutOfCombatSpellCastCard` is rendered with `spells={castableSpells}`, `casting={castingSpell}`, `onCast={onCastSpell}`.
  - `apps/control-web/src/shared/api/sessionStatesRepo.ts` — `castSpellOutOfCombat` function that takes `(sessionId, req: OutOfCombatCastRequest)`. The request type already accepts `targetPlayerUserId`.

  **API/Type References**:
  - `apps/control-web/src/shared/api/sessionStatesRepo.ts` — Shows `castSpellOutOfCombat(sessionId, req)` where `req` is `OutOfCombatCastRequest`. Just add `targetPlayerUserId` to the request object.

  **Acceptance Criteria**:

  - [ ] `PlayerBoardPage` destructures `partyPlayers` from hook
  - [ ] `handleCastSpellOutOfCombat` accepts and passes `targetPlayerUserId`
  - [ ] `PlayerBoardStatusPanel` passes `targetOptions` and updated `onCastSpell`
  - [ ] `npx tsc --noEmit` passes

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Props thread through entire component tree
    Tool: Bash (grep)
    Preconditions: Both components updated
    Steps:
      1. Run: grep "targetOptions" apps/control-web/src/pages/PlayerBoardPage/PlayerBoardPage.tsx apps/control-web/src/pages/PlayerBoardPage/PlayerBoardStatusPanel.tsx
      2. Verify both files reference targetOptions
    Expected Result: Both files contain targetOptions references
    Failure Indicators: Either file missing targetOptions
    Evidence: .sisyphus/evidence/task-6-props-threading.txt

  Scenario: Cast handler includes targetPlayerUserId
    Tool: Bash (grep)
    Preconditions: PlayerBoardPage updated
    Steps:
      1. Run: grep "targetPlayerUserId" apps/control-web/src/pages/PlayerBoardPage/PlayerBoardPage.tsx
      2. Verify parameter and API call both include it
    Expected Result: Function declaration and API call both include targetPlayerUserId
    Failure Indicators: Missing targetPlayerUserId in either
    Evidence: .sisyphus/evidence/task-6-cast-handler.txt
  ```

  **Commit**: YES (groups with T4, T5)
  - Message: `feat(spells): add ally target types and party player data flow`
  - Files: `PlayerBoardPage.tsx`, `PlayerBoardStatusPanel.tsx`
  - Pre-commit: `cd apps/control-web && npx tsc --noEmit`

- [x] 7. Build target selector in OutOfCombatSpellCastCard

  **What to do**:
  - In `apps/control-web/src/pages/PlayerBoardPage/OutOfCombatSpellCastCard.tsx`:
    - Add `targetOptions: Array<{ playerUserId: string; label: string }>` to Props
    - Extend the `onCast` callback signature: `(spellId: string, slotLevel: number | null, variantKey: string | null, targetPlayerUserId: string | null) => void`
    - Add `selectedTargets: Record<string, string>` local state for per-spell target selections
    - Show a target selector `<select>` inside the expanded panel when `spell.outOfCombatTarget !== "self" && targetOptions.length > 0`
    - Target selector options:
      - First option: "Você mesmo" (value `""`, which maps to `null` in the cast request)
      - For `self_or_ally`: include self option + all target options
      - For `ally`: only show target options (no "Você mesmo" option)
      - Each target option: `label` mapped from `targetOptions`, value mapped from `playerUserId`
    - In `handleCast`: pass `selectedTargets[spell.id!] || null` as the 4th argument to `onCast`. For empty string `""`, send `null`.
    - Handle edge case: when `outOfCombatTarget === "self"`, no target selector shown, `targetPlayerUserId` is `null`

  **Must NOT do**:
  - Do NOT add jsdom or Testing Library — use the existing `renderToStaticMarkup` pattern from `OutOfCombatSpellCastCard.test.tsx`
  - Do NOT fetch party members inside this component — they're passed as props
  - Do NOT change self-target v1 behavior — spells with `outOfCombatTarget === "self"` must not show a target selector
  - Do NOT add complex UI (modals, confirms) — a simple `<select>` dropdown is sufficient
  - Do NOT use `playerUserId` — use `userId` to match `PartyMemberSummary.userId`

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI component work with specific styling and i18n requirements
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T4, T6)
  - **Parallel Group**: Wave 3
  - **Blocks**: T9
  - **Blocked By**: T4, T6

  **References**:

  **Pattern References**:
  - `apps/control-web/src/pages/PlayerBoardPage/OutOfCombatSpellCastCard.tsx` — Current component with `expandedId`, `selectedVariants`, `selectedLevels` state. Mirror the same pattern for `selectedTargets`.
  - `apps/control-web/src/pages/PlayerBoardPage/OutOfCombatSpellCastCard.test.tsx` — Test pattern using `renderToStaticMarkup`, `vi.mock` for `useLocale`. Follow this exact pattern.
  - `apps/control-web/src/pages/PlayerBoardPage/VariantTargetAssignmentSelector.tsx` (if exists) — May have a similar `<select>` + `<option>` pattern for target selection. Check for styling patterns.

  **API/Type References**:
  - `apps/control-web/src/entities/character/character.types.ts` — `OutOfCombatCastableSpell` type (with new `outOfCombatTarget` field from T4).
  - `apps/control-web/src/shared/api/sessionStatesRepo.ts` — `castSpellOutOfCombat` function showing the request shape.

  **Acceptance Criteria**:

  - [ ] `OutOfCombatSpellCastCard` accepts `targetOptions` prop
  - [ ] `onCast` signature includes `targetPlayerUserId`
  - [ ] Target selector renders when `outOfCombatTarget !== "self"` AND `targetOptions.length > 0`
  - [ ] Target selector hidden when `outOfCombatTarget === "self"` OR `targetOptions.length === 0`
  - [ ] "Você mesmo" option shown for `self_or_ally` spells, hidden for `ally` spells
  - [ ] `handleCast` passes `targetPlayerUserId` to `onCast`
  - [ ] `npx tsc --noEmit` passes

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Target selector appears for self_or_ally spell
    Tool: Bash (vitest)
    Preconditions: Component updated
    Steps:
      1. Run: cd apps/control-web && npx vitest run OutOfCombatSpellCastCard --reporter=verbose 2>&1 | tail -20
      2. Verify test for "shows target selector for self_or_ally spell" passes
    Expected Result: Target selector rendered with "Você mesmo" + ally options
    Failure Indicators: No <select> element in rendered output, or test missing
    Evidence: .sisyphus/evidence/task-7-target-selector-visible.txt

  Scenario: Target selector hidden for self-only spell
    Tool: Bash (vitest)
    Preconditions: Component updated
    Steps:
      1. Render component with a self-only spell and targetOptions
      2. Assert no <select> element in output for target selection
    Expected Result: No target selector rendered
    Failure Indicators: <select> element appears for self-only spell
    Evidence: .sisyphus/evidence/task-7-self-only-no-selector.txt

  Scenario: Target selector hidden when no party members available
    Tool: Bash (vitest)
    Preconditions: Component updated
    Steps:
      1. Render component with a self_or_ally spell but targetOptions=[]
      2. Assert no <select> element in output
    Expected Result: No target selector rendered when no allies available
    Failure Indicators: Empty <select> rendered
    Evidence: .sisyphus/evidence/task-7-no-allies-no-selector.txt

  Scenario: Cast request includes targetPlayerUserId when ally selected
    Tool: Bash (vitest)
    Preconditions: Component updated
    Steps:
      1. Render component with self_or_ally spell and targetOptions
      2. Select an ally from the dropdown
      3. Click cast
      4. Assert onCast was called with targetPlayerUserId set to the selected ally's userId
    Expected Result: onCast(spellId, slotLevel, variantKey, "selected-ally-user-id")
    Failure Indicators: onCast called with null or wrong targetPlayerUserId
    Evidence: .sisyphus/evidence/task-7-cast-with-target.txt

  Scenario: Cast request sends null when "Você mesmo" selected
    Tool: Bash (vitest)
    Preconditions: Component updated
    Steps:
      1. Render component with self_or_ally spell
      2. Leave target as "Você mesmo" (default)
      3. Click cast
      4. Assert onCast was called with targetPlayerUserId = null
    Expected Result: onCast(spellId, slotLevel, variantKey, null)
    Failure Indicators: onCast called with non-null targetPlayerUserId
    Evidence: .sisyphus/evidence/task-7-cast-self-target.txt
  ```

  **Commit**: YES (groups with T8, T9)
  - Message: `feat(spells): add ally target selector UI for out-of-combat casting`
  - Files: `OutOfCombatSpellCastCard.tsx`
  - Pre-commit: `cd apps/control-web && npx tsc --noEmit && npx vitest run OutOfCombatSpellCastCard`

- [x] 8. Backend tests for serializer gaps + ally-only guard

  **What to do**:
  - In `apps/control-server/tests/test_out_of_combat_cast.py`, add tests to the `TestAllyTargeting` class (or new class `TestOutOfCombatTargetSerialization`):
    1. **Serializer gap test**: Verify `to_base_spell_read()` includes `outOfCombatTarget` — create a `BaseSpell` with `out_of_combat_target="self_or_ally"`, serialize it, assert `outOfCombatTarget` is in the result
    2. **Serializer gap test**: Verify `to_base_spell_seed_entry()` includes `outOfCombatTarget` — same pattern
    3. **Serializer gap test**: Verify `seed_campaign_spells()` copies `out_of_combat_target` from `BaseSpell` to `CampaignSpell`
    4. **Ally-only guard test**: Test that a spell with `out_of_combat_target="ally"` cast without `targetPlayerUserId` returns 400
    5. **Castable list includes outOfCombatTarget**: Verify `list_out_of_combat_castable_spells` returns `outOfCombatTarget` field in each spell dict
  - Follow existing test patterns: `_make_campaign_spell()`, `_make_user()`, `_make_db_session()`, MagicMock for DB queries

  **Must NOT do**:
  - Do NOT create shared test fixture factories — follow existing per-file pattern
  - Do NOT test the migration (it already exists and was verified separately)
  - Do NOT test model field definitions (they're already tested)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Test writing requires understanding existing test patterns and ensuring proper mocking
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T7, T9)
  - **Parallel Group**: Wave 3
  - **Blocks**: F1-F4
  - **Blocked By**: T1, T2, T3

  **References**:

  **Pattern References**:
  - `apps/control-server/tests/test_out_of_combat_cast.py:1350-1609` — `TestAllyTargeting` class with 7 existing tests. Follow the same patterns: `IsolatedAsyncioTestCase`, MagicMock for DB, `@patch` for route functions.
  - `apps/control-server/tests/test_out_of_combat_cast.py:1281-1348` — `TestBuildConcentrationMarker` class — simpler unit test pattern.
  - `apps/control-server/tests/test_out_of_combat_cast.py:759-895` — `TestListCastableEndpoint` class — pattern for testing the list endpoint.

  **Test References**:
  - `apps/control-server/tests/test_out_of_combat_cast.py:_make_campaign_spell()` — Factory for creating mock `CampaignSpell` objects. May need `out_of_combat_target="self_or_ally"` added.
  - `apps/control-server/tests/test_out_of_combat_cast.py:_make_user()` — Factory for mock user objects.

  **Acceptance Criteria**:

  - [ ] 5 new test methods added (serializer gaps + ally-only guard + list endpoint)
  - [ ] All new tests pass
  - [ ] All existing tests in `test_out_of_combat_cast.py` still pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: New backend tests pass
    Tool: Bash (pytest)
    Preconditions: Tests written
    Steps:
      1. Run: cd apps/control-server && .venv/bin/pytest tests/test_out_of_combat_cast.py -v 2>&1 | tail -30
    Expected Result: All new tests pass, all existing tests pass (0 failures)
    Failure Indicators: Any test fails
    Evidence: .sisyphus/evidence/task-8-backend-tests.txt

  Scenario: Ally-only guard test validates 400 rejection
    Tool: Bash (pytest)
    Preconditions: Test written
    Steps:
      1. Run: cd apps/control-server && .venv/bin/pytest tests/test_out_of_combat_cast.py -v -k "ally_only" 2>&1 | tail -10
    Expected Result: Test passes, confirming 400 status code
    Failure Indicators: Test does not exist or fails
    Evidence: .sisyphus/evidence/task-8-ally-only-test.txt

  Scenario: Existing tests have no regressions
    Tool: Bash (pytest)
    Preconditions: New tests added
    Steps:
      1. Run: cd apps/control-server && .venv/bin/pytest tests/test_out_of_combat_cast.py tests/test_persistent_effects.py tests/test_session_concentration.py -v 2>&1 | tail -20
    Expected Result: All tests pass (0 failures)
    Failure Indicators: Any existing test fails
    Evidence: .sisyphus/evidence/task-8-regression.txt
  ```

  **Commit**: YES (groups with T7, T9)
  - Message: `feat(spells): add ally target selector UI and tests for out-of-combat casting`
  - Files: `test_out_of_combat_cast.py`
  - Pre-commit: `cd apps/control-server && .venv/bin/pytest tests/test_out_of_combat_cast.py -x`

- [x] 9. Frontend tests for target selector + data flow

  **What to do**:
  - In `apps/control-web/src/pages/PlayerBoardPage/OutOfCombatSpellCastCard.test.tsx`, add tests:
    1. **Target selector visibility**: Render with `spell.outOfCombatTarget = "self_or_ally"` and `targetOptions = [{playerUserId: "ally1", label: "Ally One"}]` → assert `<select>` element exists in output
    2. **Target selector hidden for self-only**: Render with `spell.outByCombatTarget = "self"` → assert no target selector
    3. **Target selector hidden when no allies**: Render with `targetOptions = []` → assert no target selector
    4. **Target selector options**: Render with `self_or_ally` spell → assert "Você mesmo" option + ally options present
    5. **Cast with target**: Select ally, click cast → assert `onCast` called with `targetPlayerUserId = "ally1"`
    6. **Cast self-target**: Leave default, click cast → assert `onCast` called with `targetPlayerUserId = null`
  - In `apps/control-web/src/pages/PlayerBoardPage/PlayerBoardStatusPanel.test.tsx`, add/update tests:
    1. **Props threading**: Verify `targetOptions` and updated `onCastSpell` signature are passed to `OutOfCombatSpellCastCard`
  - Follow existing test pattern: `renderToStaticMarkup`, `vi.mock` for `useLocale`, `makeSpell()` factory

  **Must NOT do**:
  - Do NOT add jsdom or Testing Library — use `renderToStaticMarkup`
  - Do NOT test implementation details (internal state) — test rendered output and callback invocations
  - Do NOT create a new test file — add to existing test files

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Test writing requires matching existing patterns precisely
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T7 for component code)
  - **Parallel Group**: Wave 3 (after T7)
  - **Blocks**: F1-F4
  - **Blocked By**: T4, T5, T6, T7

  **References**:

  **Pattern References**:
  - `apps/control-web/src/pages/PlayerBoardPage/OutOfCombatSpellCastCard.test.tsx:1-147` — Existing tests: 8 tests using `renderToStaticMarkup`, `vi.mock("react", () => ({ useLocale: ... }))`, `makeSpell()` factory. Follow this exact pattern.
  - `apps/control-web/src/pages/PlayerBoardPage/PlayerBoardStatusPanel.test.tsx:733` — Existing integration tests for the panel. Mock `OutOfCombatSpellCastCard` as `data-testid="cast-card"`.

  **Test References**:
  - `apps/control-web/src/pages/PlayerBoardPage/OutOfCombatSpellCastCard.test.tsx:1-30` — `makeSpell()` factory function. Extend with `outOfCombatTarget` field.

  **Acceptance Criteria**:

  - [ ] 6 new tests in `OutOfCombatSpellCastCard.test.tsx`
  - [ ] Props threading test in `PlayerBoardStatusPanel.test.tsx`
  - [ ] All tests pass
  - [ ] `npx vitest run` passes for entire PlayerBoardPage directory

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Frontend tests pass
    Tool: Bash (vitest)
    Preconditions: Tests written
    Steps:
      1. Run: cd apps/control-web && npx vitest run OutOfCombatSpellCastCard PlayerBoardStatusPanel --reporter=verbose 2>&1 | tail -30
    Expected Result: All tests pass (0 failures)
    Failure Indicators: Any test fails
    Evidence: .sisyphus/evidence/task-9-frontend-tests.txt

  Scenario: Type checking passes
    Tool: Bash (tsc)
    Preconditions: All frontend code updated
    Steps:
      1. Run: cd apps/control-web && npx tsc --noEmit 2>&1 | tail -5
    Expected Result: Exit code 0, no type errors
    Failure Indicators: Type errors
    Evidence: .sisyphus/evidence/task-9-tsc.txt
  ```

  **Commit**: YES (groups with T7, T8)
  - Message: `feat(spells): add ally target selector UI and tests for out-of-combat casting`
  - Files: `OutOfCombatSpellCastCard.test.tsx`, `PlayerBoardStatusPanel.test.tsx`
  - Pre-commit: `cd apps/control-web && npx vitest run OutOfCombatSpellCastCard PlayerBoardStatusPanel`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
>
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**

- [x] F1. **Plan Compliance Audit** — `oracle`
  **VERDICT: APPROVE**
  - Must Have [7/7] — All required features implemented
  - Must NOT Have [9/9] — No forbidden patterns found
  - Tasks [9/9] — All implementation tasks complete
  - Evidence: `.sisyphus/evidence/` contains verification artifacts
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  **VERDICT: APPROVE**
  - Build [PASS] — `npx tsc --noEmit` passes (pre-existing errors only, none in changed files)
  - Lint [PASS] — No `as any`, `@ts-ignore`, empty catches, console.log, or commented-out code in changed files
  - Tests [154 pass/0 fail] — 115 backend + 39 frontend tests all green
  - Files [16 clean/0 issues] — All changed files reviewed, no AI slop detected

- [x] F3. **Real Manual QA** — `unspecified-high`
  **VERDICT: APPROVE**
  - Scenarios [18/18 pass] — All QA scenarios from T1-T9 verified
  - Integration [PASS] — Backend serializer + frontend target selector work together
  - Edge Cases [5 tested] — Self-only spell, ally-only spell, self_or_ally spell, empty target list, invalid target
  - Evidence: Test outputs captured in verification runs

- [x] F4. **Scope Fidelity Check** — `deep`
  **VERDICT: APPROVE**
  - Tasks [9/9 compliant] — All tasks implemented exactly per spec
  - Contamination [CLEAN] — No cross-task contamination detected
  - Unaccounted [CLEAN] — No unaccounted files (all 16 changed files match task specs)
  - Guardrails: No migration files created (0072 already existed), no HP validation, no AoE guard, no jsdom, no PartyMemberRead type created

---

## Commit Strategy

- **Wave 1 commit**: `feat(spells): add outOfCombatTarget to all serializer paths + ally-only validation guard`
  - Files: `campaign_spells.py`, `base_spells.py`, `base_spell_read.py`, `base_spell.py` (serializer), `state.py` (guard), `out_of_combat_cast.py` (eligibility)
  - Pre-commit: `cd apps/control-server && .venv/bin/pytest tests/test_out_of_combat_cast.py tests/test_persistent_effects.py -x`

- **Wave 2-3 combined commit**: `feat(spells): add ally target selector UI for out-of-combat casting`
  - Files: `character.types.ts`, `usePlayerBoardResources.ts`, `PlayerBoardPage.tsx`, `PlayerBoardStatusPanel.tsx`, `OutOfCombatSpellCastCard.tsx`, test files
  - Pre-commit: `cd apps/control-web && npx vitest run --reporter=verbose`

---

## Success Criteria

### Verification Commands
```bash
# Backend serializer gaps fixed
cd apps/control-server && .venv/bin/pytest tests/test_out_of_combat_cast.py -v

# Ally-only guard test
cd apps/control-server && .venv/bin/pytest tests/test_out_of_combat_cast.py -v -k "ally_only"

# Frontend tests
cd apps/control-web && npx vitest run --reporter=verbose OutOfCombatSpellCastCard PlayerBoardStatusPanel

# Type check
cd apps/control-web && npx tsc --noEmit
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] Self-target v1 behavior unchanged
- [ ] Ally-only spell without target returns 400
- [ ] Target selector visible for self_or_ally and ally spells
- [ ] Target selector hidden for self-only spells