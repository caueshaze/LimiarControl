from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_predicates import LESSER_RESTORATION_CONDITIONS
from app.services.combat_service.spell_automation import CombatSpellAutomationMixin
from app.services.combat_service.exceptions import CombatServiceError
from app.services.out_of_combat_cast import (
    _SPECIAL_OOC_UTILITY_SPELLS,
    build_persisted_effects,
    check_out_of_combat_cast_eligibility,
)
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEED_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
)


def _first(value):
    mock = MagicMock()
    mock.first.return_value = value
    return mock


def _condition_effect(condition_type: str, effect_id: str = "cond-1", **meta_extra) -> dict:
    return {
        "id": effect_id,
        "kind": "condition",
        "condition_type": condition_type,
        "metadata": meta_extra,
    }


def _disease_effect(effect_id: str = "disease-1", removable: bool = True, legacy: bool = False) -> dict:
    meta: dict = {}
    if removable:
        meta["removable_by_lesser_restoration"] = True
    if legacy:
        meta["disease"] = True
    return {
        "id": effect_id,
        "kind": "condition",
        "condition_type": "disease",
        "metadata": meta,
    }


def _make_spell_ooc(**kwargs):
    defaults = dict(
        canonical_key="lesser_restoration",
        name_pt="Restauração Menor",
        name_en="Lesser Restoration",
        level=2,
        concentration=False,
        out_of_combat_castable=True,
        out_of_combat_target="self_or_ally",
        effects_json=None,
        variants_json=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _minimal_state(participants: list | None = None) -> CombatState:
    return CombatState(
        id="s1",
        session_id="sess1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=participants or [],
    )


# ---------------------------------------------------------------------------
# 1. Seed
# ---------------------------------------------------------------------------

class LesserRestorationSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SEED_PATH, encoding="utf-8") as f:
            data = json.load(f)
        cls.entry = next(
            (s for s in data.get("spells", []) if s.get("canonicalKey") == "lesser_restoration"), None
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "lesser_restoration not found in base_spells.seed.json")

    def test_level(self):
        self.assertEqual(self.entry["level"], 2)

    def test_school(self):
        self.assertEqual(self.entry["school"], "abjuration")

    def test_classes(self):
        classes = self.entry["classesJson"]
        for cls_name in ["Bard", "Cleric", "Druid", "Paladin", "Ranger"]:
            self.assertIn(cls_name, classes)

    def test_range_meters(self):
        self.assertEqual(self.entry["rangeMeters"], 0)

    def test_duration_seconds(self):
        self.assertEqual(self.entry["durationSeconds"], 0)

    def test_not_concentration(self):
        self.assertFalse(self.entry["concentration"])

    def test_not_ritual(self):
        self.assertFalse(self.entry["ritual"])

    def test_resolution_type(self):
        self.assertEqual(self.entry["resolutionType"], "utility")

    def test_selection_type(self):
        self.assertEqual(self.entry["selectionType"], "single_target")

    def test_target_anchor(self):
        self.assertEqual(self.entry["targetAnchor"], "target")

    def test_attack_type(self):
        self.assertEqual(self.entry["attackType"], "none")

    def test_range_kind(self):
        self.assertEqual(self.entry["rangeKind"], "touch")

    def test_effect_timing(self):
        self.assertEqual(self.entry["effectTiming"], "immediate")

    def test_out_of_combat_castable(self):
        self.assertTrue(self.entry.get("outOfCombatCastable"))

    def test_out_of_combat_target(self):
        self.assertEqual(self.entry.get("outOfCombatTarget"), "self_or_ally")

    def test_no_damage_dice(self):
        self.assertIsNone(self.entry.get("damageDice"))

    def test_no_saving_throw(self):
        self.assertIsNone(self.entry.get("savingThrow"))

    def test_no_cantrip_scaling(self):
        self.assertIsNone(self.entry.get("cantripScaling"))


# ---------------------------------------------------------------------------
# 2. Targeting semantics
# ---------------------------------------------------------------------------

class LesserRestorationTargetingSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sem = resolve_spell_targeting_semantics({"canonicalKey": "lesser_restoration"})

    def test_selection_type(self):
        self.assertEqual(self.sem.selection_type, "single_target")

    def test_origin_type(self):
        self.assertEqual(self.sem.origin_type, "caster")

    def test_target_anchor(self):
        self.assertEqual(self.sem.target_anchor, "target")

    def test_attack_type(self):
        self.assertEqual(self.sem.attack_type, "none")

    def test_range_kind(self):
        self.assertEqual(self.sem.range_kind, "touch")

    def test_effect_timing(self):
        self.assertEqual(self.sem.effect_timing, "immediate")


# ---------------------------------------------------------------------------
# 3. Registry
# ---------------------------------------------------------------------------

class LesserRestorationRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY.get("lesser_restoration")

    def test_registry_entry_exists(self):
        self.assertIsNotNone(self.spec)

    def test_default_mode(self):
        self.assertEqual(self.spec.default_mode, "utility")

    def test_requires_effect_payload(self):
        self.assertFalse(self.spec.requires_effect_payload)

    def test_handler_name(self):
        self.assertEqual(self.spec.handler_name, "_cast_lesser_restoration_automation")


# ---------------------------------------------------------------------------
# 4. Allowlist
# ---------------------------------------------------------------------------

class LesserRestorationAllowlistTests(unittest.TestCase):
    def test_contains_blinded(self):
        self.assertIn("blinded", LESSER_RESTORATION_CONDITIONS)

    def test_contains_deafened(self):
        self.assertIn("deafened", LESSER_RESTORATION_CONDITIONS)

    def test_contains_paralyzed(self):
        self.assertIn("paralyzed", LESSER_RESTORATION_CONDITIONS)

    def test_contains_poisoned(self):
        self.assertIn("poisoned", LESSER_RESTORATION_CONDITIONS)

    def test_excludes_stunned(self):
        self.assertNotIn("stunned", LESSER_RESTORATION_CONDITIONS)

    def test_excludes_frightened(self):
        self.assertNotIn("frightened", LESSER_RESTORATION_CONDITIONS)

    def test_excludes_exhaustion(self):
        self.assertNotIn("exhaustion", LESSER_RESTORATION_CONDITIONS)

    def test_disease_not_in_allowlist(self):
        # disease is handled separately, not in the frozenset
        self.assertNotIn("disease", LESSER_RESTORATION_CONDITIONS)


# ---------------------------------------------------------------------------
# 5. Automation handler (combat cast)
# ---------------------------------------------------------------------------

