from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.combat_spells import CombatResolveSpellContextRequest
from app.schemas.roll import RollResult
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_predicates import get_roll_bonus_dice_sources


def _bless_effect(effect_id: str = "eff-bless") -> dict:
    return {
        "id": effect_id,
        "kind": "spell_effect",
        "metadata": {
            "declarative_effect_group_id": "grp-bless",
            "source_spell_key": "bless",
            "source_spell_name": "Bênção",
            "declarative_effect": {
                "type": "roll_dice_modifier",
                "params": {"mode": "bonus", "roll_types": ["attack", "save"], "dice": "1d4"},
            },
        },
    }


class BlessSeedTests(unittest.TestCase):
    def test_seed_has_bless_with_upcast_and_effects(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        self.assertIn("bless", spells)
        s = spells["bless"]
        self.assertEqual(s["level"], 1)
        self.assertEqual(s["school"], "enchantment")
        self.assertEqual(s["maxTargets"], 3)
        self.assertEqual(s["upcast"]["mode"], "additional_targets")
        self.assertEqual(s["upcast"]["perLevel"], 1)
        self.assertTrue(any(e.get("type") == "roll_dice_modifier" for e in s.get("effects", [])))

    def test_seed_has_bane_with_save_and_upcast(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        self.assertIn("bane", spells)
        s = spells["bane"]
        self.assertEqual(s["maxTargets"], 3)
        self.assertEqual(s["upcast"]["mode"], "additional_targets")
        self.assertEqual(s["upcast"]["perLevel"], 1)
        self.assertEqual(s["savingThrow"], "cha")
        self.assertEqual(s["saveEffect"], "negates")


class BlessUpcastContextTests(unittest.TestCase):
    def _resolve_context(self, slot_level: int) -> dict:
        state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "caster",
                    "kind": "player",
                    "display_name": "Caster",
                    "status": "active",
                    "team": "players",
                    "actor_user_id": "u1",
                    "active_effects": [],
                    "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
                }
            ],
            use_map=False,
        )
        attacker_state = SessionState(
            id="ss-1",
            session_id="s1",
            player_user_id="u1",
            state_json={
                "spellcasting": {
                    "spells": [{"canonicalKey": "bless", "level": 1, "prepared": True}],
                    "slots": {str(slot_level): {"used": 0, "max": 3}},
                }
            },
        )
        catalog_spell = type(
            "CatalogSpell",
            (),
            {
                "canonical_key": "bless",
                "name_en": "Bless",
                "name_pt": "Bênção",
                "level": 1,
                "resolution_type": "buff",
                "damage_dice": None,
                "heal_dice": None,
                "damage_type": None,
                "saving_throw": None,
                "save_success_outcome": None,
                "upcast_json": {"mode": "additional_targets", "perLevel": 1},
                "cantrip_scaling_json": None,
                "casting_time_type": "action",
                "target_type": "ranged",
                "selection_type": "creature",
                "origin_type": "caster",
                "target_anchor": "selected_target",
                "attack_type": "none",
                "range_kind": "distance",
                "effect_timing": "persistent",
                "area_shape": None,
                "range_meters": 9,
                "duration": "Concentration, up to 1 minute",
                "concentration": True,
                "max_targets": 3,
                "requires_target_sight": True,
                "requires_target_effect": True,
                "requires_point_sight": False,
                "requires_point_effect": False,
                "effects_json": [{"type": "roll_dice_modifier", "target": "selected_target", "params": {"mode": "bonus", "roll_types": ["attack", "save"], "dice": "1d4"}}],
            },
        )()

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=catalog_spell),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)),
        ):
            return CombatService.resolve_spell_context(
                None,
                "s1",
                CombatResolveSpellContextRequest(
                    actor_participant_id="p1",
                    spell_canonical_key="bless",
                    spell_mode="utility",
                    slot_level=slot_level,
                ),
                "u1",
                False,
            )

    def test_upcast_max_targets(self):
        self.assertEqual(self._resolve_context(1)["max_targets"], 3)
        self.assertEqual(self._resolve_context(2)["max_targets"], 4)
        self.assertEqual(self._resolve_context(3)["max_targets"], 5)


