from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.models.combat import CombatPhase
from app.schemas.combat import CombatCastSpellRequest, CombatGridCell
from app.services.combat import CombatService, CombatServiceError
from app.services.sleep_spell import (
    find_sleep_unconscious_effects,
    is_sleep_unconscious_effect,
    remove_sleep_unconscious_instance,
    remove_sleep_unconscious_on_damage,
)
from app.services.spell_material_components import MaterialConsumptionResult
from app.services.spell_targeting_semantics import explicit_spell_targeting_overrides
from app.services.combat_service.targeting_result import SpatialMetadata, TargetingResult
from app.services.seed_paths import resolve_base_seed_path


class SleepSeedContractTests(TestCombatServiceBase):
    @classmethod
    def setUpClass(cls):
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "sleep"),
            None,
        )

    def test_seed_entry_exists(self):
        self.assertIsNotNone(self.entry, "sleep not found in seed")

    def test_seed_basic_fields(self):
        entry = self.entry
        assert entry is not None
        self.assertEqual(entry.get("level"), 1)
        self.assertEqual(entry.get("school"), "enchantment")
        self.assertEqual(set(entry.get("classesJson") or []), {"Bard", "Sorcerer", "Wizard"})
        self.assertEqual(entry.get("rangeMeters"), 27)
        self.assertEqual(entry.get("durationSeconds"), 60)
        self.assertFalse(entry.get("concentration"))
        self.assertEqual(entry.get("areaShape"), "sphere")
        self.assertEqual(entry.get("radiusMeters"), 6)
        self.assertFalse(entry.get("outOfCombatCastable"))
        self.assertIsNone(entry.get("savingThrowAbility"))

    def test_seed_has_no_persistent_area(self):
        entry = self.entry
        assert entry is not None
        self.assertIsNone(entry.get("persistentArea"))


class SleepRegistryTests(TestCombatServiceBase):
    def test_targeting_semantics_override_exists(self):
        semantics = explicit_spell_targeting_overrides().get("sleep")
        self.assertIsNotNone(semantics)
        assert semantics is not None
        self.assertEqual(semantics.selection_type, "point")
        self.assertEqual(semantics.origin_type, "selected_point")
        self.assertEqual(semantics.effect_timing, "persistent")

    def test_spell_context_meta_exists(self):
        meta = CombatService.UTILITY_SPELL_CONTEXT_META.get("sleep")
        self.assertIsInstance(meta, dict)
        assert isinstance(meta, dict)
        self.assertEqual(meta.get("type"), "area_control")
        self.assertTrue(meta.get("usesHitPointPool"))
        self.assertEqual(meta.get("basePoolDice"), "5d8")
        self.assertEqual(meta.get("upcastAdditionalDice"), "2d8")
        self.assertTrue(meta.get("noSavingThrow"))
        self.assertEqual(meta.get("appliesCondition"), "unconscious")
        self.assertFalse(meta.get("outOfCombatCastable"))


def _enemy(pid, ref, name, *, status="active"):
    return {
        "id": pid,
        "ref_id": ref,
        "kind": "session_entity",
        "display_name": name,
        "initiative": None,
        "status": status,
        "team": "enemies",
        "visible": True,
        "actor_user_id": None,
        "active_effects": [],
    }