class LesserRestorationAutomationTests(unittest.IsolatedAsyncioTestCase):
    def _make_state(self, caster_id: str = "p1", target_id: str = "p2") -> CombatState:
        return CombatState(
            id="c1",
            session_id="sess1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": caster_id,
                    "ref_id": "u1",
                    "kind": "player",
                    "display_name": "Alice",
                    "active_effects": [],
                },
                {
                    "id": target_id,
                    "ref_id": "u2",
                    "kind": "player",
                    "display_name": "Bob",
                    "active_effects": [],
                },
            ],
        )

    def _make_db(self) -> MagicMock:
        db = MagicMock()
        sj = SimpleNamespace(state_json={"spellcasting": {"slots": {"2": {"used": 0, "max": 3}}}})
        db.exec.return_value = _first(sj)
        return db

    async def _cast(
        self,
        target_active_effects: list | None = None,
        variant_key: str = "poisoned",
        target_id: str = "p2",
    ) -> tuple[dict, dict]:
        db = self._make_db()
        state = self._make_state()
        caster = next(p for p in state.participants if p["id"] == "p1")
        target = next(p for p in state.participants if p["id"] == target_id)
        if target_active_effects is not None:
            target["active_effects"] = list(target_active_effects)

        req = SimpleNamespace(variant_key=variant_key, roll_source="server", override_resource_limit=False)
        spell_context = {
            "spell_name": "Restauração Menor",
            "spell_key": "lesser_restoration",
            "spell_canonical_key": "lesser_restoration",
            "slot_level": 2,
        }

        with patch("app.services.combat_service.spell_automation.flag_modified"):
            result = await CombatService._cast_lesser_restoration_automation(
                db=db,
                session_id="sess1",
                attacker=caster,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=spell_context,
                target_participant=target,
            )
        return result, target

    async def test_removes_poisoned_condition(self):
        _, target = await self._cast(
            target_active_effects=[_condition_effect("poisoned")],
            variant_key="poisoned",
        )
        condition_types = [e.get("condition_type") for e in target["active_effects"] if e.get("kind") == "condition"]
        self.assertNotIn("poisoned", condition_types)

    async def test_removes_blinded_condition(self):
        _, target = await self._cast(
            target_active_effects=[_condition_effect("blinded")],
            variant_key="blinded",
        )
        condition_types = [e.get("condition_type") for e in target["active_effects"] if e.get("kind") == "condition"]
        self.assertNotIn("blinded", condition_types)

    async def test_removes_deafened_condition(self):
        _, target = await self._cast(
            target_active_effects=[_condition_effect("deafened")],
            variant_key="deafened",
        )
        condition_types = [e.get("condition_type") for e in target["active_effects"] if e.get("kind") == "condition"]
        self.assertNotIn("deafened", condition_types)

    async def test_removes_paralyzed_condition(self):
        _, target = await self._cast(
            target_active_effects=[_condition_effect("paralyzed")],
            variant_key="paralyzed",
        )
        condition_types = [e.get("condition_type") for e in target["active_effects"] if e.get("kind") == "condition"]
        self.assertNotIn("paralyzed", condition_types)

    async def test_removes_disease_removable_by_lesser_restoration_flag(self):
        _, target = await self._cast(
            target_active_effects=[_disease_effect(removable=True)],
            variant_key="disease",
        )
        remaining = [e for e in target["active_effects"] if e.get("kind") == "condition"]
        self.assertEqual(len(remaining), 0)

    async def test_removes_disease_legacy_metadata_flag(self):
        _, target = await self._cast(
            target_active_effects=[_disease_effect(removable=False, legacy=True)],
            variant_key="disease",
        )
        remaining = [e for e in target["active_effects"] if e.get("kind") == "condition"]
        self.assertEqual(len(remaining), 0)

    async def test_disease_without_flag_not_removed_raises_400(self):
        state = self._make_state()
        caster = state.participants[0]
        target = state.participants[1]
        target["active_effects"] = [{"id": "d-1", "kind": "condition", "condition_type": "disease", "metadata": {}}]

        req = SimpleNamespace(variant_key="disease", roll_source="server", override_resource_limit=False)
        spell_context = {
            "spell_name": "Restauração Menor",
            "spell_key": "lesser_restoration",
            "spell_canonical_key": "lesser_restoration",
            "slot_level": 2,
        }
        with self.assertRaises(CombatServiceError) as ctx:
            with patch("app.services.combat_service.spell_automation.flag_modified"):
                await CombatService._cast_lesser_restoration_automation(
                    db=self._make_db(),
                    session_id="sess1",
                    attacker=caster,
                    attacker_model=MagicMock(),
                    actor_user_id="u1",
                    is_gm=False,
                    req=req,
                    state=state,
                    spell_context=spell_context,
                    target_participant=target,
                )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_no_condition_present_raises_400(self):
        state = self._make_state()
        caster = state.participants[0]
        target = state.participants[1]
        target["active_effects"] = []

        req = SimpleNamespace(variant_key="poisoned", roll_source="server", override_resource_limit=False)
        spell_context = {
            "spell_name": "Restauração Menor",
            "spell_key": "lesser_restoration",
            "spell_canonical_key": "lesser_restoration",
            "slot_level": 2,
        }
        with self.assertRaises(CombatServiceError) as ctx:
            with patch("app.services.combat_service.spell_automation.flag_modified"):
                await CombatService._cast_lesser_restoration_automation(
                    db=self._make_db(),
                    session_id="sess1",
                    attacker=caster,
                    attacker_model=MagicMock(),
                    actor_user_id="u1",
                    is_gm=False,
                    req=req,
                    state=state,
                    spell_context=spell_context,
                    target_participant=target,
                )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_missing_target_raises_400(self):
        state = self._make_state()
        caster = state.participants[0]
        req = SimpleNamespace(variant_key="poisoned", roll_source="server", override_resource_limit=False)
        spell_context = {
            "spell_name": "Restauração Menor",
            "spell_key": "lesser_restoration",
            "spell_canonical_key": "lesser_restoration",
            "slot_level": 2,
        }
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_lesser_restoration_automation(
                db=self._make_db(),
                session_id="sess1",
                attacker=caster,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=spell_context,
                target_participant=None,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_missing_variant_key_raises_400(self):
        state = self._make_state()
        caster = state.participants[0]
        target = state.participants[1]
        target["active_effects"] = [_condition_effect("poisoned")]
        req = SimpleNamespace(variant_key=None, roll_source="server", override_resource_limit=False)
        spell_context = {
            "spell_name": "Restauração Menor",
            "spell_key": "lesser_restoration",
            "spell_canonical_key": "lesser_restoration",
            "slot_level": 2,
        }
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_lesser_restoration_automation(
                db=self._make_db(),
                session_id="sess1",
                attacker=caster,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=spell_context,
                target_participant=target,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_invalid_variant_key_raises_400(self):
        state = self._make_state()
        caster = state.participants[0]
        target = state.participants[1]
        target["active_effects"] = [_condition_effect("stunned")]
        req = SimpleNamespace(variant_key="stunned", roll_source="server", override_resource_limit=False)
        spell_context = {
            "spell_name": "Restauração Menor",
            "spell_key": "lesser_restoration",
            "spell_canonical_key": "lesser_restoration",
            "slot_level": 2,
        }
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_lesser_restoration_automation(
                db=self._make_db(),
                session_id="sess1",
                attacker=caster,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=spell_context,
                target_participant=target,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_does_not_remove_other_conditions(self):
        _, target = await self._cast(
            target_active_effects=[
                _condition_effect("poisoned", "cond-poi"),
                _condition_effect("blinded", "cond-bli"),
            ],
            variant_key="poisoned",
        )
        remaining = {e["condition_type"] for e in target["active_effects"] if e.get("kind") == "condition"}
        self.assertNotIn("poisoned", remaining)
        self.assertIn("blinded", remaining)

    async def test_does_not_create_persistent_effect(self):
        initial_len = 1
        result, target = await self._cast(
            target_active_effects=[_condition_effect("poisoned")],
            variant_key="poisoned",
        )
        # The condition was removed so active_effects should be empty (0), not longer
        self.assertEqual(len(target["active_effects"]), 0)

    async def test_action_kind_utility(self):
        result, _ = await self._cast(
            target_active_effects=[_condition_effect("poisoned")],
            variant_key="poisoned",
        )
        self.assertEqual(result.get("action_kind"), "utility")

    async def test_result_has_removed_condition_key(self):
        result, _ = await self._cast(
            target_active_effects=[_condition_effect("poisoned")],
            variant_key="poisoned",
        )
        self.assertEqual(result.get("removed_condition"), "poisoned")

    async def test_no_damage_no_attack_roll(self):
        result, _ = await self._cast(
            target_active_effects=[_condition_effect("poisoned")],
            variant_key="poisoned",
        )
        self.assertEqual(result.get("damage", 0), 0)
        self.assertIsNone(result.get("roll_result"))


# ---------------------------------------------------------------------------
# 6. OOC
# ---------------------------------------------------------------------------

class LesserRestorationOocTests(unittest.TestCase):
    def test_in_special_ooc_utility_spells(self):
        self.assertIn("lesser_restoration", _SPECIAL_OOC_UTILITY_SPELLS)

    def test_check_ooc_eligibility_accepts_self(self):
        spell = _make_spell_ooc()
        state_json: dict = {"spellcasting": {"slots": {"2": {"used": 0, "max": 3}}}}
        ok, _ = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json=state_json,
            slot_level=2,
            variant_key="poisoned",
            out_of_combat_target="self_or_ally",
            target_user_id="u1",
            caster_user_id="u1",
            target_state_json=state_json,
        )
        self.assertTrue(ok)

    def test_check_ooc_eligibility_accepts_ally(self):
        spell = _make_spell_ooc()
        caster_state: dict = {"spellcasting": {"slots": {"2": {"used": 0, "max": 3}}}}
        ally_state: dict = {}
        ok, _ = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json=caster_state,
            slot_level=2,
            variant_key="poisoned",
            out_of_combat_target="self_or_ally",
            target_user_id="u2",
            caster_user_id="u1",
            target_state_json=ally_state,
        )
        self.assertTrue(ok)

    def test_build_persisted_effects_returns_empty(self):
        # lesser_restoration is in _SPECIAL_OOC_UTILITY_SPELLS but has no branch in
        # build_persisted_effects — it returns [] so the OOC route handler uses the
        # hardcoded branch in _cast_spell_out_of_combat_for_player instead
        spell = _make_spell_ooc()
        result = build_persisted_effects(
            spell=spell,
            caster_user_id="u1",
            target_user_id="u1",
            variant_key="poisoned",
            game_time_seconds=0,
        )
        self.assertEqual(result, [])

    def test_ooc_does_not_call_build_persisted_effects_for_effects(self):
        # Verify the OOC path doesn't persist any effects (not in build_persisted_effects)
        spell = _make_spell_ooc()
        result = build_persisted_effects(
            spell=spell,
            caster_user_id="u1",
            target_user_id="u2",
            variant_key="poisoned",
            game_time_seconds=100,
        )
        # No effects should be created by build_persisted_effects
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)


