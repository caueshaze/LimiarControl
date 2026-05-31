from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.models.combat import CombatPhase
from app.services.combat import CombatService, CombatServiceError
from app.services.crown_of_madness import remove_crown_of_madness_instance
from app.services.seed_paths import resolve_base_seed_path
from app.services.spell_targeting_semantics import explicit_spell_targeting_overrides


class CrownOfMadnessSeedRegistryTests(TestCombatServiceBase):
    @classmethod
    def setUpClass(cls):
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "crown_of_madness"),
            None,
        )

    def test_seed_entry_exists(self):
        self.assertIsNotNone(self.entry, "crown_of_madness not found in seed")

    def test_seed_contract(self):
        entry = self.entry
        assert entry is not None
        self.assertEqual(entry.get("level"), 2)
        self.assertEqual(entry.get("savingThrowAbility"), "wisdom")
        self.assertTrue(entry.get("concentration"))
        self.assertEqual(entry.get("rangeMeters"), 36)
        self.assertFalse(entry.get("outOfCombatCastable"))

    def test_targeting_semantics_override_exists(self):
        sem = explicit_spell_targeting_overrides().get("crown_of_madness")
        self.assertIsNotNone(sem)
        assert sem is not None
        self.assertEqual(sem.selection_type, "single_target")
        self.assertEqual(sem.origin_type, "caster")
        self.assertEqual(sem.target_anchor, "target")
        self.assertEqual(sem.effect_timing, "persistent")

    def test_context_and_registry_exist(self):
        meta = CombatService.UTILITY_SPELL_CONTEXT_META.get("crown_of_madness")
        self.assertIsInstance(meta, dict)
        assert isinstance(meta, dict)
        self.assertEqual(meta.get("initialSaveAbility"), "wisdom")
        self.assertEqual(meta.get("targetCreatureTypeRestriction"), ["humanoid"])
        spec = CombatService._get_spell_automation_spec("crown_of_madness")
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.handler_name, "_cast_crown_of_madness_automation")


