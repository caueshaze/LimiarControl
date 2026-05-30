from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.combat import CombatCastSpellRequest, CombatResolveSpellEffectRequest
from app.schemas.base_spell_effects import SpellDeclarativeEffect
from app.schemas.combat_spells import CombatResolveSpellContextRequest
from app.schemas.roll import RollResult
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_attacks import resolve_attack_advantage


class GuidingBoltSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        cls.spells = {s["canonicalKey"]: s for s in data.get("spells", [])}

    def test_seed_has_guiding_bolt_core_contract(self):
        self.assertIn("guiding_bolt", self.spells)
        s = self.spells["guiding_bolt"]
        self.assertEqual(s["level"], 1)
        self.assertEqual(s["school"], "evocation")
        self.assertEqual(s["castingTimeType"], "action")
        self.assertEqual(s["rangeMeters"], 36)
        self.assertEqual(s["attackType"], "ranged_spell")
        self.assertEqual(s["damageDice"], "4d6")
        self.assertEqual(s["damageType"], "Radiant")
        self.assertFalse(s["concentration"])

    def test_seed_has_upcast_plus_1d6_per_slot(self):
        s = self.spells["guiding_bolt"]
        self.assertEqual(s["upcast"]["mode"], "extra_damage_dice")
        self.assertEqual(s["upcast"]["dice"], "1d6")
        self.assertEqual(s["upcast"]["levelStep"], 1)

    def test_seed_has_attack_advantage_rider(self):
        s = self.spells["guiding_bolt"]
        eff = s["effects"][0]
        self.assertEqual(eff["type"], "attack_advantage_against_target")
        self.assertEqual(eff["target"], "selected_target")
        self.assertEqual(eff["duration"]["type"], "until_turn_end")
        self.assertEqual(eff["duration"]["anchor"], "caster")
        self.assertEqual(eff["params"]["mode"], "advantage")
        self.assertEqual(eff["params"]["roll_types"], ["attack"])
        self.assertEqual(eff["params"]["applies_to_attackers"], "any")
        self.assertTrue(eff["params"]["consume_on_apply"])

    def test_schema_accepts_attack_advantage_rider(self):
        eff = SpellDeclarativeEffect.model_validate(
            {
                "type": "attack_advantage_against_target",
                "target": "selected_target",
                "duration": {"type": "until_turn_end", "anchor": "caster"},
                "params": {
                    "mode": "advantage",
                    "roll_types": ["attack"],
                    "applies_to_attackers": "any",
                    "consume_on_apply": True,
                },
            }
        )
        self.assertEqual(eff.type, "attack_advantage_against_target")


