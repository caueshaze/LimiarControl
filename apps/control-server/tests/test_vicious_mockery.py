from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.base_spell_effects import SpellDeclarativeEffect
from app.schemas.combat_spells import CombatResolveSpellContextRequest
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_attacks import resolve_attack_advantage


class ViciousMockerySeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        cls.spells = {s["canonicalKey"]: s for s in data.get("spells", [])}

    def test_seed_has_vicious_mockery_core_contract(self):
        self.assertIn("vicious_mockery", self.spells)
        s = self.spells["vicious_mockery"]
        self.assertEqual(s["level"], 0)
        self.assertEqual(s["school"], "enchantment")
        self.assertEqual(s["savingThrow"], "WIS")
        self.assertEqual(s["saveSuccessOutcome"], "none")
        self.assertEqual(s["damageDice"], "1d4")
        self.assertEqual(s["damageType"], "Psychic")
        self.assertTrue(s["requiresTargetHearing"])

    def test_seed_has_next_attack_disadvantage_rider(self):
        effect = self.spells["vicious_mockery"]["effects"][0]
        self.assertEqual(effect["type"], "roll_disadvantage_modifier")
        self.assertEqual(effect["target"], "selected_target")
        self.assertEqual(effect["duration"]["type"], "until_turn_end")
        self.assertEqual(effect["duration"]["anchor"], "target")
        self.assertEqual(effect["params"]["mode"], "disadvantage")
        self.assertEqual(effect["params"]["roll_types"], ["attack"])
        self.assertTrue(effect["params"]["consume_on_apply"])
        self.assertEqual(effect["params"]["source"], "vicious_mockery")

    def test_schema_accepts_roll_disadvantage_modifier(self):
        effect = SpellDeclarativeEffect.model_validate(
            {
                "type": "roll_disadvantage_modifier",
                "target": "selected_target",
                "duration": {"type": "until_turn_end", "anchor": "target"},
                "params": {
                    "mode": "disadvantage",
                    "roll_types": ["attack"],
                    "consume_on_apply": True,
                    "source": "vicious_mockery",
                },
            }
        )
        self.assertEqual(effect.type, "roll_disadvantage_modifier")


class ViciousMockeryRuntimeTests(unittest.TestCase):
    def _attacker_with_rider(self, effect_id: str = "eff-vm") -> dict:
        return {
            "id": "t1",
            "active_effects": [
                {
                    "id": effect_id,
                    "kind": "spell_effect",
                    "metadata": {
                        "source_spell_name": "Vicious Mockery",
                        "declarative_effect": {
                            "type": "roll_disadvantage_modifier",
                            "params": {
                                "mode": "disadvantage",
                                "roll_types": ["attack"],
                                "consume_on_apply": True,
                                "source": "vicious_mockery",
                            },
                        },
                    },
                }
            ],
        }

    def test_next_attack_from_affected_target_has_disadvantage(self):
        attacker = self._attacker_with_rider()
        target = {"id": "enemy-1", "active_effects": []}
        ctx = resolve_attack_advantage(attacker, target, "melee")
        self.assertEqual(ctx.result, "disadvantage")
        self.assertIn("vicious_mockery", ctx.disadvantage_sources)
        self.assertIn("eff-vm", ctx.consumed_effect_ids_on_roll)

    def test_non_attack_roll_pipeline_does_not_consume_rider(self):
        participant = self._attacker_with_rider()
        consumed = CombatService._apply_roll_bonus_dice_to_roll_result(
            participant=participant,
            roll_result=type("Stub", (), {"total": 10, "check_modifier_sources": [], "dc": 10, "success": True})(),
            roll_type="save",
        )
        self.assertEqual(consumed, [])
        self.assertEqual(len(participant["active_effects"]), 1)

    def test_duration_contract_expires_at_end_of_target_turn(self):
        attacker = {"id": "caster-1"}
        target = {"id": "target-1"}
        effect = SpellDeclarativeEffect.model_validate(
            {
                "type": "roll_disadvantage_modifier",
                "target": "selected_target",
                "duration": {"type": "until_turn_end", "anchor": "target"},
                "params": {
                    "mode": "disadvantage",
                    "roll_types": ["attack"],
                    "consume_on_apply": True,
                    "source": "vicious_mockery",
                },
            }
        )
        kwargs = CombatService._declarative_duration_kwargs(
            effect=effect,
            attacker=attacker,
            target_participant=target,
            game_time_seconds=100,
        )
        self.assertEqual(kwargs["duration_type"], "until_turn_end")
        self.assertEqual(kwargs["expires_at_participant_id"], "target-1")


class ViciousMockeryContextTests(unittest.TestCase):
    def test_resolve_spell_context_exposes_requires_target_hearing(self):
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
                    "spells": [{"canonicalKey": "vicious_mockery", "level": 0, "prepared": True}],
                    "slots": {},
                }
            },
        )
        catalog_spell = type(
            "CatalogSpell",
            (),
            {
                "canonical_key": "vicious_mockery",
                "name_en": "Vicious Mockery",
                "name_pt": "Zombaria Viciosa",
                "level": 0,
                "resolution_type": "damage",
                "damage_dice": "1d4",
                "heal_dice": None,
                "damage_type": "Psychic",
                "saving_throw": "WIS",
                "save_success_outcome": "none",
                "upcast_json": None,
                "cantrip_scaling_json": None,
                "casting_time_type": "action",
                "target_type": "ranged",
                "selection_type": "creature",
                "origin_type": "caster",
                "target_anchor": "selected_target",
                "attack_type": "none",
                "range_kind": "distance",
                "effect_timing": "immediate",
                "area_shape": None,
                "range_meters": 18,
                "duration": "Instantaneous",
                "concentration": False,
                "max_targets": 1,
                "requires_target_sight": True,
                "requires_target_hearing": True,
                "requires_target_effect": True,
                "requires_point_sight": False,
                "requires_point_effect": False,
                "effects_json": [],
                "variants_json": None,
                "persistent_area_json": None,
                "cover_applies_to_save": None,
            },
        )()
        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=catalog_spell),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)),
        ):
            resolved = CombatService.resolve_spell_context(
                None,
                "s1",
                CombatResolveSpellContextRequest(
                    actor_participant_id="p1",
                    spell_canonical_key="vicious_mockery",
                    spell_mode="saving_throw",
                ),
                "u1",
                False,
            )
        self.assertTrue(resolved["requires_target_hearing"])

