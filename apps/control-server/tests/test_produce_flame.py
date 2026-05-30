from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.services.combat import CombatService
from app.services.combat_service.exceptions import CombatServiceError


def _state() -> CombatState:
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
                "display_name": "Druid",
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "u1",
                "active_effects": [],
                "turn_resources": {
                    "action_used": False,
                    "bonus_action_used": False,
                    "reaction_used": False,
                },
            },
            {
                "id": "e1",
                "ref_id": "enemy-1",
                "kind": "session_entity",
                "display_name": "Bandit",
                "status": "active",
                "team": "enemies",
                "visible": True,
                "active_effects": [],
                "turn_resources": {},
            },
        ],
    )


def _attacker_state(level: int = 5) -> SessionState:
    return SessionState(
        id="state-1",
        session_id="session-1",
        player_user_id="player-1",
        state_json={
            "level": level,
            "spellcasting": {"ability": "wisdom", "slots": {}},
        },
    )


def _context(mode: str, *, damage_preview: str = "2d8") -> dict:
    return {
        "spell_canonical_key": "produce_flame",
        "spell_name": "Criar Chamas",
        "spell_mode": mode,
        "spell_level": 0,
        "slot_level": None,
        "effect_kind": None if mode == "utility" else "damage",
        "effect_dice": damage_preview if mode == "spell_attack" else None,
        "damage_preview": damage_preview,
        "effect_bonus": 0,
        "damage_type": "Fire",
        "attack_bonus": 6,
    }


class TestProduceFlameSeed(unittest.TestCase):
    def test_seed_contract(self):
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "Base",
            "base_spells.seed.json",
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        self.assertIn("produce_flame", spells)
        spell = spells["produce_flame"]
        self.assertEqual(spell["level"], 0)
        self.assertEqual(spell["school"], "conjuration")
        self.assertIn("Druid", spell.get("classesJson", []))
        self.assertEqual(spell["selectionType"], "self")
        self.assertEqual(spell["rangeKind"], "self")
        self.assertEqual(spell["damageDice"], "1d8")
        self.assertEqual(spell["damageType"], "Fire")
        thresholds = spell.get("cantripScaling", {}).get("thresholds", [])
        self.assertEqual([t.get("characterLevel") for t in thresholds], [1, 5, 11, 17])
        self.assertEqual(thresholds[1]["damage"]["dice"], "2d8")


