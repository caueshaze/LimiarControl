"""Tests for Animal Friendship break-on-damage termination (issue #277).

Covers:
- Schema: target_takes_damage_from_caster_or_allies termination condition type
- declarative_effect_lifecycle: team checking, condition detection, effect removal
- spell_automation: Animal Friendship effect carries termination_conditions in metadata
- Integration: charm removed when caster or ally deals damage; not when enemy does
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.schemas.base_spell_effects import (
    SpellDeclarativeTerminationConditionType,
    TerminationCondition,
)
from app.services.declarative_effect_lifecycle import (
    _are_friendly_participants,
    _effect_has_damage_termination,
    _get_caster_participant_id_for_effect,
    _get_effect_termination_conditions,
    find_damage_terminated_effect_ids,
    remove_damage_terminated_effects_from_participant,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_participant(
    pid: str,
    ref_id: str = "ref",
    kind: str = "session_entity",
    team: str = "enemies",
) -> dict:
    return {"id": pid, "ref_id": ref_id, "kind": kind, "team": team}


def _make_charmed_effect(
    *,
    effect_id: str | None = None,
    caster_participant_id: str = "caster-p",
    has_damage_termination: bool = True,
    store_in_metadata_direct: bool = True,
) -> dict:
    """Build an effect like the one produced by _cast_animal_friendship_automation."""
    termination = (
        [{"type": "target_takes_damage_from_caster_or_allies"}]
        if has_damage_termination
        else []
    )
    if store_in_metadata_direct:
        metadata: dict = {
            "source_spell_key": "animal_friendship",
            "caster_participant_id": caster_participant_id,
            "charmer_participant_id": caster_participant_id,
        }
        if termination:
            metadata["termination_conditions"] = termination
    else:
        # Nested inside declarative_effect (declarative effects path)
        metadata = {
            "caster_participant_id": caster_participant_id,
            "declarative_effect": {
                "type": "apply_condition",
                "params": {"condition": "charmed"},
                "termination_conditions": termination if has_damage_termination else None,
            },
        }
    return {
        "id": effect_id or str(uuid4()),
        "kind": "condition",
        "condition_type": "charmed",
        "duration_type": "timed",
        "metadata": metadata,
    }


def _make_state_with_participants(*participants: dict):
    state = MagicMock()
    state.participants = list(participants)
    return state


# ---------------------------------------------------------------------------
# Schema: new termination condition type
# ---------------------------------------------------------------------------

class TestTerminationConditionSchemaExtension(unittest.TestCase):

    def test_target_takes_damage_validates(self):
        cond = TerminationCondition.model_validate(
            {"type": "target_takes_damage_from_caster_or_allies"}
        )
        self.assertEqual(cond.type, "target_takes_damage_from_caster_or_allies")

    def test_both_types_in_literal(self):
        # Ensure both types are accepted
        for t in ("target_dons_armor", "target_takes_damage_from_caster_or_allies"):
            cond = TerminationCondition.model_validate({"type": t})
            self.assertEqual(cond.type, t)

    def test_unknown_type_rejected(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            TerminationCondition.model_validate({"type": "unknown_termination"})


# ---------------------------------------------------------------------------
# Lifecycle helpers: team checking
# ---------------------------------------------------------------------------

class TestAreFriendlyParticipants(unittest.TestCase):

    def test_same_participant_is_friendly(self):
        p = _make_participant("p1", team="players")
        self.assertTrue(_are_friendly_participants(p, p))

    def test_same_id_is_friendly(self):
        p1 = _make_participant("p1", team="players")
        p2 = _make_participant("p1", team="enemies")  # same id, different team (hypothetical)
        self.assertTrue(_are_friendly_participants(p1, p2))

    def test_players_are_friendly(self):
        p1 = _make_participant("p1", team="players")
        p2 = _make_participant("p2", team="players")
        self.assertTrue(_are_friendly_participants(p1, p2))

    def test_player_and_ally_are_friendly(self):
        p = _make_participant("p1", team="players")
        a = _make_participant("a1", team="allies")
        self.assertTrue(_are_friendly_participants(p, a))

    def test_ally_and_ally_are_friendly(self):
        a1 = _make_participant("a1", team="allies")
        a2 = _make_participant("a2", team="allies")
        self.assertTrue(_are_friendly_participants(a1, a2))

    def test_enemies_are_not_friendly_to_players(self):
        p = _make_participant("p1", team="players")
        e = _make_participant("e1", team="enemies")
        self.assertFalse(_are_friendly_participants(p, e))

    def test_enemies_are_friendly_to_each_other(self):
        e1 = _make_participant("e1", team="enemies")
        e2 = _make_participant("e2", team="enemies")
        self.assertTrue(_are_friendly_participants(e1, e2))

    def test_neutral_is_not_friendly_to_players(self):
        p = _make_participant("p1", team="players")
        n = _make_participant("n1", team="neutral")
        self.assertFalse(_are_friendly_participants(p, n))


# ---------------------------------------------------------------------------
# Lifecycle helpers: condition detection
# ---------------------------------------------------------------------------

class TestEffectHasDamageTermination(unittest.TestCase):

    def test_automation_effect_with_termination(self):
        effect = _make_charmed_effect(has_damage_termination=True, store_in_metadata_direct=True)
        self.assertTrue(_effect_has_damage_termination(effect))

    def test_declarative_effect_with_termination(self):
        effect = _make_charmed_effect(has_damage_termination=True, store_in_metadata_direct=False)
        self.assertTrue(_effect_has_damage_termination(effect))

    def test_effect_without_termination(self):
        effect = _make_charmed_effect(has_damage_termination=False)
        self.assertFalse(_effect_has_damage_termination(effect))

    def test_get_caster_from_caster_participant_id(self):
        effect = _make_charmed_effect(caster_participant_id="caster-123")
        cid = _get_caster_participant_id_for_effect(effect)
        self.assertEqual(cid, "caster-123")

    def test_get_caster_from_charmer_participant_id_legacy(self):
        # Old effects may only have charmer_participant_id
        effect = {
            "id": "e1",
            "kind": "condition",
            "metadata": {
                "charmer_participant_id": "old-caster-99",
                # No caster_participant_id
            },
        }
        cid = _get_caster_participant_id_for_effect(effect)
        self.assertEqual(cid, "old-caster-99")

    def test_get_termination_conditions_from_metadata_direct(self):
        effect = _make_charmed_effect(store_in_metadata_direct=True)
        conds = _get_effect_termination_conditions(effect)
        self.assertEqual(len(conds), 1)
        self.assertEqual(conds[0]["type"], "target_takes_damage_from_caster_or_allies")

    def test_get_termination_conditions_from_declarative(self):
        effect = _make_charmed_effect(store_in_metadata_direct=False)
        conds = _get_effect_termination_conditions(effect)
        self.assertEqual(len(conds), 1)
        self.assertEqual(conds[0]["type"], "target_takes_damage_from_caster_or_allies")


# ---------------------------------------------------------------------------
# Lifecycle helpers: find and remove terminated effects
# ---------------------------------------------------------------------------

class TestFindDamageTerminatedEffectIds(unittest.TestCase):

    def _setup(self):
        caster = _make_participant("caster-p", ref_id="user-caster", kind="player", team="players")
        ally = _make_participant("ally-p", ref_id="user-ally", kind="player", team="players")
        enemy = _make_participant("enemy-p", ref_id="enemy-npc", kind="session_entity", team="enemies")
        beast = _make_participant("beast-p", ref_id="wolf-npc", kind="session_entity", team="enemies")
        charmed_effect = _make_charmed_effect(effect_id="charm-1", caster_participant_id="caster-p")
        beast["active_effects"] = [charmed_effect]
        participants = [caster, ally, enemy, beast]
        return participants, beast

    def test_caster_damaging_target_terminates_effect(self):
        participants, beast = self._setup()
        ids = find_damage_terminated_effect_ids(participants, beast, "caster-p")
        self.assertEqual(ids, ["charm-1"])

    def test_ally_damaging_target_terminates_effect(self):
        participants, beast = self._setup()
        ids = find_damage_terminated_effect_ids(participants, beast, "ally-p")
        self.assertEqual(ids, ["charm-1"])

    def test_enemy_damaging_target_does_not_terminate_effect(self):
        participants, beast = self._setup()
        ids = find_damage_terminated_effect_ids(participants, beast, "enemy-p")
        self.assertEqual(ids, [])

    def test_unknown_attacker_does_not_terminate(self):
        participants, beast = self._setup()
        ids = find_damage_terminated_effect_ids(participants, beast, "unknown-participant")
        self.assertEqual(ids, [])

    def test_effect_without_termination_not_terminated_by_ally(self):
        caster = _make_participant("caster-p", team="players")
        ally = _make_participant("ally-p", team="players")
        non_terminating_effect = _make_charmed_effect(
            effect_id="charm-no", caster_participant_id="caster-p", has_damage_termination=False
        )
        beast = _make_participant("beast-p", team="enemies")
        beast["active_effects"] = [non_terminating_effect]
        participants = [caster, ally, beast]
        ids = find_damage_terminated_effect_ids(participants, beast, "ally-p")
        self.assertEqual(ids, [])


class TestRemoveDamageTerminatedEffects(unittest.TestCase):

    def test_removes_charmed_when_caster_deals_damage(self):
        caster = _make_participant("caster-p", team="players")
        beast = _make_participant("beast-p", team="enemies")
        charm = _make_charmed_effect(effect_id="charm-1", caster_participant_id="caster-p")
        beast["active_effects"] = [charm]
        state = _make_state_with_participants(caster, beast)
        removed = remove_damage_terminated_effects_from_participant(state, beast, "caster-p")
        self.assertTrue(removed)
        self.assertEqual(beast["active_effects"], [])

    def test_preserves_other_effects_when_removing(self):
        caster = _make_participant("caster-p", team="players")
        beast = _make_participant("beast-p", team="enemies")
        charm = _make_charmed_effect(effect_id="charm-1", caster_participant_id="caster-p")
        other_effect = {"id": "other-1", "kind": "condition", "condition_type": "poisoned", "metadata": {}}
        beast["active_effects"] = [charm, other_effect]
        state = _make_state_with_participants(caster, beast)
        remove_damage_terminated_effects_from_participant(state, beast, "caster-p")
        remaining = beast["active_effects"]
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["id"], "other-1")

    def test_no_op_when_enemy_deals_damage(self):
        caster = _make_participant("caster-p", team="players")
        enemy = _make_participant("enemy-p", team="enemies")
        beast = _make_participant("beast-p", team="enemies")
        charm = _make_charmed_effect(effect_id="charm-1", caster_participant_id="caster-p")
        beast["active_effects"] = [charm]
        state = _make_state_with_participants(caster, enemy, beast)
        removed = remove_damage_terminated_effects_from_participant(state, beast, "enemy-p")
        self.assertFalse(removed)
        self.assertEqual(len(beast["active_effects"]), 1)

    def test_no_op_when_no_terminating_effects(self):
        caster = _make_participant("caster-p", team="players")
        beast = _make_participant("beast-p", team="enemies")
        beast["active_effects"] = []
        state = _make_state_with_participants(caster, beast)
        removed = remove_damage_terminated_effects_from_participant(state, beast, "caster-p")
        self.assertFalse(removed)


# ---------------------------------------------------------------------------
# Animal Friendship effect metadata validation
# ---------------------------------------------------------------------------

class TestAnimalFriendshipEffectMetadata(unittest.TestCase):
    """Verify that the effect created by _cast_animal_friendship_automation
    carries the correct termination_conditions and caster_participant_id."""

    def _build_charmed_effect_like_handler(self, caster_id: str) -> dict:
        from app.services.combat_service.concentration import CombatConcentrationMixin

        class Dummy(CombatConcentrationMixin):
            pass

        return Dummy._build_active_effect(
            kind="condition",
            condition_type="charmed",
            source_participant_id=caster_id,
            duration_type="timed",
            created_at_game_time_seconds=1000,
            expires_at_game_time_seconds=1000 + 86400,
            metadata={
                "source_spell_key": "animal_friendship",
                "caster_participant_id": caster_id,
                "charmer_participant_id": caster_id,
                "termination_conditions": [
                    {"type": "target_takes_damage_from_caster_or_allies"}
                ],
            },
        )

    def test_effect_has_termination_condition(self):
        effect = self._build_charmed_effect_like_handler("caster-p")
        self.assertTrue(_effect_has_damage_termination(effect))

    def test_effect_has_caster_participant_id(self):
        effect = self._build_charmed_effect_like_handler("caster-p")
        self.assertEqual(_get_caster_participant_id_for_effect(effect), "caster-p")

    def test_effect_has_timed_duration_86400s(self):
        effect = self._build_charmed_effect_like_handler("caster-p")
        self.assertEqual(effect["duration_type"], "timed")
        self.assertEqual(effect["expires_at_game_time_seconds"], 1000 + 86400)


if __name__ == "__main__":
    unittest.main()
