"""Tests for Inflict Wounds / Infligir Ferimentos (issue #373).

Covers:
- Seed/catalog contract (level 1, necromancy, melee_spell, 3d10 necrotic, touch range)
- Upcast context resolution: +1d10 per slot level above 1
- Runtime cast flow: hit queues damage roll, miss deals no damage, upcast uses higher dice
"""

from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.combat import CombatCastSpellRequest, CombatResolveSpellEffectRequest
from app.schemas.combat_spells import CombatResolveSpellContextRequest
from app.services.combat import CombatService


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class InflictWoundsSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        cls.spells = {s["canonicalKey"]: s for s in data.get("spells", [])}

    def test_seed_has_inflict_wounds(self):
        self.assertIn("inflict_wounds", self.spells)

    def test_seed_core_contract(self):
        s = self.spells["inflict_wounds"]
        self.assertEqual(s["level"], 1)
        self.assertEqual(s["school"], "necromancy")
        self.assertEqual(s["castingTimeType"], "action")
        self.assertEqual(s["rangeMeters"], 1.5)
        self.assertEqual(s["rangeKind"], "touch")
        self.assertEqual(s["attackType"], "melee_spell")
        self.assertEqual(s["damageDice"], "3d10")
        self.assertEqual(s["damageType"], "Necrotic")
        self.assertFalse(s["concentration"])

    def test_seed_upcast_plus_1d10_per_slot(self):
        u = self.spells["inflict_wounds"]["upcast"]
        self.assertEqual(u["mode"], "extra_damage_dice")
        self.assertEqual(u["dice"], "1d10")
        self.assertEqual(u["levelStep"], 1)

    def test_seed_no_effects(self):
        s = self.spells["inflict_wounds"]
        effects = s.get("effects") or []
        self.assertEqual(effects, [], "inflict_wounds must not have rider effects")


# ---------------------------------------------------------------------------
# Upcast context
# ---------------------------------------------------------------------------

class InflictWoundsUpcastContextTests(unittest.TestCase):
    def _catalog_spell(self):
        return type(
            "CatalogSpell",
            (),
            {
                "canonical_key": "inflict_wounds",
                "name_en": "Inflict Wounds",
                "name_pt": "Infligir Ferimentos",
                "level": 1,
                "resolution_type": "damage",
                "damage_dice": "3d10",
                "heal_dice": None,
                "damage_type": "Necrotic",
                "saving_throw": None,
                "save_success_outcome": None,
                "upcast_json": {"mode": "extra_damage_dice", "dice": "1d10", "levelStep": 1},
                "cantrip_scaling_json": None,
                "casting_time_type": "action",
                "target_type": "melee",
                "selection_type": "creature",
                "origin_type": "caster",
                "target_anchor": "selected_target",
                "attack_type": "melee_spell",
                "range_kind": "touch",
                "effect_timing": "immediate",
                "area_shape": None,
                "range_meters": 1.5,
                "duration": "Instantaneous",
                "concentration": False,
                "max_targets": 1,
                "requires_target_sight": True,
                "requires_target_effect": True,
                "requires_point_sight": False,
                "requires_point_effect": False,
                "effects_json": [],
            },
        )()

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
                    "display_name": "Cleric",
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
                    "spells": [{"canonicalKey": "inflict_wounds", "level": 1, "prepared": True}],
                    "slots": {str(slot_level): {"used": 0, "max": 3}},
                }
            },
        )
        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=self._catalog_spell()),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)),
        ):
            return CombatService.resolve_spell_context(
                None,
                "s1",
                CombatResolveSpellContextRequest(
                    actor_participant_id="p1",
                    spell_canonical_key="inflict_wounds",
                    spell_mode="spell_attack",
                    slot_level=slot_level,
                ),
                "u1",
                False,
            )

    def test_context_damage_preview_scales_with_slot(self):
        self.assertEqual(self._resolve_context(1)["damage_preview"], "3d10")
        self.assertEqual(self._resolve_context(2)["damage_preview"], "4d10")
        self.assertEqual(self._resolve_context(3)["damage_preview"], "5d10")
        self.assertEqual(self._resolve_context(4)["damage_preview"], "6d10")