class TestProduceFlameContext(unittest.TestCase):
    def _catalog_spell(self):
        return SimpleNamespace(
            canonical_key="produce_flame",
            resolution_type="utility",
            saving_throw=None,
            attack_type="none",
            casting_time_type="action",
            target_type="self",
            selection_type="self",
            origin_type="caster",
            target_anchor="caster",
            range_kind="self",
            effect_timing="persistent",
            requires_target_sight=False,
            requires_target_effect=False,
            requires_point_sight=False,
            requires_point_effect=False,
            damage_dice="1d8",
            damage_type="Fire",
            heal_dice=None,
            effects_json=None,
            max_targets=None,
            area_shape=None,
            range_meters=0,
            radius_meters=None,
            length_meters=None,
            side_meters=None,
            duration="10 minutes",
            concentration=False,
            requires_target_hearing=None,
            save_success_outcome=None,
            attack_miss_outcome=None,
            attack_advantage_condition_json=None,
            on_end_effects_json=None,
            variants_json=None,
            persistent_area_json=None,
            cover_applies_to_save=None,
            upcast_json=None,
            cantrip_scaling_json={
                "scalingMode": "character_level",
                "scalingEffectType": "damage_dice",
                "thresholds": [
                    {"characterLevel": 1, "damage": {"dice": "1d8"}},
                    {"characterLevel": 5, "damage": {"dice": "2d8"}},
                    {"characterLevel": 11, "damage": {"dice": "3d8"}},
                    {"characterLevel": 17, "damage": {"dice": "4d8"}},
                ],
            },
        )

    def test_resolve_context_utility_and_throw_metadata(self):
        req = SimpleNamespace(
            spell_mode="utility",
            is_heal=False,
            is_attack=False,
            dice_expression=None,
            slot_level=None,
            heal_dice=None,
            heal_bonus=None,
            damage_dice=None,
            damage_bonus=None,
            damage_type=None,
            save_ability=None,
            save_dc=None,
            spell_attack_bonus=None,
        )
        spell = self._catalog_spell()
        mode = CombatService._resolve_spell_mode_and_targeting(
            req,
            spell,
            "produce_flame",
            0,
            2,
            4,
            "spellcasting",
            {"level": 11},
        )
        math = CombatService._resolve_spell_effect_math(req, spell, mode, 2, 4)
        upcast = CombatService._resolve_upcast_and_affinity(
            {"level": 11},
            spell,
            math["damage_type"],
            math["effect_bonus"],
            math["effect_dice"],
            math["effect_kind"],
            None,
            0,
            11,
        )
        payload = CombatService._build_spell_context_response(
            catalog_spell=spell,
            source_context={
                "spell_name": "Criar Chamas",
                "requested_canonical_key": "produce_flame",
                "selected_variant_key": None,
                "request": SimpleNamespace(target_variant_assignments=None),
                "source_kind": "spellcasting",
                "source_item_name": None,
                "inventory_item": None,
                "ignore_components": False,
                "no_free_hand_required": False,
                "source_item": None,
            },
            resolved_mode=mode,
            resolved_math=math,
            resolved_upcast=upcast,
            spell_level=0,
            caster_spell_mod=4,
        )
        self.assertEqual(payload["spell_mode"], "utility")
        self.assertEqual(payload["selection_type"], "self")
        self.assertEqual(payload["utility"]["throw_range_meters"], 9)
        self.assertEqual(payload["throw_attack"]["damage_preview"]["dice"], "3d8")

    def test_resolve_context_spell_attack_mode_switches_targeting(self):
        req = SimpleNamespace(
            spell_mode="spell_attack",
            is_heal=False,
            is_attack=False,
            dice_expression=None,
            slot_level=None,
            heal_dice=None,
            heal_bonus=None,
            damage_dice=None,
            damage_bonus=None,
            damage_type=None,
            save_ability=None,
            save_dc=None,
            spell_attack_bonus=None,
        )
        spell = self._catalog_spell()
        mode = CombatService._resolve_spell_mode_and_targeting(
            req,
            spell,
            "produce_flame",
            0,
            2,
            4,
            "spellcasting",
            {"level": 5},
        )
        math = CombatService._resolve_spell_effect_math(req, spell, mode, 2, 4)
        upcast = CombatService._resolve_upcast_and_affinity(
            {"level": 5},
            spell,
            math["damage_type"],
            math["effect_bonus"],
            math["effect_dice"],
            math["effect_kind"],
            None,
            0,
            5,
        )
        payload = CombatService._build_spell_context_response(
            catalog_spell=spell,
            source_context={
                "spell_name": "Criar Chamas",
                "requested_canonical_key": "produce_flame",
                "selected_variant_key": None,
                "request": SimpleNamespace(target_variant_assignments=None),
                "source_kind": "spellcasting",
                "source_item_name": None,
                "inventory_item": None,
                "ignore_components": False,
                "no_free_hand_required": False,
                "source_item": None,
            },
            resolved_mode=mode,
            resolved_math=math,
            resolved_upcast=upcast,
            spell_level=0,
            caster_spell_mod=4,
        )
        self.assertEqual(payload["spell_mode"], "spell_attack")
        self.assertEqual(payload["selection_type"], "creature")
        self.assertEqual(payload["attack_type"], "ranged_spell")
        self.assertEqual(payload["range_meters"], 9)