# ---------------------------------------------------------------------------
# 7. Spell context
# ---------------------------------------------------------------------------

class LesserRestorationSpellContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.combat_service.spells.spell_context_resolve import SpellContextResolveMixin
        cls.meta = SpellContextResolveMixin._LESSER_RESTORATION_UTILITY_META

    def test_type_condition_removal(self):
        self.assertEqual(self.meta["type"], "condition_removal")

    def test_subtype_lesser_restoration(self):
        self.assertEqual(self.meta["subtype"], "lesser_restoration")

    def test_requires_concentration_false(self):
        self.assertFalse(self.meta["requiresConcentration"])

    def test_duration_seconds_zero(self):
        self.assertEqual(self.meta["durationSeconds"], 0)

    def test_removable_conditions_list(self):
        conds = self.meta["removableConditions"]
        for c in ["blinded", "deafened", "paralyzed", "poisoned", "disease"]:
            self.assertIn(c, conds)

    def test_requires_variant_key_true(self):
        self.assertTrue(self.meta["requiresVariantKey"])

    def test_requires_target_true(self):
        self.assertTrue(self.meta["requiresTarget"])

    def test_ooc_flags(self):
        self.assertTrue(self.meta["outOfCombatCastable"])
        self.assertEqual(self.meta["outOfCombatTarget"], "self_or_ally")
