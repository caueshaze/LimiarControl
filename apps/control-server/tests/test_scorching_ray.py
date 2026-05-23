from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.combat import CombatCastSpellRequest
from app.schemas.combat_spells import CombatResolveSpellContextRequest, EffectInstanceTarget
from app.services.combat import CombatService, CombatServiceError


def _build_state() -> CombatState:
    return CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=[
            {
                "id": "p1",
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Caster",
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-1",
                "active_effects": [],
                "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
            },
            {
                "id": "e1",
                "ref_id": "entity:goblin-a",
                "kind": "session_entity",
                "display_name": "Goblin A",
                "status": "active",
                "team": "enemies",
                "visible": True,
                "active_effects": [],
            },
            {
                "id": "e2",
                "ref_id": "entity:goblin-b",
                "kind": "session_entity",
                "display_name": "Goblin B",
                "status": "active",
                "team": "enemies",
                "visible": True,
                "active_effects": [],
            },
        ],
    )


def _scorching_catalog_spell():
    return SimpleNamespace(
        canonical_key="scorching_ray",
        name_en="Scorching Ray",
        name_pt="Raio Ardente",
        level=2,
        resolution_type="damage",
        damage_dice="6d6",
        damage_type="Fire",
        heal_dice=None,
        saving_throw=None,
        save_success_outcome=None,
        upcast_json={
            "mode": "additional_effect_instances",
            "dice": "2d6",
            "perLevel": 1,
            "baseEffectInstances": 3,
        },
        cantrip_scaling_json=None,
        casting_time_type="action",
        target_type="ranged",
        max_targets=3,
        selection_type="creature",
        origin_type="caster",
        target_anchor="selected_target",
        attack_type="ranged_spell",
        range_kind="distance",
        effect_timing="immediate",
        area_shape=None,
        range_meters=36,
        radius_meters=None,
        length_meters=None,
        side_meters=None,
        duration="Instantaneous",
        concentration=False,
        requires_target_sight=True,
        requires_target_effect=True,
        requires_point_sight=False,
        requires_point_effect=False,
        effects_json=[],
        variants_json=None,
        persistent_area_json=None,
        cover_applies_to_save=None,
    )


class ScorchingRaySeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        cls.spells = {s["canonicalKey"]: s for s in data.get("spells", [])}

    def test_seed_has_scorching_ray_contract(self):
        s = self.spells["scorching_ray"]
        self.assertEqual(s["level"], 2)
        self.assertEqual(s["school"], "evocation")
        self.assertEqual(s["rangeMeters"], 36)
        self.assertEqual(s["rangeKind"], "distance")
        self.assertEqual(s["attackType"], "ranged_spell")
        self.assertEqual(s["damageType"], "Fire")
        self.assertFalse(s["concentration"])
        self.assertFalse(s["ritual"])
        self.assertEqual(s["upcast"]["mode"], "additional_effect_instances")
        self.assertEqual(s["upcast"]["dice"], "2d6")
        self.assertEqual(s["upcast"]["baseEffectInstances"], 3)
        self.assertEqual(s["upcast"]["perLevel"], 1)


class ScorchingRayResolveContextTests(unittest.TestCase):
    def _resolve(self, slot_level: int) -> dict:
        state = _build_state()
        attacker_state = SessionState(
            id="state-1",
            session_id="session-1",
            player_user_id="player-1",
            state_json={
                "spellcasting": {
                    "spells": [{"canonicalKey": "scorching_ray", "level": 2, "prepared": True}],
                    "slots": {str(slot_level): {"used": 0, "max": 2}},
                }
            },
        )
        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch(
                "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                return_value=_scorching_catalog_spell(),
            ),
            patch(
                "app.services.combat.CombatService._get_stats",
                return_value=(attacker_state, 12, 10, 10, 3, 4),
            ),
        ):
            return CombatService.resolve_spell_context(
                MagicMock(),
                "session-1",
                CombatResolveSpellContextRequest(
                    actor_participant_id="p1",
                    spell_canonical_key="scorching_ray",
                    spell_mode="spell_attack",
                    slot_level=slot_level,
                ),
                "user-1",
                False,
            )

    def test_slot_2_resolves_three_instances(self):
        result = self._resolve(2)
        self.assertEqual(result["slot_level"], 2)
        self.assertEqual(result["effect_instance_count"], 3)
        self.assertEqual(result["effect_instance_dice"], "2d6")
        self.assertEqual(result["base_effect_instance_count"], 3)
        self.assertEqual(result["upcast_added_instances"], 0)

    def test_slot_3_resolves_four_instances(self):
        result = self._resolve(3)
        self.assertEqual(result["effect_instance_count"], 4)
        self.assertEqual(result["upcast_added_instances"], 1)
        self.assertEqual(result["effect_instance_dice"], "2d6")

    def test_slot_4_resolves_five_instances(self):
        result = self._resolve(4)
        self.assertEqual(result["effect_instance_count"], 5)
        self.assertEqual(result["upcast_added_instances"], 2)
        self.assertEqual(result["effect_instance_dice"], "2d6")


