# Learnings: Fix 8 serializer gaps for outOfCombatTarget

## 2026-05-05: T6 — Thread targetOptions through PlayerBoardPage → Panel → Card

- **Files modified (5 total):** `PlayerBoardPage.tsx`, `PlayerBoardStatusPanel.tsx`, `OutOfCombatSpellCastCard.tsx`, `enUS/playerBoard.ts`, `ptBR/playerBoard.ts`
- **Flow:** `PlayerBoardPage` destructures `partyPlayers` from `usePlayerBoardResources()`, maps to `targetOptions: Array<{ playerUserId, label }>`, passes to `PlayerBoardStatusPanel` → `OutOfCombatSpellCastCard`
- **Cast handler:** 4th positional arg `targetPlayerUserId: string | null` added to `onCast`/`onCastSpell` callbacks
- **API call:** `targetPlayerUserId` included in the `OutOfCombatCastRequest` object (field already existed from T4)
- **Card UI:** New dropdown for target selection appears when `targetOptions` is provided and non-empty; first option is "Self" (value `""`), then each party member. Selected target stored per-spell-id in `selectedTargets` state.
- **Translation keys added:** `playerBoard.selectTarget`, `playerBoard.targetSelf` added to both `enUS/playerBoard.ts` and `ptBR/playerBoard.ts`
- **Test mocks updated:** Added the two new keys to `OutOfCombatSpellCastCard.test.tsx` mock
- **Verification:** `npx tsc --noEmit` produces zero errors from changed files; all 10 card tests + 19 status panel tests pass

## Completed

Added `outOfCombatTarget` to 8 serialization paths across 5 files:

1. **services/campaign_spells.py** - `_FIELD_MAP`: added `"outOfCombatTarget": "out_of_combat_target"`
2. **services/base_spells.py** - `_FIELD_MAP`: added `"outOfCombatTarget": "out_of_combat_target"`
3. **services/campaign_spells.py** - `seed_campaign_spells()`: added `out_of_combat_target=base_spell.out_of_combat_target`
4. **schemas/base_spell_read.py** - `BaseSpellRead`: added `outOfCombatTarget: str = "self"`
5. **api/serializers/base_spell.py** - `to_base_spell_read()`: added `outOfCombatTarget=spell.out_of_combat_target`
6. **api/serializers/base_spell.py** - `to_base_spell_seed_entry()`: added `outOfCombatTarget=spell.out_of_combat_target`
7. **api/routes/campaign_spells.py** - `to_campaign_spell_read()`: added `outOfCombatTarget=spell.out_of_combat_target`
8. **api/routes/campaign_spells.py** - `update_spell()` field_map: added `"outOfCombatTarget": "out_of_combat_target"`

## Pattern
- All additions follow the existing `outOfCombatCastable` / `out_of_combat_castable` pattern exactly
- CamelCase in schemas/serializers → snake_case in models/services
- Default value in `BaseSpellRead`: `"self"`
- `BaseSpellWrite` already had the field with validator before this change

## T3: Extend check_out_of_combat_cast_eligibility() target validation

- Added three optional params (`out_of_combat_target`, `target_user_id`, `caster_user_id`) — all default to `None` for backward compat with existing tests
- Validation: when `out_of_combat_target == "self"` and `target_user_id != caster_user_id`, returns `"This spell can only target yourself"`
- Updated the single production call site in `state.py` to pass the new params
- All 48 existing tests pass without modification
- Route-level checks at lines 495-499 in `state.py` still catch the "ally target on self-only spell" case first (the eligibility function validation is defense-in-depth)

## 2026-05-05 — T4: Frontend types for ally targeting

- Added `outOfCombatTarget?: "self" | "ally" | "self_or_ally"` to `OutOfCombatCastableSpell` (line 74)
- Added `targetPlayerUserId?: string | null` to `OutOfCombatCastRequest` (line 52)
- File: `apps/control-web/src/entities/character/character.types.ts`
- Field names match backend API shape (camelCase)
- All pre-existing TS errors — no new errors from these additions

## 2026-05-05: T3 - Exposed partyPlayers in usePlayerBoardResources

