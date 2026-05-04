# Plan: Enforce single out-of-combat concentration group (#213)

## Problem

Multiple concentration groups can coexist in `state_json.active_spell_effects` after combat ends. The backend derives one active concentration but never prevents multiple groups from being persisted simultaneously.

## Solution

Add a pure helper and wire it into persist + restore paths.

---

## Step 1 — Add `enforce_single_persisted_concentration_group` helper

**File:** `apps/control-server/app/services/combat_service/persistent_effects.py`

Add after `clear_persisted_concentration_effects` (after line 207):

```python
def enforce_single_persisted_concentration_group(
    effects: list[dict],
) -> list[dict]:
    """Keep only the newest concentration group; preserve non-concentration effects.

    Selection rule: highest valid ``created_at`` among concentration groups.
    Fallback (missing/invalid timestamps): last concentration group encountered.
    """
    non_concentration: list[dict] = []
    groups: dict[str, list[dict]] = {}           # group_key → [effect, ...]
    group_order: list[str] = []                  # insertion order for fallback

    for effect in effects:
        metadata = effect.get("metadata") or {}
        if not metadata.get("concentration"):
            non_concentration.append(effect)
            continue
        group_key = metadata.get("concentration_group") or _solo_group_key(effect)
        groups.setdefault(group_key, []).append(effect)
        if group_key not in group_order:
            group_order.append(group_key)

    if len(groups) <= 1:
        return list(effects)

    winning = _pick_winning_concentration_group(groups, group_order)
    winning_effects = groups[winning]

    # preserve original order: non-concentration first, then winning group effects
    return non_concentration + winning_effects


def _solo_group_key(effect: dict) -> str:
    """Synthetic key for concentration effects without a concentration_group."""
    return f"__solo__:{effect.get('id', id(effect))}"


def _pick_winning_concentration_group(
    groups: dict[str, list[dict]],
    group_order: list[str],
) -> str:
    best_group: str | None = None
    best_ts: str | None = None
    for gkey in group_order:
        ts = _max_created_at(groups[gkey])
        if ts is None:
            continue
        if best_ts is None or ts > best_ts:
            best_ts = ts
            best_group = gkey
    if best_group is not None:
        return best_group
    # fallback: last group in list order
    return group_order[-1]


def _max_created_at(effects: list[dict]) -> str | None:
    best: str | None = None
    for e in effects:
        ts = e.get("created_at")
        if isinstance(ts, str) and ts:
            if best is None or ts > best:
                best = ts
    return best
```

---

## Step 2 — Wire into `persist_surviving_spell_effects`

**File:** `apps/control-server/app/services/combat_service/persistent_effects.py`

After the `surviving` list comprehension (line 44), normalize before writing:

```python
        surviving = enforce_single_persisted_concentration_group(surviving)
```

Insert between current lines 44 and 45 (after building `surviving`, before `if not surviving`).

---

## Step 3 — Wire into `restore_persisted_effects`

**File:** `apps/control-server/app/services/combat_service/persistent_effects.py`

After reading `persisted` and before the deduplication loop (around line 89), normalize:

```python
    persisted = enforce_single_persisted_concentration_group(persisted)
    if not persisted:
        return
```

Additionally, if normalization changed the list, sync back to `state_json`:

```python
    original_persisted = (session_state.state_json or {}).get("active_spell_effects")
    if isinstance(original_persisted, list) and persisted != original_persisted:
        data = dict(session_state.state_json)
        if persisted:
            data["active_spell_effects"] = persisted
        else:
            data.pop("active_spell_effects", None)
        session_state.state_json = finalize_session_state_data(data)
        flag_modified(session_state, "state_json")
        db.add(session_state)
```

---

## Step 4 — Tests

**File:** `apps/control-server/tests/test_persistent_effects.py`

### 4a. Add import

```python
from app.services.combat_service.persistent_effects import (
    ...,
    enforce_single_persisted_concentration_group,
)
```

### 4b. Add `TestEnforceSinglePersistedConcentrationGroup` class

- `test_no_concentration_effects_unchanged` — all non-conc → returned as-is
- `test_single_concentration_group_unchanged` — one group → returned as-is
- `test_two_groups_keeps_newest_by_created_at` — group A (older ts), group B (newer ts) → only group B
- `test_multiple_effects_in_winning_group_all_kept` — winning group has 3 effects → all 3 returned
- `test_non_concentration_effects_survive` — non-conc effects preserved alongside winning group
- `test_invalid_created_at_falls_back_to_last_group` — no valid timestamps → last group in list order wins
- `test_preserves_original_ordering` — non-conc first, then winning group in original order
- `test_solo_concentration_without_group_key` — concentration effect with no `concentration_group` gets synthetic key, still works

### 4c. Add persist integration tests

- `test_persist_surviving_keeps_only_newest_concentration_group` — two conc groups in surviving → only newest persisted
- `test_persist_surviving_preserves_non_concentration` — conc + non-conc → both in state_json

### 4d. Add restore integration tests

- `test_restore_normalizes_multiple_concentration_groups` — state_json has two groups → only one restored into participant
- `test_restore_syncs_back_to_state_json` — state_json updated when normalization changes list

### 4e. Verify existing clear tests pass unchanged

- `clear_persisted_concentration_effects` tests already verify non-conc survive — no changes needed

---

## Verification

```bash
cd apps/control-server
.venv/bin/pytest tests/test_persistent_effects.py -v
```

## Files changed

- `apps/control-server/app/services/combat_service/persistent_effects.py` — add helper + wire into persist/restore
- `apps/control-server/tests/test_persistent_effects.py` — add ~12 new tests