class ScorchingRayInstanceValidationTests(unittest.TestCase):
    def setUp(self):
        self.state = _build_state()
        self.ctx = {
            "spell_canonical_key": "scorching_ray",
            "spell_mode": "spell_attack",
            "effect_instance_count": 3,
            "effect_instance_dice": "2d6",
        }

    def test_requires_effect_instance_targets(self):
        req = SimpleNamespace(effect_instance_targets=None)
        with self.assertRaises(CombatServiceError) as cm:
            CombatService._validate_instance_targets(req=req, spell_context=self.ctx, state=self.state)
        self.assertIn("requires effect_instance_targets", str(cm.exception))

    def test_accepts_same_target_multiple_instances(self):
        req = SimpleNamespace(
            effect_instance_targets=[
                EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a"),
                EffectInstanceTarget(instance_index=2, target_ref_id="entity:goblin-a"),
                EffectInstanceTarget(instance_index=3, target_ref_id="entity:goblin-a"),
            ]
        )
        validated = CombatService._validate_instance_targets(req=req, spell_context=self.ctx, state=self.state)
        self.assertEqual(len(validated), 3)

    def test_rejects_duplicate_instance_index(self):
        req = SimpleNamespace(
            effect_instance_targets=[
                EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a"),
                EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-b"),
                EffectInstanceTarget(instance_index=3, target_ref_id="entity:goblin-a"),
            ]
        )
        with self.assertRaises(CombatServiceError) as cm:
            CombatService._validate_instance_targets(req=req, spell_context=self.ctx, state=self.state)
        self.assertIn("Duplicate instance index", str(cm.exception))


class ScorchingRaySlotSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_instance_payloads_do_not_consume_slot(self):
        state = _build_state()
        attacker = state.participants[0]
        attacker_model = MagicMock()
        attacker_model.state_json = {"spellcasting": {"slots": {"2": {"used": 0, "max": 2}}}}
        spell_context = {
            "spell_name": "Scorching Ray",
            "spell_canonical_key": "scorching_ray",
            "spell_mode": "spell_attack",
            "selection_type": "creature",
            "target_type": "ranged",
            "attack_type": "ranged_spell",
            "range_kind": "distance",
            "range_meters": 36,
            "requires_target_sight": True,
            "requires_target_effect": True,
            "slot_level": 2,
            "effect_instance_count": 3,
            "effect_instance_dice": "2d6",
            "action_cost": "action",
            "source_kind": "spell",
        }

        bad_payloads = [
            ("duplicate", [
                EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a"),
                EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-b"),
                EffectInstanceTarget(instance_index=3, target_ref_id="entity:goblin-a"),
            ]),
            ("missing", [
                EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a"),
                EffectInstanceTarget(instance_index=2, target_ref_id="entity:goblin-b"),
            ]),
            ("invalid_target", [
                EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a"),
                EffectInstanceTarget(instance_index=2, target_ref_id="entity:unknown"),
                EffectInstanceTarget(instance_index=3, target_ref_id="entity:goblin-b"),
            ]),
            ("out_of_range", [
                EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a"),
                EffectInstanceTarget(instance_index=2, target_ref_id="entity:goblin-b"),
                EffectInstanceTarget(instance_index=4, target_ref_id="entity:goblin-a"),
            ]),
        ]

        for _name, targets in bad_payloads:
            req = CombatCastSpellRequest(
                actor_participant_id="p1",
                spell_canonical_key="scorching_ray",
                spell_mode="spell_attack",
                slot_level=2,
                effect_instance_targets=targets,
            )
            with (
                patch.object(CombatService, "_validate_cast_prerequisites", return_value=(state, attacker, attacker_model)),
                patch.object(CombatService, "_resolve_player_spell_context", return_value=spell_context),
                patch.object(CombatService, "_validate_modal_target_variant_assignments", return_value=None),
                patch.object(CombatService, "_validate_plain_multi_target_refs", return_value=None),
                patch.object(CombatService, "_consume_player_spell_slot") as consume_slot,
            ):
                with self.assertRaises(CombatServiceError):
                    await CombatService.cast_spell(
                        MagicMock(),
                        "session-1",
                        req,
                        "user-1",
                        False,
                    )
            consume_slot.assert_not_called()


class ScorchingRayPerInstanceConsumptionTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.state = _build_state()
        self.attacker = self.state.participants[0]
        self.target = self.state.participants[1]
        self.req = SimpleNamespace(
            has_advantage=False,
            has_disadvantage=False,
            concentration_roll_source="system",
            concentration_manual_roll=None,
        )
        self.spell_context = {
            "spell_mode": "spell_attack",
            "spell_canonical_key": "scorching_ray",
            "effect_instance_dice": "2d6",
            "effect_kind": "damage",
            "damage_type": "Fire",
            "attack_bonus": 5,
        }

    @patch.object(CombatService, "_get_stats", return_value=(MagicMock(), 12, None, None, None, None))
    @patch("app.services.combat_service.spells.cast_target.resolve_attack_base")
    def test_vicious_mockery_consumes_on_first_instance_only(self, resolve_attack_base_mock, _mock_stats):
        self.attacker["active_effects"] = [
            {
                "id": "vm-1",
                "kind": "spell_effect",
                "metadata": {
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
        ]
        resolve_attack_base_mock.side_effect = [
            SimpleNamespace(total=18, selected_roll=18, success=True),
            SimpleNamespace(total=17, selected_roll=17, success=True),
        ]
        with patch.object(CombatService, "_resolve_damage_roll", return_value=([], 6)), patch.object(
            CombatService, "_apply_spell_effect", return_value=(1, "", 7, None)
        ):
            CombatService._resolve_instance_attack(
                self.db, "session-1", self.state, self.attacker, self.target, self.spell_context, self.req, False
            )
            CombatService._resolve_instance_attack(
                self.db, "session-1", self.state, self.attacker, self.target, self.spell_context, self.req, False
            )

        self.assertEqual(resolve_attack_base_mock.call_args_list[0].kwargs["advantage_mode"], "disadvantage")
        self.assertEqual(resolve_attack_base_mock.call_args_list[1].kwargs["advantage_mode"], "normal")
        self.assertEqual(self.attacker["active_effects"], [])

    @patch.object(CombatService, "_get_stats", return_value=(MagicMock(), 12, None, None, None, None))
    @patch("app.services.combat_service.spells.cast_target.resolve_attack_base")
    def test_guiding_bolt_consumes_on_first_instance_only(self, resolve_attack_base_mock, _mock_stats):
        self.target["active_effects"] = [
            {
                "id": "gb-1",
                "kind": "spell_effect",
                "metadata": {
                    "source_spell_name": "Guiding Bolt",
                    "marked_target_participant_id": self.target["id"],
                    "declarative_effect": {
                        "type": "attack_advantage_against_target",
                        "params": {
                            "mode": "advantage",
                            "roll_types": ["attack"],
                            "applies_to_attackers": "any",
                            "consume_on_apply": True,
                        },
                    },
                },
            }
        ]
        resolve_attack_base_mock.side_effect = [
            SimpleNamespace(total=18, selected_roll=18, success=True),
            SimpleNamespace(total=17, selected_roll=17, success=True),
        ]
        with patch.object(CombatService, "_resolve_damage_roll", return_value=([], 6)), patch.object(
            CombatService, "_apply_spell_effect", return_value=(1, "", 7, None)
        ):
            CombatService._resolve_instance_attack(
                self.db, "session-1", self.state, self.attacker, self.target, self.spell_context, self.req, False
            )
            CombatService._resolve_instance_attack(
                self.db, "session-1", self.state, self.attacker, self.target, self.spell_context, self.req, False
            )

        self.assertEqual(resolve_attack_base_mock.call_args_list[0].kwargs["advantage_mode"], "advantage")
        self.assertEqual(resolve_attack_base_mock.call_args_list[1].kwargs["advantage_mode"], "normal")
        self.assertEqual(self.target["active_effects"], [])

