"""Tests for Mage Armor (issue #275) automation.

Covers:
- Timed combat duration schema (SpellDeclarativeDuration with type='timed')
- termination_conditions field on SpellDeclarativeEffect
- OOC cast validation: armored target rejected before slot consumption
- OOC cast: persisted effect shape with timed duration
- Armor-don lifecycle termination from state_json via finalize
- Combat combat participant armor-don removal
- AC applicability: requires_unarmored makes formula inapplicable without removing effect
- Removing armor does NOT restore a terminated effect
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.base_spell_effects import (
    SpellDeclarativeEffect,
    SpellDeclarativeDuration,
    TerminationCondition,
)
from app.services.declarative_effect_lifecycle import (
    _effect_has_target_dons_armor_termination,
    _has_equipped_armor,
    find_armor_don_terminated_effect_ids,
    remove_armor_don_effects_from_combat_participant,
    terminate_armor_don_effects_from_state,
)
from app.services.out_of_combat_cast import (
    _check_requires_unarmored_eligibility,
    _target_has_armor,
    build_persisted_effects,
    check_out_of_combat_cast_eligibility,
)
from app.services.session_state_finalize import (
    calculate_player_armor_class_from_state,
    finalize_session_state_data,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mage_armor_effect(
    *,
    requires_unarmored: bool = True,
    has_termination: bool = True,
    duration_type: str = "timed",
    seconds: int = 28800,
) -> dict:
    termination = [{"type": "target_dons_armor"}] if has_termination else None
    return {
        "type": "armor_class_formula",
        "target": "selected_target",
        "duration": {"type": duration_type, "seconds": seconds} if duration_type == "timed" else {"type": duration_type},
        "out_of_combat_duration": {"type": "timed", "seconds": seconds},
        "params": {
            "base_value": 13,
            "ability": "dexterity",
            "requires_unarmored": requires_unarmored,
        },
        **({"termination_conditions": termination} if termination is not None else {}),
    }


def _make_campaign_spell(
    *,
    canonical_key: str = "mage_armor",
    level: int = 1,
    effects_json: list | None = None,
    out_of_combat_castable: bool = True,
    out_of_combat_target: str = "self_or_ally",
    concentration: bool = False,
):
    spell = MagicMock()
    spell.canonical_key = canonical_key
    spell.level = level
    spell.concentration = concentration
    spell.out_of_combat_castable = out_of_combat_castable
    spell.out_of_combat_target = out_of_combat_target
    spell.effects_json = effects_json if effects_json is not None else [_mage_armor_effect()]
    spell.variants_json = []
    spell.name_pt = "Armadura Arcana"
    spell.name_en = "Mage Armor"
    return spell


def _make_active_spell_effect(
    *,
    base_value: int = 13,
    ability: str = "dexterity",
    requires_unarmored: bool = True,
    has_termination: bool = True,
    duration_type: str = "timed",
    expires_at: int | None = 28800,
    effect_id: str | None = None,
) -> dict:
    termination = [{"type": "target_dons_armor"}] if has_termination else []
    return {
        "id": effect_id or str(uuid4()),
        "kind": "spell_effect",
        "duration_type": duration_type,
        "created_at_game_time_seconds": 0,
        "expires_at_game_time_seconds": expires_at,
        "metadata": {
            "declarative_effect": {
                "type": "armor_class_formula",
                "target": "selected_target",
                "params": {
                    "base_value": base_value,
                    "ability": ability,
                    "requires_unarmored": requires_unarmored,
                },
                "termination_conditions": termination,
            },
            "source_spell_key": "mage_armor",
            "concentration": False,
        },
    }


def _player_state(
    *,
    dexterity: int = 14,
    equipped_armor: dict | None = None,
    active_spell_effects: list | None = None,
) -> dict:
    state = {
        "abilities": {
            "strength": 10, "dexterity": dexterity, "constitution": 10,
            "intelligence": 10, "wisdom": 10, "charisma": 10,
        },
        "currentHP": 20,
        "maxHP": 20,
    }
    if equipped_armor is not None:
        state["equippedArmor"] = equipped_armor
    if active_spell_effects is not None:
        state["active_spell_effects"] = active_spell_effects
    return state


def _leather_armor() -> dict:
    return {"armorType": "light", "baseAC": 11, "allowsDex": True}


def _scale_mail() -> dict:
    return {"armorType": "medium", "baseAC": 14, "dexCap": 2, "allowsDex": True}


# ---------------------------------------------------------------------------
# Schema: SpellDeclarativeDuration with type='timed'
# ---------------------------------------------------------------------------

class TestTimedCombatDurationSchema(unittest.TestCase):

    def test_timed_duration_valid(self):
        dur = SpellDeclarativeDuration.model_validate({"type": "timed", "seconds": 28800})
        self.assertEqual(dur.type, "timed")
        self.assertEqual(dur.seconds, 28800)
        self.assertIsNone(dur.rounds)
        self.assertIsNone(dur.anchor)

    def test_timed_duration_requires_seconds(self):
        with self.assertRaises(ValidationError):
            SpellDeclarativeDuration.model_validate({"type": "timed"})

    def test_timed_duration_rejects_negative_seconds(self):
        with self.assertRaises(ValidationError):
            SpellDeclarativeDuration.model_validate({"type": "timed", "seconds": 0})

    def test_timed_duration_strips_anchor(self):
        dur = SpellDeclarativeDuration.model_validate(
            {"type": "timed", "seconds": 100, "anchor": "target"}
        )
        self.assertIsNone(dur.anchor)

    def test_rounds_duration_unaffected(self):
        dur = SpellDeclarativeDuration.model_validate({"type": "rounds", "rounds": 10})
        self.assertEqual(dur.type, "rounds")
        self.assertEqual(dur.rounds, 10)
        self.assertIsNone(dur.seconds)

    def test_manual_duration_unaffected(self):
        dur = SpellDeclarativeDuration.model_validate({"type": "manual"})
        self.assertEqual(dur.type, "manual")
        self.assertIsNone(dur.seconds)
        self.assertIsNone(dur.rounds)


# ---------------------------------------------------------------------------
# Schema: termination_conditions on SpellDeclarativeEffect
# ---------------------------------------------------------------------------

class TestTerminationConditionSchema(unittest.TestCase):

    def test_effect_with_target_dons_armor_termination(self):
        effect = SpellDeclarativeEffect.model_validate({
            "type": "armor_class_formula",
            "target": "selected_target",
            "duration": {"type": "timed", "seconds": 28800},
            "out_of_combat_duration": {"type": "timed", "seconds": 28800},
            "params": {"base_value": 13, "ability": "dexterity", "requires_unarmored": True},
            "termination_conditions": [{"type": "target_dons_armor"}],
        })
        self.assertIsNotNone(effect.termination_conditions)
        self.assertEqual(len(effect.termination_conditions), 1)
        self.assertEqual(effect.termination_conditions[0].type, "target_dons_armor")

    def test_effect_without_termination_conditions(self):
        effect = SpellDeclarativeEffect.model_validate({
            "type": "armor_class_formula",
            "target": "selected_target",
            "params": {"base_value": 13, "ability": "dexterity"},
        })
        self.assertIsNone(effect.termination_conditions)

    def test_unknown_termination_type_rejected(self):
        with self.assertRaises(ValidationError):
            SpellDeclarativeEffect.model_validate({
                "type": "armor_class_formula",
                "target": "selected_target",
                "params": {"base_value": 13, "ability": "dexterity"},
                "termination_conditions": [{"type": "unknown_condition"}],
            })

    def test_termination_condition_model(self):
        cond = TerminationCondition.model_validate({"type": "target_dons_armor"})
        self.assertEqual(cond.type, "target_dons_armor")


# ---------------------------------------------------------------------------
# OOC cast validation: requires_unarmored
# ---------------------------------------------------------------------------

class TestOOCRequiresUnarmoredEligibility(unittest.TestCase):

    def test_check_rejects_armored_target(self):
        effects = [_mage_armor_effect()]
        target_state = _player_state(equipped_armor=_leather_armor())
        result = _check_requires_unarmored_eligibility(effects, target_state)
        self.assertIsNotNone(result)

    def test_check_allows_unarmored_target(self):
        effects = [_mage_armor_effect()]
        target_state = _player_state(equipped_armor=None)
        result = _check_requires_unarmored_eligibility(effects, target_state)
        self.assertIsNone(result)

    def test_check_ignores_effect_without_requires_unarmored(self):
        effects = [{"type": "armor_class_formula", "target": "selected_target",
                    "params": {"base_value": 13, "ability": "dexterity"}}]
        target_state = _player_state(equipped_armor=_scale_mail())
        result = _check_requires_unarmored_eligibility(effects, target_state)
        self.assertIsNone(result)

    def test_target_has_armor_helper_light_armor(self):
        self.assertTrue(_target_has_armor({"equippedArmor": {"armorType": "light"}}))

    def test_target_has_armor_helper_medium_armor(self):
        self.assertTrue(_target_has_armor({"equippedArmor": {"armorType": "medium"}}))

    def test_target_has_armor_helper_heavy_armor(self):
        self.assertTrue(_target_has_armor({"equippedArmor": {"armorType": "heavy"}}))

    def test_target_has_armor_helper_no_armor(self):
        self.assertFalse(_target_has_armor({}))

    def test_target_has_armor_helper_empty_armor(self):
        self.assertFalse(_target_has_armor({"equippedArmor": {}}))

    def test_check_eligibility_with_armored_target_state_json(self):
        spell = _make_campaign_spell()
        state_json = _player_state(
            dexterity=14,
            equipped_armor=None,
        )
        state_json["spellcasting"] = {
            "slots": {"1": {"used": 0, "max": 2}},
            "spells": [],
        }
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json=state_json,
            slot_level=1,
            variant_key=None,
            target_state_json=_player_state(equipped_armor=_leather_armor()),
        )
        self.assertFalse(ok)
        self.assertIn("armor", reason.lower())

    def test_check_eligibility_unarmored_target_passes(self):
        spell = _make_campaign_spell()
        state_json = _player_state(dexterity=14)
        state_json["spellcasting"] = {
            "slots": {"1": {"used": 0, "max": 2}},
            "spells": [],
        }
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json=state_json,
            slot_level=1,
            variant_key=None,
            target_state_json=_player_state(equipped_armor=None),
        )
        self.assertTrue(ok)
        self.assertIsNone(reason)


# ---------------------------------------------------------------------------
# OOC cast: persisted effect shape with timed duration
# ---------------------------------------------------------------------------

class TestOOCMageArmorEffectShape(unittest.TestCase):

    def test_build_persisted_effects_timed_duration(self):
        spell = _make_campaign_spell()
        game_time = 1000
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="caster-1",
            target_user_id="target-1",
            variant_key=None,
            game_time_seconds=game_time,
        )
        self.assertEqual(len(effects), 1)
        e = effects[0]
        self.assertEqual(e["duration_type"], "timed")
        self.assertEqual(e["created_at_game_time_seconds"], game_time)
        self.assertEqual(e["expires_at_game_time_seconds"], game_time + 28800)
        self.assertEqual(e["kind"], "spell_effect")

    def test_build_persisted_effects_metadata_contains_declarative_effect(self):
        spell = _make_campaign_spell()
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="caster-1",
            target_user_id="target-1",
            variant_key=None,
            game_time_seconds=0,
        )
        self.assertEqual(len(effects), 1)
        metadata = effects[0]["metadata"]
        declarative = metadata["declarative_effect"]
        self.assertEqual(declarative["type"], "armor_class_formula")
        params = declarative["params"]
        self.assertEqual(params["base_value"], 13)
        self.assertEqual(params["ability"], "dexterity")
        self.assertTrue(params["requires_unarmored"])

    def test_build_persisted_effects_includes_termination_conditions(self):
        spell = _make_campaign_spell()
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="caster-1",
            target_user_id="target-1",
            variant_key=None,
            game_time_seconds=0,
        )
        declarative = effects[0]["metadata"]["declarative_effect"]
        self.assertIn("termination_conditions", declarative)
        self.assertEqual(declarative["termination_conditions"], [{"type": "target_dons_armor"}])


# ---------------------------------------------------------------------------
# AC calculation: requires_unarmored applicability (no removal)
# ---------------------------------------------------------------------------

class TestACApplicabilityVsTermination(unittest.TestCase):

    def test_formula_applies_when_unarmored(self):
        state = _player_state(dexterity=14, active_spell_effects=[_make_active_spell_effect()])
        ac = calculate_player_armor_class_from_state(state)
        # 13 + DEX(14→+2) = 15
        self.assertEqual(ac, 15)

    def test_formula_inapplicable_when_armored_not_removed(self):
        # Effect stays in state but doesn't contribute to AC
        effect = _make_active_spell_effect()
        state = _player_state(
            dexterity=14,
            equipped_armor=_leather_armor(),
            active_spell_effects=[effect],
        )
        ac = calculate_player_armor_class_from_state(state)
        # leather armor: 11 + 2 DEX = 13 (formula ignored, not 15)
        self.assertEqual(ac, 13)
        # Effect still in state (applicability ≠ termination)
        self.assertEqual(len(state["active_spell_effects"]), 1)

    def test_formula_beats_default_unarmored(self):
        state = _player_state(dexterity=14, active_spell_effects=[_make_active_spell_effect()])
        ac = calculate_player_armor_class_from_state(state)
        self.assertEqual(ac, 15)

    def test_additive_bonuses_stack_on_formula(self):
        effects = [
            _make_active_spell_effect(),
            {
                "id": str(uuid4()),
                "kind": "temp_ac_bonus",
                "numeric_value": 2,
                "duration_type": "manual",
            },
        ]
        state = _player_state(dexterity=14, active_spell_effects=effects)
        ac = calculate_player_armor_class_from_state(state)
        # 13 + 2 (DEX) + 2 (temp bonus) = 17
        self.assertEqual(ac, 17)


# ---------------------------------------------------------------------------
# Armor-don termination: declarative_effect_lifecycle helpers
# ---------------------------------------------------------------------------

class TestArmorDonLifecycleHelpers(unittest.TestCase):

    def test_effect_has_target_dons_armor_termination_true(self):
        effect = _make_active_spell_effect(has_termination=True)
        self.assertTrue(_effect_has_target_dons_armor_termination(effect))

    def test_effect_has_target_dons_armor_termination_false(self):
        effect = _make_active_spell_effect(has_termination=False)
        self.assertFalse(_effect_has_target_dons_armor_termination(effect))

    def test_has_equipped_armor_light(self):
        state = _player_state(equipped_armor=_leather_armor())
        self.assertTrue(_has_equipped_armor(state))

    def test_has_equipped_armor_none(self):
        state = _player_state()
        self.assertFalse(_has_equipped_armor(state))

    def test_find_armor_don_terminated_effect_ids(self):
        e1 = _make_active_spell_effect(effect_id="e1", has_termination=True)
        e2 = _make_active_spell_effect(effect_id="e2", has_termination=False)
        ids = find_armor_don_terminated_effect_ids([e1, e2])
        self.assertEqual(ids, ["e1"])

    def test_terminate_armor_don_effects_removes_when_armored(self):
        effect = _make_active_spell_effect()
        state = _player_state(
            equipped_armor=_leather_armor(),
            active_spell_effects=[effect],
        )
        result = terminate_armor_don_effects_from_state(state)
        self.assertNotIn("active_spell_effects", result)

    def test_terminate_armor_don_effects_keeps_when_unarmored(self):
        effect = _make_active_spell_effect()
        state = _player_state(active_spell_effects=[effect])
        result = terminate_armor_don_effects_from_state(state)
        self.assertIn("active_spell_effects", result)
        self.assertEqual(len(result["active_spell_effects"]), 1)

    def test_terminate_armor_don_preserves_non_terminating_effects(self):
        e1 = _make_active_spell_effect(effect_id="e1", has_termination=True)
        e2 = _make_active_spell_effect(effect_id="e2", has_termination=False)
        state = _player_state(
            equipped_armor=_leather_armor(),
            active_spell_effects=[e1, e2],
        )
        result = terminate_armor_don_effects_from_state(state)
        remaining = result.get("active_spell_effects", [])
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["id"], "e2")

    def test_removing_armor_does_not_restore_terminated_effect(self):
        # Effect was removed when armor was equipped; then armor removed.
        # No effect to restore — termination is permanent.
        state = _player_state(active_spell_effects=[])  # effect already gone
        result = terminate_armor_don_effects_from_state(state)
        self.assertEqual(result.get("active_spell_effects", []), [])

    def test_idempotent_when_no_armor(self):
        effect = _make_active_spell_effect()
        state = _player_state(active_spell_effects=[effect])
        result = terminate_armor_don_effects_from_state(state)
        self.assertIs(result, state)  # unchanged object

    def test_idempotent_when_no_effects(self):
        state = _player_state(equipped_armor=_leather_armor())
        result = terminate_armor_don_effects_from_state(state)
        self.assertIs(result, state)


# ---------------------------------------------------------------------------
# finalize_session_state_data: armor-don termination integrated
# ---------------------------------------------------------------------------

class TestFinalizeArmorDonTermination(unittest.TestCase):

    def test_finalize_removes_armor_don_effects_on_armor_equip(self):
        effect = _make_active_spell_effect()
        state = _player_state(
            dexterity=14,
            equipped_armor=_leather_armor(),
            active_spell_effects=[effect],
        )
        result = finalize_session_state_data(state)
        self.assertNotIn("active_spell_effects", result)

    def test_finalize_keeps_effects_when_unarmored(self):
        effect = _make_active_spell_effect()
        state = _player_state(dexterity=14, active_spell_effects=[effect])
        result = finalize_session_state_data(state)
        self.assertIn("active_spell_effects", result)

    def test_finalize_recalculates_ac_after_armor_don_termination(self):
        # With Mage Armor and leather equipped, Mage Armor is terminated,
        # AC should be from leather (11 + 2 DEX = 13).
        effect = _make_active_spell_effect()
        state = _player_state(
            dexterity=14,
            equipped_armor=_leather_armor(),
            active_spell_effects=[effect],
        )
        result = finalize_session_state_data(state)
        # Mage Armor gone; leather: 11 + 2 = 13
        self.assertEqual(result["armorClass"], 13)


# ---------------------------------------------------------------------------
# Combat participant armor-don removal
# ---------------------------------------------------------------------------

class TestCombatArmorDonRemoval(unittest.TestCase):

    def _make_combat_state(self, effects: list[dict], player_user_id: str = "user-1"):
        state = MagicMock()
        state.participants = [
            {
                "id": "p-1",
                "kind": "player",
                "ref_id": player_user_id,
                "display_name": "Alice",
                "active_effects": list(effects),
            }
        ]
        return state

    def test_removes_armor_don_effects_from_participant(self):
        e1 = _make_active_spell_effect(effect_id="e1", has_termination=True)
        combat_state = self._make_combat_state([e1])
        removed = remove_armor_don_effects_from_combat_participant(combat_state, "user-1")
        self.assertTrue(removed)
        self.assertEqual(combat_state.participants[0]["active_effects"], [])

    def test_no_op_when_no_terminating_effects(self):
        e1 = _make_active_spell_effect(effect_id="e1", has_termination=False)
        combat_state = self._make_combat_state([e1])
        removed = remove_armor_don_effects_from_combat_participant(combat_state, "user-1")
        self.assertFalse(removed)
        self.assertEqual(len(combat_state.participants[0]["active_effects"]), 1)

    def test_no_op_when_participant_not_found(self):
        e1 = _make_active_spell_effect(has_termination=True)
        combat_state = self._make_combat_state([e1], player_user_id="user-1")
        removed = remove_armor_don_effects_from_combat_participant(combat_state, "user-9")
        self.assertFalse(removed)

    def test_preserves_non_terminating_effects(self):
        e1 = _make_active_spell_effect(effect_id="e1", has_termination=True)
        e2 = _make_active_spell_effect(effect_id="e2", has_termination=False)
        combat_state = self._make_combat_state([e1, e2])
        remove_armor_don_effects_from_combat_participant(combat_state, "user-1")
        remaining = combat_state.participants[0]["active_effects"]
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["id"], "e2")

    def test_handles_none_combat_state(self):
        removed = remove_armor_don_effects_from_combat_participant(None, "user-1")
        self.assertFalse(removed)


# ---------------------------------------------------------------------------
# Full mage_armor seed entry schema validation
# ---------------------------------------------------------------------------

class TestMageArmorSeedEntry(unittest.TestCase):

    def _mage_armor_seed_effect(self) -> dict:
        return {
            "type": "armor_class_formula",
            "target": "selected_target",
            "duration": {"type": "timed", "seconds": 28800},
            "out_of_combat_duration": {"type": "timed", "seconds": 28800},
            "params": {
                "base_value": 13,
                "ability": "dexterity",
                "requires_unarmored": True,
            },
            "termination_conditions": [{"type": "target_dons_armor"}],
        }

    def test_seed_effect_validates_as_spell_declarative_effect(self):
        effect = SpellDeclarativeEffect.model_validate(self._mage_armor_seed_effect())
        self.assertEqual(effect.type, "armor_class_formula")
        self.assertIsNotNone(effect.termination_conditions)
        self.assertEqual(effect.duration.type, "timed")
        self.assertEqual(effect.duration.seconds, 28800)

    def test_seed_effect_round_trips(self):
        raw = self._mage_armor_seed_effect()
        effect = SpellDeclarativeEffect.model_validate(raw)
        dumped = effect.model_dump(mode="json", exclude_none=True)
        self.assertEqual(dumped["termination_conditions"], [{"type": "target_dons_armor"}])
        self.assertEqual(dumped["duration"]["type"], "timed")
        self.assertEqual(dumped["duration"]["seconds"], 28800)


if __name__ == "__main__":
    unittest.main()
