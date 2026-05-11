"""Persist and restore manual-duration spell effects across combat boundaries.

`active_spell_effects` in SessionState.state_json is the canonical store for
non-combat spell effects.  Only effects with:
  - kind in {"spell_effect", "temp_ac_bonus"}
  - duration_type == "manual"
are persisted (including concentration effects).  Round-based and turn-based
effects expire naturally during combat.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select as sa_select
from sqlalchemy.orm.attributes import flag_modified

from app.models.session_state import SessionState
from app.services.game_time import get_game_time_seconds
from app.services.session_state_finalize import finalize_session_state_data
from app.services.persistent_effect_expiry import prune_expired_persisted_effects_from_state

if TYPE_CHECKING:
    from app.models.combat import CombatState
    from sqlmodel import Session as DbSession

_PERSISTABLE_KINDS = {"spell_effect", "temp_ac_bonus"}
_PERSISTABLE_DURATION_TYPES = {
    "manual",
    "until_long_rest",
    "until_short_rest",
    "until_removed",
    "timed",
}


def is_mechanical_effect(effect: dict) -> bool:
    metadata = effect.get("metadata")
    if not isinstance(metadata, dict):
        return True
    if metadata.get("mechanical") is False:
        return False
    return True


def _persistable_effects_for_participant(participant: dict) -> list[dict]:
    effects = participant.get("active_effects")
    if not isinstance(effects, list):
        return []
    surviving = [
        effect
        for effect in effects
        if effect.get("kind") in _PERSISTABLE_KINDS
        and effect.get("duration_type") in _PERSISTABLE_DURATION_TYPES
    ]
    return enforce_single_persisted_concentration_group(surviving)


def sync_persisted_effects_from_combat_participants(
    db: DbSession,
    state: CombatState,
    *,
    game_time_seconds: int,
) -> list[SessionState]:
    modified: list[SessionState] = []
    for participant in state.participants:
        if participant.get("kind") != "player":
            continue
        ref_id = participant.get("ref_id")
        if not ref_id:
            continue
        session_state = db.exec(
            sa_select(SessionState).where(
                SessionState.session_id == state.session_id,
                SessionState.player_user_id == ref_id,
            )
        ).first()
        if not session_state:
            continue
        next_data = dict(session_state.state_json or {})
        surviving = _persistable_effects_for_participant(participant)
        if surviving:
            next_data["active_spell_effects"] = surviving
        else:
            next_data.pop("active_spell_effects", None)
        finalized = finalize_session_state_data(
            next_data,
            game_time_seconds=game_time_seconds,
        )
        if finalized == (session_state.state_json or {}):
            continue
        session_state.state_json = finalized
        flag_modified(session_state, "state_json")
        db.add(session_state)
        modified.append(session_state)
    return modified


def persist_surviving_spell_effects(db: DbSession, state: CombatState) -> None:
    """Transfer manual-duration spell effects (including concentration) to state_json.

    Called during end_combat() AFTER concentration has been cleared but BEFORE
    remaining participant effects are wiped.
    """
    sync_persisted_effects_from_combat_participants(
        db,
        state,
        game_time_seconds=get_game_time_seconds(state.session_id, db),
    )


def restore_persisted_effects(
    db: DbSession,
    session_id: str,
    participant: dict,
) -> None:
    """Restore persisted spell effects from state_json into a combat participant.

    Called during start_combat() for each player participant.
    """
    if participant.get("kind") != "player":
        return
    ref_id = participant.get("ref_id")
    if not ref_id:
        return
    session_state = db.exec(
        sa_select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == ref_id,
        )
    ).first()
    if not session_state:
        return
    persisted = (session_state.state_json or {}).get("active_spell_effects")
    if not isinstance(persisted, list) or not persisted:
        return
    current_game_time_seconds = get_game_time_seconds(session_id, db)
    pruned_state = prune_expired_persisted_effects_from_state(
        session_state.state_json,
        current_game_time_seconds,
    )
    if pruned_state != (session_state.state_json or {}):
        session_state.state_json = finalize_session_state_data(
            pruned_state,
            game_time_seconds=current_game_time_seconds,
        )
        flag_modified(session_state, "state_json")
        db.add(session_state)
    persisted = (session_state.state_json or {}).get("active_spell_effects")
    if not isinstance(persisted, list) or not persisted:
        return
    original_persisted = list(persisted)
    persisted = enforce_single_persisted_concentration_group(persisted)
    if not persisted:
        data = dict(session_state.state_json)
        data.pop("active_spell_effects", None)
        session_state.state_json = finalize_session_state_data(
            data,
            game_time_seconds=current_game_time_seconds,
        )
        flag_modified(session_state, "state_json")
        db.add(session_state)
        return
    if persisted != original_persisted:
        data = dict(session_state.state_json)
        data["active_spell_effects"] = persisted
        session_state.state_json = finalize_session_state_data(
            data,
            game_time_seconds=current_game_time_seconds,
        )
        flag_modified(session_state, "state_json")
        db.add(session_state)
    existing = participant.get("active_effects")
    if not isinstance(existing, list):
        existing = []
        participant["active_effects"] = existing
    existing_ids = {e.get("id") for e in existing}
    for effect in persisted:
        if effect.get("id") not in existing_ids:
            existing.append(effect)


def sync_effect_removal_to_state_json(
    db: DbSession,
    session_id: str,
    participant: dict,
    removed_effect_id: str,
) -> None:
    """Remove an effect from state_json.active_spell_effects by id.

    Called from remove_effect() when the target is a player participant.
    """
    if participant.get("kind") != "player":
        return
    ref_id = participant.get("ref_id")
    if not ref_id:
        return
    session_state = db.exec(
        sa_select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == ref_id,
        )
    ).first()
    if not session_state:
        return
    data = dict(session_state.state_json or {})
    persisted = data.get("active_spell_effects")
    if not isinstance(persisted, list):
        return
    filtered = [e for e in persisted if e.get("id") != removed_effect_id]
    if len(filtered) == len(persisted):
        return
    if filtered:
        data["active_spell_effects"] = filtered
    else:
        data.pop("active_spell_effects", None)
    session_state.state_json = finalize_session_state_data(
        data,
        game_time_seconds=get_game_time_seconds(session_id, db),
    )
    flag_modified(session_state, "state_json")
    db.add(session_state)


def remove_persisted_effect(
    state_json: dict | None,
    effect_id: str,
) -> dict:
    """Remove a persisted effect by id.

    If the effect is part of a concentration group, the whole group is removed.
    Idempotent: returns ``state_json`` unchanged if the effect is not found.
    """
    data = dict(state_json or {})
    persisted = data.get("active_spell_effects")
    if not isinstance(persisted, list):
        return data

    target: dict | None = None
    for effect in persisted:
        if effect.get("id") == effect_id:
            target = effect
            break

    if target is None:
        return data

    metadata = target.get("metadata") or {}
    concentration_group = metadata.get("concentration_group")
    if metadata.get("concentration") and isinstance(concentration_group, str) and concentration_group:
        return clear_persisted_concentration_effects(data, concentration_group=concentration_group)

    filtered = [e for e in persisted if e.get("id") != effect_id]
    if len(filtered) == len(persisted):
        return data
    if filtered:
        data["active_spell_effects"] = filtered
    else:
        data.pop("active_spell_effects", None)
    return data


def derive_active_concentration(state_json: dict | None) -> dict | None:
    persisted = (state_json or {}).get("active_spell_effects")
    if not isinstance(persisted, list):
        return None

    first_group: str | None = None
    first_metadata: dict | None = None
    for effect in persisted:
        if not is_mechanical_effect(effect):
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        if not metadata.get("concentration"):
            continue
        first_group = metadata.get("concentration_group")
        first_metadata = metadata
        break

    if first_metadata is None:
        return None

    if isinstance(first_group, str) and first_group:
        grouped = [
            e for e in persisted
            if (e.get("metadata") or {}).get("concentration_group") == first_group
        ]
        effect_ids = [e.get("id") for e in grouped if e.get("id")]
    else:
        effect_ids = [e.get("id") for e in persisted
                      if (e.get("metadata") or {}).get("concentration")
                      and e.get("id")][:1]

    return {
        "spellKey": first_metadata.get("source_spell_key"),
        "spellName": first_metadata.get("source_spell_name"),
        "variantKey": first_metadata.get("selected_variant_key"),
        "variantLabel": first_metadata.get("selected_variant_label"),
        "concentrationGroup": first_group,
        "effectIds": effect_ids,
    }


def clear_persisted_concentration_effects(
    state_json: dict | None,
    *,
    concentration_group: str | None = None,
) -> dict:
    data = dict(state_json or {})
    persisted = data.get("active_spell_effects")
    if not isinstance(persisted, list):
        return state_json if state_json is not None else data

    if concentration_group is not None:
        filtered = [
            e for e in persisted
            if (e.get("metadata") or {}).get("concentration_group") != concentration_group
        ]
    else:
        filtered = [
            e for e in persisted
            if not (e.get("metadata") or {}).get("concentration")
        ]

    if len(filtered) == len(persisted):
        return state_json if state_json is not None else data
    if filtered:
        data["active_spell_effects"] = filtered
    else:
        data.pop("active_spell_effects", None)
    return data


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

    if not groups:
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


def clear_concentration_group_across_session(
    db,
    session_id: str,
    concentration_group: str,
    exclude_user_id: str | None = None,
) -> list[SessionState]:
    """Remove all effects with concentration_group from every SessionState in the
    session, optionally skipping one player (the caster who handles their own state).

    Stages changes via flag_modified but does NOT commit — the caller commits once.
    Returns the list of modified SessionState objects.
    """
    states = db.exec(
        sa_select(SessionState).where(SessionState.session_id == session_id)
    ).all()

    modified: list[SessionState] = []
    current_game_time_seconds = get_game_time_seconds(session_id, db)
    for state in states:
        if exclude_user_id and state.player_user_id == exclude_user_id:
            continue
        original = state.state_json
        updated = clear_persisted_concentration_effects(
            original, concentration_group=concentration_group
        )
        if updated is not original:
            state.state_json = finalize_session_state_data(
                updated,
                game_time_seconds=current_game_time_seconds,
            )
            flag_modified(state, "state_json")
            db.add(state)
            modified.append(state)

    return modified