# ---------------------------------------------------------------------------
# Cast flow E2E
# ---------------------------------------------------------------------------

class InflictWoundsCastFlowE2ETests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = MagicMock()
        self.db.exec.return_value.first.return_value = MagicMock(max_hp=20)
        self.state = CombatState(
            id="combat-1",
            session_id="session-123",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "cleric-1",
                    "kind": "player",
                    "display_name": "Cleric",
                    "status": "active",
                    "team": "players",
                    "actor_user_id": "user-1",
                    "active_effects": [],
                    "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
                },
                {
                    "id": "e1",
                    "ref_id": "enemy-1",
                    "kind": "session_entity",
                    "display_name": "Zombie",
                    "status": "active",
                    "team": "enemies",
                    "active_effects": [],
                    "hp": 20,
                },
            ],
            local_distances={"cleric-1": {"enemy-1": 1.5}},
            use_map=False,
        )

    def _catalog_spell(self, slot_level: int = 1):
        return type(
            "CatalogSpell",
            (),
            {
                "canonical_key": "inflict_wounds",
                "name_en": "Inflict Wounds",
                "name_pt": "Infligir Ferimentos",
                "level": 1,
                "resolution_type": "damage",
                "damage_dice": "3d10",
                "heal_dice": None,
                "damage_type": "Necrotic",
                "saving_throw": None,
                "save_success_outcome": None,
                "upcast_json": {"mode": "extra_damage_dice", "dice": "1d10", "levelStep": 1},
                "cantrip_scaling_json": None,
                "casting_time_type": "action",
                "target_type": "melee",
                "selection_type": "creature",
                "origin_type": "caster",
                "target_anchor": "selected_target",
                "attack_type": "melee_spell",
                "range_kind": "touch",
                "effect_timing": "immediate",
                "area_shape": None,
                "range_meters": 1.5,
                "duration": "Instantaneous",
                "concentration": False,
                "max_targets": 1,
                "requires_target_sight": True,
                "requires_target_effect": True,
                "requires_point_sight": False,
                "requires_point_effect": False,
                "effects_json": [],
            },
        )()

    def _attacker_state(self, slot_level: int = 1):
        return SessionState(
            id="state-cleric",
            session_id="session-123",
            player_user_id="cleric-1",
            state_json={
                "spellcasting": {
                    "spells": [{"canonicalKey": "inflict_wounds", "level": 1, "prepared": True}],
                    "slots": {str(slot_level): {"used": 0, "max": 2}},
                }
            },
        )

    def _get_stats_side_effect(self, attacker_state):
        def _side_effect(_db, ref_id, kind, _session_id="", **_kwargs):
            if ref_id == "cleric-1" and kind == "player":
                return (attacker_state, 12, 10, 10, 2, 3)
            return (MagicMock(campaign_entity_id="ce-1", current_hp=20), 14, 10, 10, 2, 0)
        return _side_effect

    async def test_real_cast_hit_queues_damage_roll(self):
        attacker_state = self._attacker_state(1)

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=self._catalog_spell()),
            patch("app.services.combat.CombatService._get_stats", side_effect=self._get_stats_side_effect(attacker_state)),
            patch("app.services.combat.CombatService._emit_player_state_update"),
            patch("app.services.combat.CombatService._emit_entity_hp_update"),
            patch("app.services.combat.CombatService._emit_state"),
            patch("app.services.combat.CombatService._emit_log"),
            patch("app.services.combat.CombatService._emit_and_persist_log"),
            patch("app.services.combat.CombatService._record_spell_cast_rejected_activity"),
        ):
            first = await CombatService.cast_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id="p1",
                    target_ref_id="enemy-1",
                    spell_canonical_key="inflict_wounds",
                    spell_mode="spell_attack",
                    slot_level=1,
                    roll_source="manual",
                    manual_roll=17,
                ),
                "user-1",
                False,
            )
            self.assertTrue(first["is_hit"])
            self.assertIsNotNone(first["pending_spell_id"])
            self.assertIsNone(first["concentration_group"])
            self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["1"]["used"], 1)

            second = await CombatService.cast_spell_effect(
                self.db,
                "session-123",
                CombatResolveSpellEffectRequest(
                    actor_participant_id="p1",
                    pending_spell_id=first["pending_spell_id"],
                    roll_source="manual",
                    manual_rolls=[5, 5, 5],
                ),
                "user-1",
                False,
            )
            self.assertEqual(second["effect_dice"], "3d10")
            self.assertGreater(second["damage"], 0)
            target = next(p for p in self.state.participants if p["id"] == "e1")
            self.assertEqual(target.get("active_effects", []), [], "no rider effects expected")

    async def test_real_cast_miss_deals_no_damage(self):
        attacker_state = self._attacker_state(1)

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=self._catalog_spell()),
            patch("app.services.combat.CombatService._get_stats", side_effect=self._get_stats_side_effect(attacker_state)),
            patch("app.services.combat.CombatService._emit_player_state_update"),
            patch("app.services.combat.CombatService._emit_entity_hp_update"),
            patch("app.services.combat.CombatService._emit_state"),
            patch("app.services.combat.CombatService._emit_log"),
            patch("app.services.combat.CombatService._emit_and_persist_log"),
            patch("app.services.combat.CombatService._record_spell_cast_rejected_activity"),
        ):
            result = await CombatService.cast_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id="p1",
                    target_ref_id="enemy-1",
                    spell_canonical_key="inflict_wounds",
                    spell_mode="spell_attack",
                    slot_level=1,
                    roll_source="manual",
                    manual_roll=1,
                ),
                "user-1",
                False,
            )
            self.assertFalse(result["is_hit"])
            self.assertEqual(result["damage"], 0)
            self.assertIsNone(result["pending_spell_id"])
            self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["1"]["used"], 1)

    async def test_real_upcast_hit_uses_higher_dice(self):
        attacker_state = self._attacker_state(3)

        # Rebuild state to avoid action_used carry-over
        state = CombatState(
            id="combat-1",
            session_id="session-123",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "cleric-1",
                    "kind": "player",
                    "display_name": "Cleric",
                    "status": "active",
                    "team": "players",
                    "actor_user_id": "user-1",
                    "active_effects": [],
                    "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
                },
                {
                    "id": "e1",
                    "ref_id": "enemy-1",
                    "kind": "session_entity",
                    "display_name": "Zombie",
                    "status": "active",
                    "team": "enemies",
                    "active_effects": [],
                    "hp": 20,
                },
            ],
            local_distances={"cleric-1": {"enemy-1": 1.5}},
            use_map=False,
        )

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=self._catalog_spell(3)),
            patch("app.services.combat.CombatService._get_stats", side_effect=self._get_stats_side_effect(attacker_state)),
            patch("app.services.combat.CombatService._emit_player_state_update"),
            patch("app.services.combat.CombatService._emit_entity_hp_update"),
            patch("app.services.combat.CombatService._emit_state"),
            patch("app.services.combat.CombatService._emit_log"),
            patch("app.services.combat.CombatService._emit_and_persist_log"),
            patch("app.services.combat.CombatService._record_spell_cast_rejected_activity"),
        ):
            first = await CombatService.cast_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id="p1",
                    target_ref_id="enemy-1",
                    spell_canonical_key="inflict_wounds",
                    spell_mode="spell_attack",
                    slot_level=3,
                    roll_source="manual",
                    manual_roll=17,
                ),
                "user-1",
                False,
            )
            second = await CombatService.cast_spell_effect(
                self.db,
                "session-123",
                CombatResolveSpellEffectRequest(
                    actor_participant_id="p1",
                    pending_spell_id=first["pending_spell_id"],
                    roll_source="manual",
                    manual_rolls=[5, 5, 5, 5, 5],
                ),
                "user-1",
                False,
            )
            self.assertEqual(second["effect_dice"], "5d10")
            self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["3"]["used"], 1)


if __name__ == "__main__":
    unittest.main()