class SleepCastBase(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.attacker = self.state.participants[0]
        self.attacker["active_effects"] = []
        # Replace default goblin with a controlled roster.
        self.g1 = _enemy("g1", "gob-1", "Goblin 1")
        self.g2 = _enemy("g2", "gob-2", "Goblin 2")
        self.g3 = _enemy("g3", "gob-3", "Goblin 3")
        self.state.participants = [self.attacker, self.g1, self.g2, self.g3]
        self.hp_map = {"gob-1": 5, "gob-2": 8, "gob-3": 20, "player-123": 30}
        self.creature_types = {}  # ref_id -> type override; default humanoid

    def _spell_context(self, slot_level=None):
        return {
            "spell_name": "Sleep",
            "spell_canonical_key": "sleep",
            "spell_mode": "utility",
            "effect_kind": None,
            "effect_timing": "persistent",
            "origin_type": "selected_point",
            "target_anchor": "selected_point",
            "selection_type": "point",
            "attack_type": "none",
            "range_kind": "distance",
            "area_shape": "sphere",
            "range_meters": 27,
            "radius_meters": 6,
            "duration": "1 minute",
            "duration_seconds": 60,
            "concentration": False,
            "action_cost": "action",
            "source_kind": "prepared_spell",
            "slot_level": slot_level,
            "save_ability": None,
            "save_dc": None,
            "material_component_consumed": False,
            "consumable_material_options_json": None,
        }

    def _targeting_result(self, ref_ids):
        return TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="",
            affected_target_ref_ids=list(ref_ids),
            target_kind="",
            spatial_metadata=SpatialMetadata(
                affected_cells=[{"x": 10, "y": 10}],
                affected_token_ids=[],
                area_shape="sphere",
                map_version=1,
                targeting_authority="limiar_map",
            ),
        )

    def _hp_snapshot(self, db, session_id, ref_id, kind):
        return (self.hp_map.get(ref_id, 10), 30)

    def _creature_type(self, db, session_id, participant):
        return self.creature_types.get(participant["ref_id"], "humanoid")

    async def _cast_sleep(self, *, ref_ids, slot_level=None, pool_total=27, pool_dice_capture=None):
        def _roll(expr, critical=False):
            if pool_dice_capture is not None:
                pool_dice_capture.append(expr)
            return pool_total

        with patch(
            "app.services.combat_service.spells.cast_area_sleep.get_game_time_seconds",
            return_value=1000,
        ), patch(
            "app.services.combat_service.spells.cast_area_sleep._roll_dice_expression",
            side_effect=_roll,
        ), patch(
            "app.services.combat_service.spells.cast_area_sleep.has_condition_immunity_from_source",
            return_value=False,
        ), patch(
            "app.services.combat.CombatService._get_target_hp_snapshot",
            side_effect=self._hp_snapshot,
        ), patch(
            "app.services.combat.CombatService.resolve_effective_creature_type",
            side_effect=self._creature_type,
        ), patch(
            "app.services.combat.CombatService._emit_state",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_and_persist_log",
            new_callable=AsyncMock,
        ):
            return await CombatService._cast_sleep_area(
                self.db,
                "session-123",
                req=CombatCastSpellRequest(
                    actor_participant_id=self.attacker["id"],
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=10),
                    spell_canonical_key="sleep",
                ),
                attacker=self.attacker,
                actor_user_id="user-1",
                is_gm=False,
                state=self.state,
                spell_context=self._spell_context(slot_level=slot_level),
                area_spec={"shape": "sphere", "size_meters": 6, "range_meters": 27},
                targeting_result=self._targeting_result(ref_ids),
                was_overridden=False,
            )


class SleepSelectionTests(SleepCastBase):
    def _sleeping_refs(self):
        return {
            p["ref_id"]
            for p in self.state.participants
            for e in (p.get("active_effects") or [])
            if is_sleep_unconscious_effect(e)
        }

    async def test_applies_in_ascending_hp_until_pool_exhausted(self):
        # Pool 14: gob-1 (5) + gob-2 (8) = 13 affected; gob-3 (20) does not fit.
        result = await self._cast_sleep(ref_ids=["gob-1", "gob-2", "gob-3"], pool_total=14)
        self.assertEqual(self._sleeping_refs(), {"gob-1", "gob-2"})
        self.assertEqual(result["remaining_pool"], 1)
        affected_refs = [a["target_ref_id"] for a in result["affected"]]
        self.assertEqual(affected_refs, ["gob-1", "gob-2"])  # ascending order

    async def test_stops_at_first_creature_that_does_not_fit(self):
        # Pool 6: only gob-1 (5) fits; gob-2 (8) exceeds remaining 1 -> stop.
        result = await self._cast_sleep(ref_ids=["gob-1", "gob-2", "gob-3"], pool_total=6)
        self.assertEqual(self._sleeping_refs(), {"gob-1"})
        self.assertEqual(result["remaining_pool"], 1)

    async def test_unconscious_condition_metadata(self):
        await self._cast_sleep(ref_ids=["gob-1"], pool_total=27)
        effects = [e for e in self.g1["active_effects"] if is_sleep_unconscious_effect(e)]
        self.assertEqual(len(effects), 1)
        meta = effects[0]["metadata"]
        self.assertEqual(meta["source_spell_key"], "sleep")
        self.assertTrue(meta["wakes_on_damage"])
        self.assertTrue(meta["wakes_on_action"])
        self.assertTrue(meta["source_effect_id"].startswith("sleep:"))
        self.assertEqual(effects[0]["condition_type"], "unconscious")
        self.assertEqual(effects[0]["expires_at_game_time_seconds"], 1060)

    async def test_ally_in_area_is_eligible_pure_raw(self):
        # Player ally with low HP gets slept too (no hostility guardrail).
        self.hp_map["player-123"] = 4
        await self._cast_sleep(ref_ids=["player-123", "gob-3"], pool_total=10)
        self.assertIn("player-123", self._sleeping_refs())