class BlessRollBonusTests(unittest.TestCase):
    @patch("app.services.combat_service.condition_effects_predicates_parts.predicates_spell_metadata._roll_dice_expression", return_value=3)
    def test_get_roll_bonus_sources_for_attack_and_save(self, _mock_roll):
        participant = {"active_effects": [_bless_effect()]}
        attack_sources = get_roll_bonus_dice_sources(participant, roll_type="attack")
        save_sources = get_roll_bonus_dice_sources(participant, roll_type="save")
        self.assertEqual(len(attack_sources), 1)
        self.assertEqual(len(save_sources), 1)
        self.assertEqual(attack_sources[0]["signed_total"], 3)
        self.assertEqual(save_sources[0]["source_label"], "Bênção")

    @patch("app.services.combat_service.condition_effects_predicates_parts.predicates_spell_metadata._roll_dice_expression", return_value=2)
    def test_apply_roll_bonus_updates_attack_result(self, _mock_roll):
        participant = {"active_effects": [_bless_effect()]}
        result = RollResult(
            event_id="e1",
            roll_type="attack",
            actor_kind="player",
            actor_ref_id="p1",
            actor_display_name="Lia",
            rolls=[10, 10],
            selected_roll=10,
            advantage_mode="normal",
            modifier_used=5,
            override_used=False,
            formula="1d20 + 5",
            total=15,
            target_ac=16,
            success=False,
            roll_source="system",
            timestamp="2026-01-01T00:00:00Z",
        )
        CombatService._apply_roll_bonus_dice_to_roll_result(
            participant=participant,
            roll_result=result,
            roll_type="attack",
        )
        self.assertEqual(result.total, 17)
        self.assertTrue(result.success)
        self.assertEqual(result.check_modifier_sources[0]["modifier_type"], "roll_dice_modifier")

    @patch("app.services.combat_service.condition_effects_predicates_parts.predicates_spell_metadata._roll_dice_expression", return_value=4)
    def test_apply_roll_penalty_updates_save_result(self, _mock_roll):
        participant = {"active_effects": [{
            "id": "eff-bane",
            "kind": "spell_effect",
            "metadata": {
                "declarative_effect_group_id": "grp-bane",
                "source_spell_key": "bane",
                "source_spell_name": "Perdição",
                "declarative_effect": {
                    "type": "roll_dice_modifier",
                    "params": {"mode": "penalty", "roll_types": ["attack", "save"], "dice": "1d4"},
                },
            },
        }]}
        result = RollResult(
            event_id="e3",
            roll_type="save",
            actor_kind="player",
            actor_ref_id="p1",
            actor_display_name="Lia",
            rolls=[12, 12],
            selected_roll=12,
            advantage_mode="normal",
            modifier_used=2,
            override_used=False,
            formula="1d20 + 2",
            total=14,
            ability="wisdom",
            dc=13,
            success=True,
            roll_source="system",
            timestamp="2026-01-01T00:00:00Z",
        )
        CombatService._apply_roll_bonus_dice_to_roll_result(participant=participant, roll_result=result, roll_type="save")
        self.assertEqual(result.total, 10)
        self.assertFalse(result.success)

    @patch("app.services.combat_service.condition_effects_predicates_parts.predicates_spell_metadata._roll_dice_expression", return_value=4)
    def test_apply_roll_bonus_updates_save_result(self, _mock_roll):
        participant = {"active_effects": [_bless_effect()]}
        result = RollResult(
            event_id="e2",
            roll_type="save",
            actor_kind="player",
            actor_ref_id="p1",
            actor_display_name="Lia",
            rolls=[9, 9],
            selected_roll=9,
            advantage_mode="normal",
            modifier_used=1,
            override_used=False,
            formula="1d20 + 1",
            total=10,
            ability="wisdom",
            dc=13,
            success=False,
            roll_source="system",
            timestamp="2026-01-01T00:00:00Z",
        )
        CombatService._apply_roll_bonus_dice_to_roll_result(
            participant=participant,
            roll_result=result,
            roll_type="save",
        )
        self.assertEqual(result.total, 14)
        self.assertTrue(result.success)