- Added `PartyMemberSummary` import and `partyPlayers` state to `usePlayerBoardResources.ts`
- Filtering happens inside the existing `partiesRepo.get(partyId)` `.then()` callback — no new API call
- Filter: `role === "PLAYER" && status === "JOINED" && userId !== currentUserId` (self excluded)
- State is reset to `[]` on cleanup (no partyId, catch, or unmount)
- Returned `partyPlayers` in the hook's return object
- Verified: zero diagnostics on the file, all existing tsc errors are pre-existing in unrelated files

## 2026-05-05: T8 — Frontend tests for target selector and data flow

- **Files modified:** `OutOfCombatSpellCastCard.test.tsx`, `PlayerBoardStatusPanel.test.tsx`, `OutOfCombatSpellCastCard.tsx`
- **Component fix:** Added `spell.outOfCombatTarget !== "self"` guard to target selector render block so "self" spells hide the selector even when allies exist
- **Factory extended:** `makeSpell()` now accepts `outOfCombatTarget` override (type already on `OutOfCombatCastableSpell` from T4)
- **New tests (7):** `OutOfCombatSpellCastCard.test.tsx`
  1. shows target selector for `self_or_ally` spell when allies exist
  2. hides target selector for `self` spell even when allies exist
  3. hides target selector when no allies are available
  4. target selector shows "Você mesmo" + ally options
  5. cast with ally target sends correct `targetPlayerUserId`
  6. cast with self target sends `null` `targetPlayerUserId`
  7. cast without `targetOptions` sends `null` `targetPlayerUserId`
- **Props threading tests (3):** `PlayerBoardStatusPanel.test.tsx`
  1. passes `targetOptions` to `OutOfCombatSpellCastCard`
  2. passes `castingSpell` as `casting` to `OutOfCombatSpellCastCard`
  3. passes `onCastSpell` as `onCast` to `OutOfCombatSpellCastCard`
- **Mock pattern for hooks without jsdom:** Used `vi.mock("react", ...)` to override `useState` with a mutable `mockState.overrides` queue. This lets tests preset `expandedId` and `selectedTargets` while still using `renderToStaticMarkup` for output assertions, or calling the component directly to traverse the React element tree and invoke `onClick` closures.
- **Tree traversal helper:** `findCastButton` recursively walks the React element tree returned by calling the component function directly, matching `type === "button"` and `children === "Conjurar"`.
- **Verification:** All 39 tests pass (17 card + 22 panel). Zero diagnostics on changed TSX files.

## 2026-05-05: T9 — Backend tests for serializer gaps and ally-only guard

- **File modified:** `apps/control-server/tests/test_out_of_combat_cast.py`
- **New tests (4):**
  1. `TestSerializerGaps.test_to_base_spell_read_includes_out_of_combat_target` — verifies `to_base_spell_read()` maps `out_of_combat_target` to `outOfCombatTarget`
  2. `TestSerializerGaps.test_to_base_spell_seed_entry_includes_out_of_combat_target` — verifies `to_base_spell_seed_entry()` maps `out_of_combat_target` to `outOfCombatTarget`
  3. `TestAllyTargeting.test_ally_only_spell_without_target_returns_400` — casts an `out_of_combat_target="ally"` spell with `targetPlayerUserId=None` and asserts 400 with "ally target" in detail
  4. `TestListCastableEndpoint.test_returns_out_of_combat_target_field` — asserts the list endpoint includes `"outOfCombatTarget"` in each returned spell dict
- **Helper added:** `_make_base_spell()` using `MagicMock` with explicit attribute defaults (mirrors `_make_campaign_spell()` pattern). Works because `resolve_spell_automation_metadata_from_catalog` uses `getattr` for all lookups.
- **Pitfall:** `_setup_two_player_cast()` assumes 3 DB exec calls (caster state, target state, campaign spell). When `targetPlayerUserId=None`, the target state lookup is skipped, so only 2 calls happen — using `_setup_two_player_cast()` for ally-only guard tests causes the campaign spell lookup to receive `target_state` instead of the spell, leading to `MagicMock > int` comparison errors in `check_out_of_combat_cast_eligibility()`. Fixed by using a manual 2-call `exec_side` setup.
- **Pitfall:** `_make_campaign_spell()` does not accept `out_of_combat_target` as a constructor param. Must set it on the returned MagicMock after creation: `spell.out_of_combat_target = "ally"`.
- **Verification:** All 52 tests pass (48 existing + 4 new), 12 subtests pass.