class CrownOfMadnessCastTests(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.attacker = self.state.participants[0]
        self.target = self.state.participants[1]
        self.ctx = {
            "spell_name": "Crown of Madness",
            "spell_canonical_key": "crown_of_madness",
            "save_ability": "wisdom",
            "save_dc": 14,
            "duration_seconds": 60,
        }
        self.req = SimpleNamespace(variant_key=None)

    async def test_save_success_does_not_apply_effect_or_clear_concentration(self):
        roll_result = SimpleNamespace(success=True, total=16, check_modifier_sources=[], is_gm_roll=False)
        with patch(
            "app.services.combat_service.spells.automation._control_spells.resolve_saving_throw",
            return_value=roll_result,
        ), patch.object(
            CombatService,
            "_build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ), patch.object(
            CombatService,
            "_clear_concentration_for_source",
        ) as clear_mock:
            result = await CombatService._cast_crown_of_madness_automation(
                self.db,
                "session-123",
                attacker=self.attacker,
                attacker_model=SimpleNamespace(),
                actor_user_id="user-1",
                is_gm=False,
                req=self.req,
                state=self.state,
                spell_context=self.ctx,
                target_participant=self.target,
            )
        self.assertTrue(result["is_saved"])
        self.assertFalse(result["effect_applied"])
        clear_mock.assert_not_called()

    async def test_failed_save_with_immunity_does_not_clear_concentration(self):
        roll_result = SimpleNamespace(success=False, total=7, check_modifier_sources=[], is_gm_roll=False)
        with patch(
            "app.services.combat_service.spells.automation._control_spells.resolve_saving_throw",
            return_value=roll_result,
        ), patch(
            "app.services.combat_service.spells.automation._control_spells.has_condition_immunity_from_source",
            return_value=True,
        ), patch.object(
            CombatService,
            "_build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ), patch.object(
            CombatService,
            "_clear_concentration_for_source",
        ) as clear_mock:
            result = await CombatService._cast_crown_of_madness_automation(
                self.db,
                "session-123",
                attacker=self.attacker,
                attacker_model=SimpleNamespace(),
                actor_user_id="user-1",
                is_gm=False,
                req=self.req,
                state=self.state,
                spell_context=self.ctx,
                target_participant=self.target,
            )
        self.assertTrue(result["blocked_by_condition_immunity"])
        self.assertFalse(result["effect_applied"])
        clear_mock.assert_not_called()

    async def test_failed_save_applies_charmed_and_crown(self):
        roll_result = SimpleNamespace(success=False, total=5, check_modifier_sources=[], is_gm_roll=False)
        with patch(
            "app.services.combat_service.spells.automation._control_spells.resolve_saving_throw",
            return_value=roll_result,
        ), patch.object(
            CombatService,
            "_build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ):
            result = await CombatService._cast_crown_of_madness_automation(
                self.db,
                "session-123",
                attacker=self.attacker,
                attacker_model=SimpleNamespace(),
                actor_user_id="user-1",
                is_gm=False,
                req=self.req,
                state=self.state,
                spell_context=self.ctx,
                target_participant=self.target,
            )
        self.assertFalse(result["is_saved"])
        self.assertTrue(result["effect_applied"])
        effects = self.target.get("active_effects") or []
        self.assertTrue(
            any((e.get("metadata") or {}).get("source_spell_key") == "crown_of_madness" for e in effects)
        )
        self.assertTrue(
            any(e.get("kind") == "condition" and e.get("condition_type") == "charmed" for e in effects)
        )

    async def test_non_humanoid_rejected(self):
        with patch.object(CombatService, "resolve_effective_creature_type", return_value="undead"):
            with self.assertRaises(CombatServiceError):
                await CombatService._cast_crown_of_madness_automation(
                    self.db,
                    "session-123",
                    attacker=self.attacker,
                    attacker_model=SimpleNamespace(),
                    actor_user_id="user-1",
                    is_gm=False,
                    req=self.req,
                    state=self.state,
                    spell_context=self.ctx,
                    target_participant=self.target,
                )


class CrownOfMadnessForcedAttackTests(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.controlled = self.state.participants[0]
        self.target = self.state.participants[1]
        self.controlled["active_effects"] = [
            {
                "id": "crown-1",
                "kind": "spell_effect",
                "source_participant_id": "caster-1",
                "metadata": {
                    "source_spell_key": "crown_of_madness",
                    "forced_attack_pending": True,
                    "concentration_group": "grp-1",
                },
            }
        ]
        self.state.local_distances = {
            self.controlled["ref_id"]: {self.target["ref_id"]: 1.5},
            self.target["ref_id"]: {self.controlled["ref_id"]: 1.5},
        }

    async def test_null_target_marks_skipped_without_consuming_action(self):
        with patch.object(CombatService, "get_state", return_value=self.state), patch.object(
            CombatService,
            "_emit_state",
            new_callable=AsyncMock,
        ), patch.object(
            CombatService,
            "_emit_log",
            new_callable=AsyncMock,
        ):
            result = await CombatService.resolve_crown_of_madness_forced_attack(
                self.db,
                "session-123",
                actor_user_id="gm-user",
                is_gm=True,
                controlled_target_ref_id=self.controlled["ref_id"],
                forced_attack_target_ref_id=None,
            )
        self.assertTrue(result["resolved"])
        self.assertTrue(result["skipped"])
        self.assertFalse(result["actionConsumed"])

    async def test_invalid_target_does_not_mark_resolved(self):
        with patch.object(CombatService, "get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError):
                await CombatService.resolve_crown_of_madness_forced_attack(
                    self.db,
                    "session-123",
                    actor_user_id="gm-user",
                    is_gm=True,
                    controlled_target_ref_id=self.controlled["ref_id"],
                    forced_attack_target_ref_id="missing-target",
                )
        md = self.controlled["active_effects"][0]["metadata"]
        self.assertTrue(md.get("forced_attack_pending"))
        self.assertFalse(md.get("forced_attack_resolved", False))


class CrownOfMadnessTurnHooksTests(TestCombatServiceBase):
    async def test_no_maintenance_required_on_cast_turn(self):
        caster = self.state.participants[0]
        target = self.state.participants[1]
        self.state.round = 3
        target["active_effects"] = [
            {
                "id": "crown-1",
                "kind": "spell_effect",
                "source_participant_id": caster["id"],
                "metadata": {
                    "source_spell_key": "crown_of_madness",
                    "concentration_group": "grp-1",
                    "cast_round": 3,
                    "cast_turn_participant_id": caster["id"],
                    "last_maintained_round": 3,
                    "last_maintained_turn_participant_id": caster["id"],
                },
            },
            {
                "id": "charm-1",
                "kind": "condition",
                "condition_type": "charmed",
                "source_participant_id": caster["id"],
                "metadata": {
                    "source_spell_key": "crown_of_madness",
                    "concentration_group": "grp-1",
                },
            },
        ]
        await CombatService._resolve_crown_of_madness_maintenance_on_turn_end(
            self.db,
            "session-123",
            self.state,
            caster,
        )
        self.assertEqual(len(target.get("active_effects") or []), 2)

    async def test_missing_maintenance_on_subsequent_turn_removes_effect(self):
        caster = self.state.participants[0]
        target = self.state.participants[1]
        self.state.round = 4
        target["active_effects"] = [
            {
                "id": "crown-1",
                "kind": "spell_effect",
                "source_participant_id": caster["id"],
                "metadata": {
                    "source_spell_key": "crown_of_madness",
                    "concentration_group": "grp-1",
                    "cast_round": 3,
                    "cast_turn_participant_id": caster["id"],
                    "last_maintained_round": 3,
                    "last_maintained_turn_participant_id": caster["id"],
                },
            },
            {
                "id": "charm-1",
                "kind": "condition",
                "condition_type": "charmed",
                "source_participant_id": caster["id"],
                "metadata": {
                    "source_spell_key": "crown_of_madness",
                    "concentration_group": "grp-1",
                },
            },
        ]
        with patch.object(CombatService, "_emit_log", new_callable=AsyncMock):
            await CombatService._resolve_crown_of_madness_maintenance_on_turn_end(
                self.db,
                "session-123",
                self.state,
                caster,
            )
        self.assertEqual(target.get("active_effects") or [], [])

    async def test_repeat_save_success_removes_only_instance(self):
        caster = self.state.participants[0]
        target = self.state.participants[1]
        target["active_effects"] = [
            {
                "id": "crown-1",
                "kind": "spell_effect",
                "source_participant_id": caster["id"],
                "metadata": {
                    "source_spell_key": "crown_of_madness",
                    "concentration_group": "grp-1",
                    "repeat_save_ability": "wisdom",
                    "repeat_save_dc": 14,
                },
            },
            {
                "id": "charm-1",
                "kind": "condition",
                "condition_type": "charmed",
                "source_participant_id": caster["id"],
                "metadata": {
                    "source_spell_key": "crown_of_madness",
                    "concentration_group": "grp-1",
                },
            },
            {
                "id": "other-charm",
                "kind": "condition",
                "condition_type": "charmed",
                "source_participant_id": "other-caster",
                "metadata": {
                    "source_spell_key": "charm_person",
                },
            },
        ]
        roll_result = SimpleNamespace(success=True, total=16, check_modifier_sources=[])
        with patch(
            "app.services.combat_service.spells.automation._control_spells.resolve_saving_throw",
            return_value=roll_result,
        ), patch.object(
            CombatService,
            "_build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ), patch.object(
            CombatService,
            "_emit_log",
            new_callable=AsyncMock,
        ):
            await CombatService._resolve_crown_of_madness_repeat_save_on_turn_end(
                self.db,
                "session-123",
                self.state,
                target,
            )
        effects = target.get("active_effects") or []
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["id"], "other-charm")


class CrownOfMadnessCleanupIsolationTests(TestCombatServiceBase):
    def test_remove_instance_keeps_other_sources(self):
        target = self.state.participants[1]
        target["active_effects"] = [
            {
                "id": "crown-1",
                "kind": "spell_effect",
                "metadata": {
                    "source_spell_key": "crown_of_madness",
                    "concentration_group": "grp-1",
                },
            },
            {
                "id": "charm-1",
                "kind": "condition",
                "condition_type": "charmed",
                "metadata": {
                    "source_spell_key": "crown_of_madness",
                    "concentration_group": "grp-1",
                },
            },
            {
                "id": "crown-2",
                "kind": "spell_effect",
                "metadata": {
                    "source_spell_key": "crown_of_madness",
                    "concentration_group": "grp-2",
                },
            },
        ]
        remove_crown_of_madness_instance(self.state, concentration_group="grp-1")
        remaining_ids = {e.get("id") for e in (target.get("active_effects") or [])}
        self.assertEqual(remaining_ids, {"crown-2"})