class SleepUpcastTests(SleepCastBase):
    async def test_slot_1_rolls_5d8(self):
        capture: list[str] = []
        await self._cast_sleep(ref_ids=["gob-1"], slot_level=1, pool_total=20, pool_dice_capture=capture)
        self.assertEqual(capture, ["5d8"])

    async def test_slot_2_rolls_7d8(self):
        capture: list[str] = []
        await self._cast_sleep(ref_ids=["gob-1"], slot_level=2, pool_total=20, pool_dice_capture=capture)
        self.assertEqual(capture, ["7d8"])

    async def test_slot_3_rolls_9d8(self):
        capture: list[str] = []
        await self._cast_sleep(ref_ids=["gob-1"], slot_level=3, pool_total=20, pool_dice_capture=capture)
        self.assertEqual(capture, ["9d8"])

    async def test_default_slot_rolls_5d8(self):
        capture: list[str] = []
        await self._cast_sleep(ref_ids=["gob-1"], slot_level=None, pool_total=20, pool_dice_capture=capture)
        self.assertEqual(capture, ["5d8"])


class SleepExclusionTests(SleepCastBase):
    def _sleeping_refs(self):
        return {
            p["ref_id"]
            for p in self.state.participants
            for e in (p.get("active_effects") or [])
            if is_sleep_unconscious_effect(e)
        }

    async def test_undead_skipped(self):
        self.creature_types["gob-1"] = "undead"
        result = await self._cast_sleep(ref_ids=["gob-1", "gob-2"], pool_total=50)
        self.assertNotIn("gob-1", self._sleeping_refs())
        self.assertIn("gob-2", self._sleeping_refs())
        reasons = {s["target_ref_id"]: s["reason"] for s in result["skipped"]}
        self.assertEqual(reasons["gob-1"], "creature_type_undead")

    async def test_charm_immune_skipped(self):
        def _immune(participant, condition, *, source_participant=None):
            return participant["ref_id"] == "gob-2" and condition == "charmed"

        with patch(
            "app.services.combat_service.spells.cast_area_sleep.has_condition_immunity_from_source",
            side_effect=_immune,
        ), patch(
            "app.services.combat_service.spells.cast_area_sleep.get_game_time_seconds",
            return_value=1000,
        ), patch(
            "app.services.combat_service.spells.cast_area_sleep._roll_dice_expression",
            return_value=50,
        ), patch(
            "app.services.combat.CombatService._get_target_hp_snapshot",
            side_effect=self._hp_snapshot,
        ), patch(
            "app.services.combat.CombatService.resolve_effective_creature_type",
            side_effect=self._creature_type,
        ), patch(
            "app.services.combat.CombatService._emit_state", new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_and_persist_log", new_callable=AsyncMock,
        ):
            result = await CombatService._cast_sleep_area(
                self.db, "session-123",
                req=CombatCastSpellRequest(
                    actor_participant_id=self.attacker["id"],
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=10),
                    spell_canonical_key="sleep",
                ),
                attacker=self.attacker, actor_user_id="user-1", is_gm=False,
                state=self.state, spell_context=self._spell_context(),
                area_spec={"shape": "sphere", "size_meters": 6, "range_meters": 27},
                targeting_result=self._targeting_result(["gob-1", "gob-2"]),
                was_overridden=False,
            )
        self.assertEqual(self._sleeping_refs(), {"gob-1"})
        reasons = {s["target_ref_id"]: s["reason"] for s in result["skipped"]}
        self.assertEqual(reasons["gob-2"], "immune_to_charmed")

    async def test_already_unconscious_skipped(self):
        self.g1["active_effects"] = [{"kind": "condition", "condition_type": "unconscious", "metadata": {}}]
        result = await self._cast_sleep(ref_ids=["gob-1", "gob-2"], pool_total=50)
        reasons = {s["target_ref_id"]: s["reason"] for s in result["skipped"]}
        self.assertEqual(reasons["gob-1"], "already_unconscious")

    async def test_zero_hp_skipped(self):
        self.hp_map["gob-1"] = 0
        result = await self._cast_sleep(ref_ids=["gob-1", "gob-2"], pool_total=50)
        reasons = {s["target_ref_id"]: s["reason"] for s in result["skipped"]}
        self.assertEqual(reasons["gob-1"], "no_hp")
        self.assertNotIn("gob-1", self._sleeping_refs())