class TestProduceFlameAutomation(unittest.IsolatedAsyncioTestCase):
    async def test_utility_cast_creates_and_dedupes_effect(self):
        state = _state()
        attacker = state.participants[0]
        attacker["active_effects"] = [
            {
                "id": "old",
                "kind": "spell_effect",
                "metadata": {"source_spell_key": "produce_flame"},
            }
        ]
        result = await CombatService._cast_produce_flame_automation(
            MagicMock(),
            "session-1",
            attacker=attacker,
            attacker_model=_attacker_state(level=5),
            actor_user_id="u1",
            is_gm=False,
            req=SimpleNamespace(),
            state=state,
            spell_context=_context("utility", damage_preview="2d8"),
            target_participant=None,
        )
        effects = attacker.get("active_effects") or []
        self.assertEqual(len(effects), 1)
        meta = effects[0].get("metadata", {})
        self.assertEqual(meta.get("source_spell_key"), "produce_flame")
        self.assertEqual(meta.get("bright_light_meters"), 3)
        self.assertEqual(meta.get("dim_light_meters"), 3)
        self.assertEqual(meta.get("damage_dice"), "2d8")
        self.assertIn("created_effect_id", result)

    async def test_throw_without_active_effect_errors(self):
        state = _state()
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_produce_flame_automation(
                MagicMock(),
                "session-1",
                attacker=state.participants[0],
                attacker_model=_attacker_state(),
                actor_user_id="u1",
                is_gm=False,
                req=SimpleNamespace(roll_source="system", manual_roll=None, manual_rolls=None, has_advantage=False, has_disadvantage=False),
                state=state,
                spell_context=_context("spell_attack", damage_preview="2d8"),
                target_participant=state.participants[1],
            )

    async def test_throw_hit_applies_damage_and_consumes_effect(self):
        state = _state()
        attacker = state.participants[0]
        attacker["active_effects"] = [
            {
                "id": "fx-1",
                "kind": "spell_effect",
                "metadata": {"source_spell_key": "produce_flame", "damage_dice": "2d8"},
            }
        ]
        with (
            patch.object(
                CombatService,
                "_get_stats",
                return_value=(MagicMock(), 12, 0, 0, 2, 4),
            ),
            patch.object(
                CombatService,
                "_resolve_damage_roll",
                return_value=(None, 9),
            ),
            patch.object(
                CombatService,
                "_apply_spell_effect",
                return_value=(31, "msg", 40, None),
            ),
            patch(
                "app.services.combat_service.spells.automation._produce_flame.resolve_attack_base",
                return_value=SimpleNamespace(
                    success=True,
                    total=18,
                    selected_roll=14,
                    is_gm_roll=False,
                ),
            ),
        ):
            result = await CombatService._cast_produce_flame_automation(
                MagicMock(),
                "session-1",
                attacker=attacker,
                attacker_model=_attacker_state(level=5),
                actor_user_id="u1",
                is_gm=False,
                req=SimpleNamespace(
                    roll_source="system",
                    manual_roll=None,
                    manual_rolls=None,
                    has_advantage=False,
                    has_disadvantage=False,
                ),
                state=state,
                spell_context=_context("spell_attack", damage_preview="2d8"),
                target_participant=state.participants[1],
            )
        self.assertTrue(result["is_hit"])
        self.assertEqual(result["damage"], 9)
        self.assertEqual(attacker.get("active_effects"), [])

    async def test_throw_miss_consumes_effect_and_no_damage(self):
        state = _state()
        attacker = state.participants[0]
        attacker["active_effects"] = [
            {
                "id": "fx-1",
                "kind": "spell_effect",
                "metadata": {"source_spell_key": "produce_flame", "damage_dice": "2d8"},
            }
        ]
        with (
            patch.object(
                CombatService,
                "_get_stats",
                return_value=(MagicMock(), 18, 0, 0, 2, 4),
            ),
            patch.object(CombatService, "_apply_spell_effect") as mock_apply,
            patch(
                "app.services.combat_service.spells.automation._produce_flame.resolve_attack_base",
                return_value=SimpleNamespace(
                    success=False,
                    total=7,
                    selected_roll=7,
                    is_gm_roll=False,
                ),
            ),
        ):
            result = await CombatService._cast_produce_flame_automation(
                MagicMock(),
                "session-1",
                attacker=attacker,
                attacker_model=_attacker_state(level=5),
                actor_user_id="u1",
                is_gm=False,
                req=SimpleNamespace(
                    roll_source="system",
                    manual_roll=None,
                    manual_rolls=None,
                    has_advantage=False,
                    has_disadvantage=False,
                ),
                state=state,
                spell_context=_context("spell_attack", damage_preview="2d8"),
                target_participant=state.participants[1],
            )
        mock_apply.assert_not_called()
        self.assertFalse(result["is_hit"])
        self.assertEqual(result["damage"], 0)
        self.assertEqual(attacker.get("active_effects"), [])
