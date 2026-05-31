from __future__ import annotations

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService


def _state() -> CombatState:
    return CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=[],
    )


def test_create_pending_spell_cast_defaults():
    state = _state()
    created = CombatService._create_pending_spell_cast(
        state,
        spell_key="prayer_of_healing",
        spell_name="Oração de Cura",
        caster_participant_id="p1",
        caster_ref_id="player-1",
        target_ref_ids=["player-1", "player-2"],
        slot_level=2,
        required_rounds=100,
        completed_rounds=1,
        requires_action_each_turn=True,
        requires_concentration_during_casting=True,
        maintained_this_turn=True,
        metadata={"source": "test"},
    )

    assert created["spell_key"] == "prayer_of_healing"
    assert created["required_rounds"] == 100
    assert created["completed_rounds"] == 1
    assert created["remaining_rounds"] == 99
    assert created["maintained_this_turn"] is True
    assert created["status"] == "casting"
    assert isinstance(created["id"], str) and created["id"]
    assert len(state.pending_spell_casts) == 1


def test_find_cancel_and_complete_pending_spell_cast():
    state = _state()
    first = CombatService._create_pending_spell_cast(
        state,
        spell_key="prayer_of_healing",
        spell_name="Oração de Cura",
        caster_participant_id="p1",
        caster_ref_id="player-1",
        target_ref_ids=["player-1"],
        slot_level=2,
        required_rounds=100,
    )
    second = CombatService._create_pending_spell_cast(
        state,
        spell_key="prayer_of_healing",
        spell_name="Oração de Cura",
        caster_participant_id="p1",
        caster_ref_id="player-1",
        target_ref_ids=["player-2"],
        slot_level=2,
        required_rounds=100,
    )

    found = CombatService._find_pending_spell_cast(state, pending_cast_id=first["id"])
    assert found is first

    cancelled = CombatService._cancel_pending_spell_cast(
        state,
        pending_cast_id=first["id"],
        reason="missed_maintain_action",
    )
    assert cancelled is first
    assert cancelled["status"] == "cancelled"
    assert cancelled["cancel_reason"] == "missed_maintain_action"
    assert CombatService._find_pending_spell_cast(state, pending_cast_id=first["id"]) is None
    assert len(state.pending_spell_casts) == 1

    completed = CombatService._complete_pending_spell_cast(
        state,
        pending_cast_id=second["id"],
    )
    assert completed is second
    assert completed["status"] == "completed"
    assert completed["remaining_rounds"] == 0
    assert state.pending_spell_casts == []
