"""Persist and restore manual-duration spell effects across combat boundaries.

`active_spell_effects` in SessionState.state_json is the canonical store for
non-combat spell effects.  Only effects with:
  - kind in {"spell_effect", "temp_ac_bonus"}
  - duration_type == "manual"
  - concentration == False
are persisted.  Round-based and turn-based effects expire naturally during combat.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select as sa_select
from sqlalchemy.orm.attributes import flag_modified

from app.models.session_state import SessionState
from app.services.session_state_finalize import finalize_session_state_data

if TYPE_CHECKING:
    from app.models.combat import CombatState
    from sqlmodel import Session as DbSession

_PERSISTABLE_KINDS = {"spell_effect", "temp_ac_bonus"}


def persist_surviving_spell_effects(db: DbSession, state: CombatState) -> None:
    """Transfer manual-duration, non-concentration spell effects to state_json.

    Called during end_combat() AFTER concentration has been cleared but BEFORE
    remaining participant effects are wiped.
    """
    for participant in state.participants:
        if participant.get("kind") != "player":
            continue
        effects = participant.get("active_effects")
        if not isinstance(effects, list):
            continue
        surviving = [
            e for e in effects
            if e.get("kind") in _PERSISTABLE_KINDS
            and e.get("duration_type") == "manual"
            and not (e.get("metadata") or {}).get("concentration")
        ]
        if not surviving:
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
        data = dict(session_state.state_json or {})
        data["active_spell_effects"] = surviving
        session_state.state_json = finalize_session_state_data(data)
        flag_modified(session_state, "state_json")
        db.add(session_state)


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
    session_state.state_json = finalize_session_state_data(data)
    flag_modified(session_state, "state_json")
    db.add(session_state)
