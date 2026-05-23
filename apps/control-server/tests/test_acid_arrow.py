from __future__ import annotations

import json
import os
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.combat_spells import CombatResolveSpellContextRequest
from app.schemas.roll import RollResult
from app.services.combat import CombatService


class AcidArrowSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        cls.spells = {s["canonicalKey"]: s for s in data.get("spells", [])}

    def test_seed_has_expected_contract(self):
        self.assertIn("acid_arrow", self.spells)
        spell = self.spells["acid_arrow"]
        self.assertEqual(spell["attackType"], "ranged_spell")
        self.assertEqual(spell["damageDice"], "4d4")
        self.assertEqual(spell["attackMissOutcome"], "half_damage")
        self.assertEqual(spell["upcast"]["dice"], "1d4")
        delayed = spell["effects"][0]
        self.assertEqual(delayed["type"], "delayed_damage")
        self.assertEqual(delayed["params"]["dice"], "2d4")
        self.assertEqual(delayed["params"]["timing"], "target_turn_end")


class AcidArrowContextTests(unittest.TestCase):
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
                    "spells": [{"canonicalKey": "acid_arrow", "level": 2, "prepared": True}],
                    "slots": {str(slot_level): {"used": 0, "max": 3}},
                }
            },
        )
        catalog_spell = type(
            "CatalogSpell",
            (),
            {
                "canonical_key": "acid_arrow",
                "name_en": "Melf's Acid Arrow",
                "name_pt": "Flecha Ácida",
                "level": 2,
                "resolution_type": "damage",
                "damage_dice": "4d4",
                "heal_dice": None,
                "damage_type": "Acid",
                "saving_throw": None,
                "save_success_outcome": None,
                "attack_miss_outcome": "half_damage",
                "upcast_json": {"mode": "extra_damage_dice", "dice": "1d4", "perLevel": 1},
                "cantrip_scaling_json": None,
                "casting_time_type": "action",
                "target_type": "ranged",
                "selection_type": "creature",
                "origin_type": "caster",
                "target_anchor": "selected_target",
                "attack_type": "ranged_spell",
                "range_kind": "distance",
                "effect_timing": "immediate",
                "area_shape": None,
                "range_meters": 27,
                "duration": "Instantaneous",
                "concentration": False,
                "max_targets": 1,
                "requires_target_sight": True,
                "requires_target_effect": True,
                "requires_point_sight": False,
                "requires_point_effect": False,
                "effects_json": [
                    {
                        "type": "delayed_damage",
                        "target": "selected_target",
                        "duration": {"type": "manual"},
                        "params": {
                            "dice": "2d4",
                            "damageType": "Acid",
                            "timing": "target_turn_end",
                            "apply_once": True,
                        },
                    }
                ],
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
                    spell_canonical_key="acid_arrow",
                    spell_mode="spell_attack",
                    slot_level=slot_level,
                ),
                "u1",
                False,
            )

    def test_context_exposes_miss_outcome_and_upcasted_delayed_damage_preview(self):
        lvl2 = self._resolve_context(2)
        lvl4 = self._resolve_context(4)
        self.assertEqual(lvl2["attack_miss_outcome"], "half_damage")
        self.assertEqual(lvl2["damage_preview"], "4d4")
        self.assertEqual(lvl2["delayed_damage_preview"], "2d4")
        self.assertEqual(lvl4["damage_preview"], "6d4")
        self.assertEqual(lvl4["delayed_damage_preview"], "4d4")


class AcidArrowRuntimeTests(unittest.TestCase):
    def test_spell_attack_miss_can_apply_half_damage(self):
        req = SimpleNamespace(
            has_advantage=False,
            has_disadvantage=False,
            roll_source="system",
            manual_roll=None,
            manual_rolls=None,
            concentration_roll_source="system",
            concentration_manual_roll=None,
        )
        attacker = {"id": "p1", "ref_id": "caster", "display_name": "Caster", "active_effects": []}
        target = {"id": "e1", "ref_id": "target", "kind": "session_entity", "display_name": "Target", "active_effects": []}
        roll_result = RollResult(
            event_id="r1",
            roll_type="attack",
            actor_kind="player",
            actor_ref_id="caster",
            actor_display_name="Caster",
            rolls=[5, 11],
            selected_roll=11,
            advantage_mode="normal",
            modifier_used=5,
            override_used=False,
            formula="1d20+5",
            total=16,
            target_ac=20,
            success=False,
            timestamp=datetime.now(UTC),
        )
        targeting_result = SimpleNamespace(
            spatial_metadata=SimpleNamespace(
                cover="none",
                has_line_of_sight=True,
            )
        )
        spell_context = {
            "attack_miss_outcome": "half_damage",
            "effect_dice": "4d4",
            "damage_type": "Acid",
        }
        state = MagicMock()
        with (
            patch("app.services.combat.CombatService._get_stats", return_value=(None, 18, None, None, None, None)),
            patch("app.services.combat_service.spells.spell_resolution_attack.resolve_attack_base", return_value=roll_result),
            patch("app.services.combat.CombatService._resolve_damage_roll", return_value=([2, 2, 2, 3], 9)),
            patch("app.services.combat.CombatService._apply_spell_effect", return_value=(7, "", 11, None)),
            patch("app.services.combat_service.spells.spell_resolution_attack.flag_modified"),
        ):
            result = CombatService._resolve_spell_attack(
                None,
                "s1",
                state=state,
                attacker=attacker,
                target_p=target,
                spell_context=spell_context,
                req=req,
                is_gm=False,
                spell_mode="spell_attack",
                effect_kind="damage",
                effect_bonus=0,
                effect_roll_required=True,
                targeting_result=targeting_result,
            )
        self.assertFalse(result.is_hit)
        self.assertEqual(result.rolled_effect_total, 9)
        self.assertEqual(result.damage, 4)

    def test_turn_end_delayed_damage_applies_once_and_removes_effect(self):
        participant = {
            "id": "e1",
            "ref_id": "target",
            "kind": "session_entity",
            "display_name": "Target",
            "active_effects": [
                {
                    "id": "fx-1",
                    "kind": "damage",
                    "metadata": {
                        "delayed_damage": True,
                        "timing": "target_turn_end",
                        "damage_formula": "3d4",
                        "damage_type": "Acid",
                        "remaining_triggers": 1,
                        "source_spell_key": "acid_arrow",
                    },
                }
            ],
        }
        state = SimpleNamespace(participants=[participant])
        with (
            patch("app.services.combat_service.lifecycle_turns._roll_dice_expression", return_value=8),
            patch("app.services.combat.CombatService._apply_spell_effect", return_value=(5, "", 13, None)) as apply_effect,
            patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock),
        ):
            import asyncio

            asyncio.run(
                CombatService._resolve_turn_end_delayed_damage_effects(
                    None, "s1", state, participant
                )
            )
        apply_effect.assert_called_once()
        self.assertEqual(participant["active_effects"], [])