class GuidingBoltUpcastContextTests(unittest.TestCase):
    def _resolve_context(self, slot_level: int) -> dict:
        from app.models.combat import CombatPhase, CombatState
        from app.models.session_state import SessionState

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
                    "spells": [{"canonicalKey": "guiding_bolt", "level": 1, "prepared": True}],
                    "slots": {str(slot_level): {"used": 0, "max": 3}},
                }
            },
        )
        catalog_spell = type(
            "CatalogSpell",
            (),
            {
                "canonical_key": "guiding_bolt",
                "name_en": "Guiding Bolt",
                "name_pt": "Raio Guiador",
                "level": 1,
                "resolution_type": "damage",
                "damage_dice": "4d6",
                "heal_dice": None,
                "damage_type": "Radiant",
                "saving_throw": None,
                "save_success_outcome": None,
                "upcast_json": {"mode": "extra_damage_dice", "dice": "1d6", "levelStep": 1},
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
                "range_meters": 36,
                "duration": "1 round",
                "concentration": False,
                "max_targets": 1,
                "requires_target_sight": True,
                "requires_target_effect": True,
                "requires_point_sight": False,
                "requires_point_effect": False,
                "effects_json": [
                    {
                        "type": "attack_advantage_against_target",
                        "target": "selected_target",
                        "duration": {"type": "until_turn_end", "anchor": "caster"},
                        "params": {
                            "mode": "advantage",
                            "roll_types": ["attack"],
                            "applies_to_attackers": "any",
                            "consume_on_apply": True,
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
                    spell_canonical_key="guiding_bolt",
                    spell_mode="spell_attack",
                    slot_level=slot_level,
                ),
                "u1",
                False,
            )

    def test_context_damage_preview_scales_with_slot(self):
        self.assertEqual(self._resolve_context(1)["damage_preview"], "4d6")
        self.assertEqual(self._resolve_context(2)["damage_preview"], "5d6")
        self.assertEqual(self._resolve_context(3)["damage_preview"], "6d6")
        self.assertEqual(self._resolve_context(4)["damage_preview"], "7d6")


class GuidingBoltRiderAdvantageTests(unittest.TestCase):
    def _target_with_rider(self, effect_id: str = "eff-gb") -> dict:
        return {
            "id": "e1",
            "kind": "entity",
            "display_name": "Goblin",
            "active_effects": [
                {
                    "id": effect_id,
                    "kind": "spell_effect",
                    "metadata": {
                        "source_spell_key": "guiding_bolt",
                        "source_spell_name": "Raio Guiador",
                        "marked_target_participant_id": "e1",
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
            ],
        }

    def test_next_attack_against_marked_target_gets_advantage(self):
        attacker = {"id": "p2", "active_effects": []}
        target = self._target_with_rider()
        ctx = resolve_attack_advantage(attacker, target, "ranged")
        self.assertEqual(ctx.result, "advantage")
        self.assertIn("eff-gb", ctx.consumed_effect_ids_on_roll)

    def test_other_target_does_not_get_or_consume(self):
        attacker = {"id": "p2", "active_effects": []}
        target = self._target_with_rider()
        target["id"] = "e2"
        ctx = resolve_attack_advantage(attacker, target, "ranged")
        self.assertEqual(ctx.result, "normal")
        self.assertEqual(ctx.consumed_effect_ids_on_roll, [])

    def test_consume_effect_id_removes_only_matched_effect(self):
        participant = self._target_with_rider("eff-1")
        participant["active_effects"].append(
            {
                "id": "eff-2",
                "kind": "spell_effect",
                "metadata": {"source_spell_key": "other"},
            }
        )
        removed = CombatService._consume_effect_ids(participant, ["eff-1"])
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]["id"], "eff-1")
        self.assertEqual([e["id"] for e in participant["active_effects"]], ["eff-2"])

    @patch("app.services.combat_service.condition_effects_predicates_parts.predicates_spell_metadata._roll_dice_expression", return_value=2)
    def test_rider_not_consumed_by_non_attack_roll_dice_pipeline(self, _mock_roll):
        # Ability/save pipelines only consume roll_dice_modifier with consume_on_apply,
        # not the Guiding Bolt attack-advantage rider.
        participant = self._target_with_rider()
        result = RollResult(
            event_id="e1",
            roll_type="ability",
            actor_kind="player",
            actor_ref_id="p1",
            actor_display_name="Lia",
            rolls=[10, 10],
            selected_roll=10,
            advantage_mode="normal",
            modifier_used=3,
            override_used=False,
            formula="1d20 + 3",
            total=13,
            dc=12,
            success=True,
            roll_source="system",
            timestamp="2026-01-01T00:00:00Z",
        )
        consumed = CombatService._apply_roll_bonus_dice_to_roll_result(
            participant=participant,
            roll_result=result,
            roll_type="ability",
        )
        self.assertEqual(consumed, [])
        self.assertEqual(len(participant["active_effects"]), 1)


class GuidingBoltCastFlowE2ETests(unittest.IsolatedAsyncioTestCase):
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
                    "ref_id": "player-123",
                    "kind": "player",
                    "display_name": "Lia",
                    "status": "active",
                    "team": "players",
                    "actor_user_id": "user-1",
                    "active_effects": [],
                    "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
                },
                {
                    "id": "e1",
                    "ref_id": "enemy-123",
                    "kind": "session_entity",
                    "display_name": "Goblin",
                    "status": "active",
                    "team": "enemies",
                    "active_effects": [],
                    "hp": 20,
                },
            ],
            local_distances={"player-123": {"enemy-123": 9.0}},
            use_map=False,
        )

    def _catalog_spell(self):
        return type(
            "CatalogSpell",
            (),
            {
                "canonical_key": "guiding_bolt",
                "name_en": "Guiding Bolt",
                "name_pt": "Raio Guiador",
                "level": 1,
                "resolution_type": "damage",
                "damage_dice": "4d6",
                "heal_dice": None,
                "damage_type": "Radiant",
                "saving_throw": None,
                "save_success_outcome": None,
                "upcast_json": {"mode": "extra_damage_dice", "dice": "1d6", "levelStep": 1},
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
                "range_meters": 36,
                "duration": "1 round",
                "concentration": False,
                "max_targets": 1,
                "requires_target_sight": True,
                "requires_target_effect": True,
                "requires_point_sight": False,
                "requires_point_effect": False,
                "effects_json": [
                    {
                        "type": "attack_advantage_against_target",
                        "target": "selected_target",
                        "duration": {"type": "until_turn_end", "anchor": "caster"},
                        "params": {
                            "mode": "advantage",
                            "roll_types": ["attack"],
                            "applies_to_attackers": "any",
                            "consume_on_apply": True,
                        },
                    }
                ],
            },
        )()

    async def test_real_cast_hit_applies_damage_and_rider(self):
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "spellcasting": {
                    "spells": [{"canonicalKey": "guiding_bolt", "level": 1, "prepared": True}],
                    "slots": {"1": {"used": 0, "max": 2}},
                }
            },
        )

        def get_stats_side_effect(_db, ref_id, kind, _session_id="", **_kwargs):
            if ref_id == "player-123" and kind == "player":
                return (attacker_state, 12, 10, 10, 2, 3)
            return (MagicMock(campaign_entity_id="ce-1", current_hp=20), 14, 10, 10, 2, 0)

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=self._catalog_spell()),
            patch("app.services.combat.CombatService._get_stats", side_effect=get_stats_side_effect),
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
                    target_ref_id="enemy-123",
                    spell_canonical_key="guiding_bolt",
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
            self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["1"]["used"], 1)
            self.assertIsNone(first["pending_save_id"])
            self.assertIsNone(first["concentration_group"])

            second = await CombatService.cast_spell_effect(
                self.db,
                "session-123",
                CombatResolveSpellEffectRequest(
                    actor_participant_id="p1",
                    pending_spell_id=first["pending_spell_id"],
                    roll_source="manual",
                    manual_rolls=[4, 4, 4, 4],
                ),
                "user-1",
                False,
            )
            self.assertEqual(second["effect_dice"], "4d6")
            self.assertGreater(second["damage"], 0)
            target = next(p for p in self.state.participants if p["id"] == "e1")
            rider = [
                e for e in target.get("active_effects", [])
                if e.get("kind") == "spell_effect"
                and isinstance(e.get("metadata"), dict)
                and e["metadata"].get("source_spell_key") == "guiding_bolt"
            ]
            self.assertEqual(len(rider), 1)

    async def test_real_cast_miss_applies_no_damage_and_no_rider(self):
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "spellcasting": {
                    "spells": [{"canonicalKey": "guiding_bolt", "level": 1, "prepared": True}],
                    "slots": {"1": {"used": 0, "max": 2}},
                }
            },
        )

        def get_stats_side_effect(_db, ref_id, kind, _session_id="", **_kwargs):
            if ref_id == "player-123" and kind == "player":
                return (attacker_state, 12, 10, 10, 2, 3)
            return (MagicMock(campaign_entity_id="ce-1", current_hp=20), 14, 10, 10, 2, 0)

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=self._catalog_spell()),
            patch("app.services.combat.CombatService._get_stats", side_effect=get_stats_side_effect),
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
                    target_ref_id="enemy-123",
                    spell_canonical_key="guiding_bolt",
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
            target = next(p for p in self.state.participants if p["id"] == "e1")
            rider = [
                e for e in target.get("active_effects", [])
                if e.get("kind") == "spell_effect"
                and isinstance(e.get("metadata"), dict)
                and e["metadata"].get("source_spell_key") == "guiding_bolt"
            ]
            self.assertEqual(len(rider), 0)

    async def test_real_upcast_hit_uses_selected_slot_damage(self):
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "spellcasting": {
                    "spells": [{"canonicalKey": "guiding_bolt", "level": 1, "prepared": True}],
                    "slots": {"2": {"used": 0, "max": 2}},
                }
            },
        )

        def get_stats_side_effect(_db, ref_id, kind, _session_id="", **_kwargs):
            if ref_id == "player-123" and kind == "player":
                return (attacker_state, 12, 10, 10, 2, 3)
            return (MagicMock(campaign_entity_id="ce-1", current_hp=20), 14, 10, 10, 2, 0)

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=self._catalog_spell()),
            patch("app.services.combat.CombatService._get_stats", side_effect=get_stats_side_effect),
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
                    target_ref_id="enemy-123",
                    spell_canonical_key="guiding_bolt",
                    spell_mode="spell_attack",
                    slot_level=2,
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
                    manual_rolls=[3, 3, 3, 3, 3],
                ),
                "user-1",
                False,
            )
            self.assertEqual(second["effect_dice"], "5d6")
            self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["2"]["used"], 1)


if __name__ == "__main__":
    unittest.main()