def _sleep_unconscious(effect_id="u1", source_effect_id="sleep:abc"):
    return {
        "id": effect_id,
        "kind": "condition",
        "condition_type": "unconscious",
        "metadata": {
            "source_spell_key": "sleep",
            "source_effect_id": source_effect_id,
            "wakes_on_damage": True,
            "wakes_on_action": True,
        },
    }


class SleepWakeOnDamageTests(TestCombatServiceBase):
    def test_damage_removes_sleep_unconscious(self):
        participant = {"active_effects": [_sleep_unconscious()]}
        removed = remove_sleep_unconscious_on_damage(participant, 3)
        self.assertEqual(len(removed), 1)
        self.assertEqual(participant["active_effects"], [])

    def test_zero_damage_does_nothing(self):
        participant = {"active_effects": [_sleep_unconscious()]}
        removed = remove_sleep_unconscious_on_damage(participant, 0)
        self.assertEqual(removed, [])
        self.assertEqual(len(participant["active_effects"]), 1)

    def test_other_unconscious_preserved(self):
        other = {"kind": "condition", "condition_type": "unconscious", "metadata": {"source_spell_key": "hold_person"}}
        participant = {"active_effects": [_sleep_unconscious(), other]}
        remove_sleep_unconscious_on_damage(participant, 5)
        self.assertEqual(participant["active_effects"], [other])


class SleepWakeActionTests(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.actor = self.state.participants[0]
        self.target = self.state.participants[1]
        self.target["active_effects"] = [_sleep_unconscious(effect_id="u1", source_effect_id="sleep:abc")]

    async def _wake(self, *, target_ref_id="enemy-123", source_effect_id=None):
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._emit_state", new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_log", new_callable=AsyncMock,
        ):
            return await CombatService.resolve_condition_wake_action(
                self.db,
                "session-123",
                actor_participant_id=self.actor["id"],
                target_ref_id=target_ref_id,
                actor_user_id="user-1",
                is_gm=False,
                source_effect_id=source_effect_id,
            )

    async def test_wake_removes_condition_and_consumes_action(self):
        result = await self._wake()
        self.assertTrue(result["conditionRemoved"])
        self.assertTrue(self.actor["turn_resources"]["action_used"])
        self.assertEqual(find_sleep_unconscious_effects(self.target), [])

    async def test_invalid_target_does_not_consume_action(self):
        self.target["active_effects"] = []
        with self.assertRaises(CombatServiceError):
            await self._wake()
        self.assertNotEqual(self.actor.get("turn_resources", {}).get("action_used"), True)

    async def test_source_effect_id_filters_instance(self):
        self.target["active_effects"] = [
            _sleep_unconscious(effect_id="u1", source_effect_id="sleep:abc"),
            _sleep_unconscious(effect_id="u2", source_effect_id="sleep:xyz"),
        ]
        await self._wake(source_effect_id="sleep:xyz")
        remaining = {e["id"] for e in find_sleep_unconscious_effects(self.target)}
        self.assertEqual(remaining, {"u1"})


class SleepHelperTests(TestCombatServiceBase):
    def test_remove_instance_only_targets_matching_id(self):
        participant = {"active_effects": [_sleep_unconscious("u1"), _sleep_unconscious("u2")]}
        self.assertTrue(remove_sleep_unconscious_instance(participant, "u1"))
        ids = {e["id"] for e in participant["active_effects"]}
        self.assertEqual(ids, {"u2"})

    def test_remove_instance_missing_returns_false(self):
        participant = {"active_effects": [_sleep_unconscious("u1")]}
        self.assertFalse(remove_sleep_unconscious_instance(participant, "missing"))
