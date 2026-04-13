"""Paridade com packages/tactical-engine/tests/unit/combat-state.test.ts"""
from shared_contracts import CombatState
from tactical_engine import advance_combat, can_token_act


def _make_combat(**kwargs) -> CombatState:
    base = dict(
        id="combat",
        battle_map_id="map",
        status="active",
        round_number=1,
        turn_index=0,
        active_combatant_id="a",
        initiative_order=["a", "b"],
        advanced_by="LimiarControl",
        version=1,
    )
    base.update(kwargs)
    return CombatState(**base)


def test_advances_to_next_active_combatant():
    next_state = advance_combat(_make_combat())
    assert next_state.active_combatant_id == "b"
    assert next_state.version == 2


def test_guards_acting_tokens_by_active_turn():
    assert can_token_act(_make_combat(), "b") is False


def test_can_act_when_combat_inactive():
    state = _make_combat(status="inactive")
    assert can_token_act(state, "b") is True


def test_wraps_round_on_last_combatant():
    state = _make_combat(turn_index=1, active_combatant_id="b")
    next_state = advance_combat(state)
    assert next_state.turn_index == 0
    assert next_state.round_number == 2
    assert next_state.active_combatant_id == "a"
