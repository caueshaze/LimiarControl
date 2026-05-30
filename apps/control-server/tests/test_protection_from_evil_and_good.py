from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_attacks import resolve_attack_advantage
from app.services.combat_service.condition_effects_predicates import (
    PROTECTION_FROM_EVIL_AND_GOOD_CREATURE_TYPES,
    PROTECTION_FROM_EVIL_AND_GOOD_CONDITIONS,
    get_participant_creature_type,
    has_condition_immunity,
    has_condition_immunity_from_source,
    is_protection_from_evil_and_good_type,
)
from app.services.combat_service.exceptions import CombatServiceError
from app.services.out_of_combat_cast import (
    _is_ooc_utility_spell,
    build_persisted_effects,
    check_out_of_combat_cast_eligibility,
)
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


SEED_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
)

_PROTECTED_TYPES = sorted(PROTECTION_FROM_EVIL_AND_GOOD_CREATURE_TYPES)


def _first(value):
    mock = MagicMock()
    mock.first.return_value = value
    return mock


def _make_state(
    caster_id: str = "p1",
    target_id: str = "p2",
    target_extra: dict | None = None,
    extra_participants: list[dict] | None = None,
) -> CombatState:
    target = {
        "id": target_id,
        "ref_id": "u2",
        "kind": "player",
        "display_name": "Bob",
        "active_effects": [],
    }
    if target_extra:
        target.update(target_extra)
    participants = [
        {
            "id": caster_id,
            "ref_id": "u1",
            "kind": "player",
            "display_name": "Alice",
            "active_effects": [],
        },
        target,
    ]
    if extra_participants:
        participants.extend(extra_participants)
    return CombatState(
        id="c1",
        session_id="sess1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=participants,
    )


def _make_db() -> MagicMock:
    db = MagicMock()
    sj = SimpleNamespace(state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 2}}}})
    db.exec.return_value = _first(sj)
    return db


def _spell_context() -> dict:
    return {
        "spell_name": "Proteção Contra Mal e Bem",
        "spell_key": "protection_from_evil_and_good",
        "spell_canonical_key": "protection_from_evil_and_good",
        "slot_level": 1,
    }


async def _cast(
    target_extra: dict | None = None,
    variant_key=None,
    extra_participants: list[dict] | None = None,
) -> tuple[dict, dict, dict]:
    db = _make_db()
    state = _make_state(target_extra=target_extra, extra_participants=extra_participants)
    caster = next(p for p in state.participants if p["id"] == "p1")
    target = next(p for p in state.participants if p["id"] == "p2")

    req = SimpleNamespace(variant_key=variant_key, roll_source="server", override_resource_limit=False)

    with (
        patch.object(
            CombatService,
            "_clear_concentration_for_source",
            return_value={"removed_effects": [], "removed_area_effects": []},
        ),
        patch.object(CombatService, "_sync_area_effects_if_changed"),
        patch.object(
            CombatService,
            "_append_effect_to_participant",
            side_effect=lambda p, e: p.setdefault("active_effects", []).append(e),
        ),
        patch("app.services.combat_service.spell_automation.flag_modified"),
        patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=100),
    ):
        result = await CombatService._cast_protection_from_evil_and_good_automation(
            db=db,
            session_id="sess1",
            attacker=caster,
            attacker_model=MagicMock(),
            actor_user_id="u1",
            is_gm=False,
            req=req,
            state=state,
            spell_context=_spell_context(),
            target_participant=target,
        )
    return result, caster, target


def _make_protection_effect(
    protected_types: list[str] | None = None,
    immune_conditions: list[str] | None = None,
) -> dict:
    types = protected_types if protected_types is not None else _PROTECTED_TYPES
    conditions = immune_conditions if immune_conditions is not None else sorted(PROTECTION_FROM_EVIL_AND_GOOD_CONDITIONS)
    return {
        "id": "eff-prot",
        "kind": "spell_effect",
        "metadata": {
            "source_spell_key": "protection_from_evil_and_good",
            "concentration": True,
            "protected_creature_types": types,
            "attack_disadvantage_against_target": True,
            "condition_immunity": True,
            "immune_conditions": conditions,
            "immune_conditions_from_creature_types": types,
            "saving_throw_advantage_against_creature_types": True,
            "saving_throw_advantage_creature_types": types,
            "declarative_save_effect": {
                "type": "saving_throw_advantage_against_creature_types",
                "params": {
                    "mode": "advantage",
                    "source": "protection_from_evil_and_good",
                    "source_creature_types": types,
                    "roll_types": ["saving_throw"],
                    "consume_on_apply": False,
                },
            },
            "grants_ac_bonus": False,
            "grants_resistance": False,
            "declarative_effect": {
                "type": "attack_disadvantage_against_target",
                "params": {
                    "mode": "disadvantage",
                    "roll_types": ["attack"],
                    "source": "protection_from_evil_and_good",
                    "requires_attacker_creature_type": types,
                    "consume_on_apply": False,
                },
            },
        },
    }


def _attacker(creature_type: str | None) -> dict:
    return {"id": "att1", "creature_type": creature_type, "active_effects": []}


def _protected_target() -> dict:
    return {"id": "tgt1", "active_effects": [_make_protection_effect()]}


def _make_ooc_spell(**kwargs) -> SimpleNamespace:
    defaults = dict(
        canonical_key="protection_from_evil_and_good",
        name_pt="Proteção Contra Mal e Bem",
        name_en="Protection from Evil and Good",
        level=1,
        concentration=True,
        out_of_combat_castable=True,
        out_of_combat_target="self_or_ally",
        effects_json=None,
        variants_json=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# 1. Seed
# ---------------------------------------------------------------------------

class ProtectionFromEvilAndGoodSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SEED_PATH, encoding="utf-8") as f:
            data = json.load(f)
        cls.entry = next(
            (s for s in data.get("spells", []) if s.get("canonicalKey") == "protection_from_evil_and_good"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry)

    def test_level(self):
        self.assertEqual(self.entry["level"], 1)

    def test_school(self):
        self.assertEqual(self.entry["school"], "abjuration")

    def test_classes_cleric(self):
        self.assertIn("Cleric", self.entry["classesJson"])

    def test_classes_paladin(self):
        self.assertIn("Paladin", self.entry["classesJson"])

    def test_classes_warlock(self):
        self.assertIn("Warlock", self.entry["classesJson"])

    def test_classes_wizard(self):
        self.assertIn("Wizard", self.entry["classesJson"])

    def test_range_meters(self):
        self.assertAlmostEqual(self.entry["rangeMeters"], 1.5)

    def test_duration_seconds(self):
        self.assertEqual(self.entry["durationSeconds"], 600)

    def test_concentration_true(self):
        self.assertTrue(self.entry["concentration"])

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
        self.assertEqual(self.entry["effectTiming"], "persistent")

    def test_out_of_combat_castable(self):
        self.assertTrue(self.entry.get("outOfCombatCastable"))

    def test_out_of_combat_target(self):
        self.assertEqual(self.entry.get("outOfCombatTarget"), "self_or_ally")

    def test_material_component_consumed_true(self):
        self.assertTrue(self.entry.get("materialComponentConsumed"))

    def test_consumable_material_options(self):
        options = self.entry.get("consumableMaterialOptions") or []
        keys = {opt.get("key") for opt in options if isinstance(opt, dict)}
        self.assertEqual(keys, {"holy_water", "powdered_silver_and_iron"})

    def test_no_damage_dice(self):
        self.assertIsNone(self.entry.get("damageDice"))

    def test_no_saving_throw(self):
        self.assertIsNone(self.entry.get("savingThrow"))

    def test_no_cantrip_scaling(self):
        self.assertIsNone(self.entry.get("cantripScaling"))

    def test_no_upcast(self):
        self.assertIsNone(self.entry.get("upcast"))


# ---------------------------------------------------------------------------
# 2. Targeting semantics
# ---------------------------------------------------------------------------

class ProtectionFromEvilAndGoodTargetingSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sem = resolve_spell_targeting_semantics({"canonicalKey": "protection_from_evil_and_good"})

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
        self.assertEqual(self.sem.effect_timing, "persistent")


# ---------------------------------------------------------------------------
# 3. Registry
# ---------------------------------------------------------------------------

class ProtectionFromEvilAndGoodRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.combat_service.spell_automation import CombatSpellAutomationMixin
        cls.spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY.get(
            "protection_from_evil_and_good"
        )

    def test_registry_entry_exists(self):
        self.assertIsNotNone(self.spec)

    def test_default_mode(self):
        self.assertEqual(self.spec.default_mode, "utility")

    def test_requires_effect_payload(self):
        self.assertFalse(self.spec.requires_effect_payload)

    def test_handler_name(self):
        self.assertEqual(
            self.spec.handler_name, "_cast_protection_from_evil_and_good_automation"
        )


# ---------------------------------------------------------------------------
# 4. Constants and helpers
# ---------------------------------------------------------------------------

class ProtectionFromEvilAndGoodConstantsTests(unittest.TestCase):
    def test_protected_types_contains_all_six(self):
        for t in ["aberration", "celestial", "elemental", "fey", "fiend", "undead"]:
            self.assertIn(t, PROTECTION_FROM_EVIL_AND_GOOD_CREATURE_TYPES)

    def test_immune_conditions_contains_charmed_frightened_possessed(self):
        self.assertIn("charmed", PROTECTION_FROM_EVIL_AND_GOOD_CONDITIONS)
        self.assertIn("frightened", PROTECTION_FROM_EVIL_AND_GOOD_CONDITIONS)
        self.assertIn("possessed", PROTECTION_FROM_EVIL_AND_GOOD_CONDITIONS)

    def test_get_participant_creature_type_from_dict(self):
        p = {"creature_type": "fiend"}
        self.assertEqual(get_participant_creature_type(p), "fiend")

    def test_get_participant_creature_type_camel_case(self):
        p = {"creatureType": "undead"}
        self.assertEqual(get_participant_creature_type(p), "undead")

    def test_get_participant_creature_type_metadata_fallback(self):
        p = {"metadata": {"creature_type": "celestial"}}
        self.assertEqual(get_participant_creature_type(p), "celestial")

    def test_get_participant_creature_type_none_when_empty(self):
        p = {}
        self.assertIsNone(get_participant_creature_type(p))

    def test_get_participant_creature_type_normalizes_case(self):
        p = {"creature_type": "FIEND"}
        self.assertEqual(get_participant_creature_type(p), "fiend")

    def test_is_protection_type_true_for_fiend(self):
        self.assertTrue(is_protection_from_evil_and_good_type({"creature_type": "fiend"}))

    def test_is_protection_type_false_for_humanoid(self):
        self.assertFalse(is_protection_from_evil_and_good_type({"creature_type": "humanoid"}))

    def test_is_protection_type_false_for_none(self):
        self.assertFalse(is_protection_from_evil_and_good_type({}))


# ---------------------------------------------------------------------------
# 5. Combat automation
# ---------------------------------------------------------------------------

class ProtectionFromEvilAndGoodAutomationTests(unittest.IsolatedAsyncioTestCase):
    async def test_creates_spell_effect_on_target(self):
        _, _, target = await _cast()
        spell_effects = [e for e in target["active_effects"] if e.get("kind") == "spell_effect"]
        self.assertEqual(len(spell_effects), 1)

    async def test_effect_source_spell_key(self):
        _, _, target = await _cast()
        effect = target["active_effects"][0]
        self.assertEqual(effect["metadata"]["source_spell_key"], "protection_from_evil_and_good")

    async def test_protected_creature_types_complete(self):
        _, _, target = await _cast()
        types = target["active_effects"][0]["metadata"]["protected_creature_types"]
        for t in ["aberration", "celestial", "elemental", "fey", "fiend", "undead"]:
            self.assertIn(t, types)

    async def test_condition_immunity_true(self):
        _, _, target = await _cast()
        self.assertTrue(target["active_effects"][0]["metadata"]["condition_immunity"])

    async def test_immune_conditions_has_charmed(self):
        _, _, target = await _cast()
        self.assertIn("charmed", target["active_effects"][0]["metadata"]["immune_conditions"])

    async def test_immune_conditions_has_frightened(self):
        _, _, target = await _cast()
        self.assertIn("frightened", target["active_effects"][0]["metadata"]["immune_conditions"])

    async def test_immune_conditions_has_possessed(self):
        _, _, target = await _cast()
        self.assertIn("possessed", target["active_effects"][0]["metadata"]["immune_conditions"])

    async def test_grants_ac_bonus_false(self):
        _, _, target = await _cast()
        self.assertFalse(target["active_effects"][0]["metadata"]["grants_ac_bonus"])

    async def test_grants_resistance_false(self):
        _, _, target = await _cast()
        self.assertFalse(target["active_effects"][0]["metadata"]["grants_resistance"])

    async def test_concentration_true(self):
        _, _, target = await _cast()
        self.assertTrue(target["active_effects"][0]["metadata"]["concentration"])

    async def test_concentration_group_created(self):
        _, _, target = await _cast()
        cg = target["active_effects"][0]["metadata"].get("concentration_group")
        self.assertIsNotNone(cg)

    async def test_declarative_effect_type(self):
        _, _, target = await _cast()
        decl = target["active_effects"][0]["metadata"]["declarative_effect"]
        self.assertEqual(decl["type"], "attack_disadvantage_against_target")

    async def test_declarative_effect_requires_attacker_creature_type(self):
        _, _, target = await _cast()
        params = target["active_effects"][0]["metadata"]["declarative_effect"]["params"]
        for t in ["aberration", "celestial", "elemental", "fey", "fiend", "undead"]:
            self.assertIn(t, params["requires_attacker_creature_type"])

    async def test_declarative_save_effect_type(self):
        _, _, target = await _cast()
        decl = target["active_effects"][0]["metadata"]["declarative_save_effect"]
        self.assertEqual(decl["type"], "saving_throw_advantage_against_creature_types")

    async def test_no_effect_on_caster_when_caster_is_not_target(self):
        _, caster, _ = await _cast()
        spell_effects = [e for e in caster["active_effects"] if e.get("kind") == "spell_effect"]
        self.assertEqual(len(spell_effects), 0)

    async def test_action_kind_utility(self):
        result, _, _ = await _cast()
        self.assertEqual(result.get("action_kind"), "utility")

    async def test_missing_target_raises_400(self):
        db = _make_db()
        state = _make_state()
        caster = state.participants[0]
        req = SimpleNamespace(variant_key=None, roll_source="server", override_resource_limit=False)
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_protection_from_evil_and_good_automation(
                db=db,
                session_id="sess1",
                attacker=caster,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=_spell_context(),
                target_participant=None,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_variant_key_raises_400(self):
        db = _make_db()
        state = _make_state()
        caster = state.participants[0]
        target = state.participants[1]
        req = SimpleNamespace(variant_key="something", roll_source="server", override_resource_limit=False)
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_protection_from_evil_and_good_automation(
                db=db,
                session_id="sess1",
                attacker=caster,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=_spell_context(),
                target_participant=target,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_suppresses_charmed_from_fiend_source(self):
        fiend_participant = {"id": "fiend1", "creature_type": "fiend", "active_effects": []}
        charmed_effect = {
            "id": "c1",
            "kind": "condition",
            "condition_type": "charmed",
            "source_participant_id": "fiend1",
        }
        _, _, target = await _cast(
            target_extra={"active_effects": [charmed_effect]},
            extra_participants=[fiend_participant],
        )
        remaining = [e for e in target["active_effects"] if e.get("condition_type") == "charmed"]
        self.assertEqual(len(remaining), 0)

    async def test_suppresses_frightened_from_undead_source(self):
        undead_p = {"id": "undead1", "creature_type": "undead", "active_effects": []}
        frightened_effect = {
            "id": "f1",
            "kind": "condition",
            "condition_type": "frightened",
            "source_participant_id": "undead1",
        }
        _, _, target = await _cast(
            target_extra={"active_effects": [frightened_effect]},
            extra_participants=[undead_p],
        )
        remaining = [e for e in target["active_effects"] if e.get("condition_type") == "frightened"]
        self.assertEqual(len(remaining), 0)

    async def test_suppresses_possessed_from_fiend_source(self):
        fiend_participant = {"id": "fiend1", "creature_type": "fiend", "active_effects": []}
        possessed_effect = {
            "id": "p1",
            "kind": "condition",
            "condition_type": "possessed",
            "source_participant_id": "fiend1",
        }
        _, _, target = await _cast(
            target_extra={"active_effects": [possessed_effect]},
            extra_participants=[fiend_participant],
        )
        remaining = [e for e in target["active_effects"] if e.get("condition_type") == "possessed"]
        self.assertEqual(len(remaining), 0)

    async def test_does_not_suppress_charmed_from_humanoid(self):
        humanoid_p = {"id": "h1", "creature_type": "humanoid", "active_effects": []}
        charmed_effect = {
            "id": "c1",
            "kind": "condition",
            "condition_type": "charmed",
            "source_participant_id": "h1",
        }
        _, _, target = await _cast(
            target_extra={"active_effects": [charmed_effect]},
            extra_participants=[humanoid_p],
        )
        remaining = [e for e in target["active_effects"] if e.get("condition_type") == "charmed"]
        self.assertEqual(len(remaining), 1)

    async def test_does_not_suppress_charmed_without_source(self):
        charmed_effect = {
            "id": "c1",
            "kind": "condition",
            "condition_type": "charmed",
            "source_participant_id": None,
        }
        _, _, target = await _cast(target_extra={"active_effects": [charmed_effect]})
        remaining = [e for e in target["active_effects"] if e.get("condition_type") == "charmed"]
        self.assertEqual(len(remaining), 1)

    async def test_does_not_suppress_possessed_without_source(self):
        possessed_effect = {
            "id": "p1",
            "kind": "condition",
            "condition_type": "possessed",
            "source_participant_id": None,
        }
        _, _, target = await _cast(target_extra={"active_effects": [possessed_effect]})
        remaining = [e for e in target["active_effects"] if e.get("condition_type") == "possessed"]
        self.assertEqual(len(remaining), 1)

    async def test_does_not_suppress_possessed_from_beast(self):
        beast_p = {"id": "b1", "creature_type": "beast", "active_effects": []}
        possessed_effect = {
            "id": "p1",
            "kind": "condition",
            "condition_type": "possessed",
            "source_participant_id": "b1",
        }
        _, _, target = await _cast(
            target_extra={"active_effects": [possessed_effect]},
            extra_participants=[beast_p],
        )
        remaining = [e for e in target["active_effects"] if e.get("condition_type") == "possessed"]
        self.assertEqual(len(remaining), 1)

    async def test_suppressed_conditions_in_extra(self):
        fiend_p = {"id": "fiend1", "creature_type": "fiend", "active_effects": []}
        charmed_effect = {
            "id": "c1",
            "kind": "condition",
            "condition_type": "charmed",
            "source_participant_id": "fiend1",
        }
        result, _, _ = await _cast(
            target_extra={"active_effects": [charmed_effect]},
            extra_participants=[fiend_p],
        )
        self.assertIn("charmed", result.get("suppressed_conditions", []))


# ---------------------------------------------------------------------------
# 6. Attack disadvantage
# ---------------------------------------------------------------------------

class AttackDisadvantageTests(unittest.TestCase):
    def test_fiend_attacking_protected_has_disadvantage(self):
        ctx = resolve_attack_advantage(_attacker("fiend"), _protected_target())
        self.assertEqual(ctx.result, "disadvantage")
        self.assertIn("protection_from_evil_and_good", ctx.disadvantage_sources)

    def test_undead_attacking_protected_has_disadvantage(self):
        ctx = resolve_attack_advantage(_attacker("undead"), _protected_target())
        self.assertEqual(ctx.result, "disadvantage")

    def test_aberration_attacking_protected_has_disadvantage(self):
        ctx = resolve_attack_advantage(_attacker("aberration"), _protected_target())
        self.assertEqual(ctx.result, "disadvantage")

    def test_celestial_attacking_protected_has_disadvantage(self):
        ctx = resolve_attack_advantage(_attacker("celestial"), _protected_target())
        self.assertEqual(ctx.result, "disadvantage")

    def test_elemental_attacking_protected_has_disadvantage(self):
        ctx = resolve_attack_advantage(_attacker("elemental"), _protected_target())
        self.assertEqual(ctx.result, "disadvantage")

    def test_fey_attacking_protected_has_disadvantage(self):
        ctx = resolve_attack_advantage(_attacker("fey"), _protected_target())
        self.assertEqual(ctx.result, "disadvantage")

    def test_humanoid_attacking_protected_no_disadvantage(self):
        ctx = resolve_attack_advantage(_attacker("humanoid"), _protected_target())
        self.assertNotIn("protection_from_evil_and_good", ctx.disadvantage_sources)

    def test_beast_attacking_protected_no_disadvantage(self):
        ctx = resolve_attack_advantage(_attacker("beast"), _protected_target())
        self.assertNotIn("protection_from_evil_and_good", ctx.disadvantage_sources)

    def test_attacker_no_creature_type_no_disadvantage(self):
        ctx = resolve_attack_advantage(_attacker(None), _protected_target())
        self.assertNotIn("protection_from_evil_and_good", ctx.disadvantage_sources)

    def test_target_without_protection_no_disadvantage(self):
        target = {"id": "tgt1", "active_effects": []}
        ctx = resolve_attack_advantage(_attacker("fiend"), target)
        self.assertNotIn("protection_from_evil_and_good", ctx.disadvantage_sources)


# ---------------------------------------------------------------------------
# 7. Condition immunity helpers
# ---------------------------------------------------------------------------

class ConditionImmunityTests(unittest.TestCase):
    def _protected_participant(self) -> dict:
        return {
            "id": "tgt1",
            "active_effects": [_make_protection_effect()],
        }

    def test_has_condition_immunity_from_source_charmed_fiend(self):
        p = self._protected_participant()
        source = {"id": "s1", "creature_type": "fiend"}
        self.assertTrue(has_condition_immunity_from_source(p, "charmed", source))

    def test_has_condition_immunity_from_source_frightened_undead(self):
        p = self._protected_participant()
        source = {"id": "s1", "creature_type": "undead"}
        self.assertTrue(has_condition_immunity_from_source(p, "frightened", source))

    def test_has_condition_immunity_from_source_poisoned_fiend_false(self):
        p = self._protected_participant()
        source = {"id": "s1", "creature_type": "fiend"}
        self.assertFalse(has_condition_immunity_from_source(p, "poisoned", source))

    def test_has_condition_immunity_from_source_charmed_humanoid_false(self):
        p = self._protected_participant()
        source = {"id": "s1", "creature_type": "humanoid"}
        self.assertFalse(has_condition_immunity_from_source(p, "charmed", source))

    def test_has_condition_immunity_from_source_charmed_no_source_false(self):
        p = self._protected_participant()
        self.assertFalse(has_condition_immunity_from_source(p, "charmed", None))

    def test_has_condition_immunity_from_source_possessed_fiend(self):
        p = self._protected_participant()
        source = {"id": "s1", "creature_type": "fiend"}
        self.assertTrue(has_condition_immunity_from_source(p, "possessed", source))

    def test_has_condition_immunity_from_source_possessed_humanoid_false(self):
        p = self._protected_participant()
        source = {"id": "s1", "creature_type": "humanoid"}
        self.assertFalse(has_condition_immunity_from_source(p, "possessed", source))

    def test_has_condition_immunity_from_source_possessed_no_source_false(self):
        p = self._protected_participant()
        self.assertFalse(has_condition_immunity_from_source(p, "possessed", None))

    def test_has_condition_immunity_legacy_still_works(self):
        p = {
            "id": "tgt1",
            "active_effects": [{
                "id": "eff1",
                "kind": "spell_effect",
                "metadata": {
                    "condition_immunity": True,
                    "immune_conditions": ["charmed"],
                },
            }],
        }
        self.assertTrue(has_condition_immunity(p, "charmed"))
        self.assertFalse(has_condition_immunity(p, "poisoned"))


# ---------------------------------------------------------------------------
# 8. OOC
# ---------------------------------------------------------------------------

class ProtectionFromEvilAndGoodOocTests(unittest.TestCase):
    def test_in_special_ooc_utility_spells(self):
        self.assertTrue(_is_ooc_utility_spell("protection_from_evil_and_good"))

    def test_build_persisted_effects_creates_one_effect(self):
        spell = _make_ooc_spell()
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="u1",
            target_user_id="u1",
            variant_key=None,
            game_time_seconds=0,
        )
        self.assertEqual(len(effects), 1)

    def test_build_persisted_effects_has_declarative_effect(self):
        spell = _make_ooc_spell()
        effects = build_persisted_effects(
            spell=spell, caster_user_id="u1", target_user_id="u1",
            variant_key=None, game_time_seconds=0,
        )
        decl = effects[0]["metadata"]["declarative_effect"]
        self.assertEqual(decl["type"], "attack_disadvantage_against_target")

    def test_build_persisted_effects_has_declarative_save_effect(self):
        spell = _make_ooc_spell()
        effects = build_persisted_effects(
            spell=spell, caster_user_id="u1", target_user_id="u1",
            variant_key=None, game_time_seconds=0,
        )
        decl = effects[0]["metadata"]["declarative_save_effect"]
        self.assertEqual(decl["type"], "saving_throw_advantage_against_creature_types")

    def test_build_persisted_effects_condition_immunity_true(self):
        spell = _make_ooc_spell()
        effects = build_persisted_effects(
            spell=spell, caster_user_id="u1", target_user_id="u1",
            variant_key=None, game_time_seconds=0,
        )
        self.assertTrue(effects[0]["metadata"]["condition_immunity"])

    def test_build_persisted_effects_protected_creature_types(self):
        spell = _make_ooc_spell()
        effects = build_persisted_effects(
            spell=spell, caster_user_id="u1", target_user_id="u1",
            variant_key=None, game_time_seconds=0,
        )
        types = effects[0]["metadata"]["protected_creature_types"]
        for t in ["aberration", "celestial", "elemental", "fey", "fiend", "undead"]:
            self.assertIn(t, types)

    def test_build_persisted_effects_expires_at_600(self):
        spell = _make_ooc_spell()
        effects = build_persisted_effects(
            spell=spell, caster_user_id="u1", target_user_id="u1",
            variant_key=None, game_time_seconds=1000,
        )
        self.assertEqual(effects[0]["expires_at_game_time_seconds"], 1600)

    def test_ooc_eligibility_self(self):
        spell = _make_ooc_spell()
        state_json: dict = {"spellcasting": {"slots": {"1": {"used": 0, "max": 2}}}}
        ok, _ = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json=state_json,
            slot_level=1,
            variant_key=None,
            out_of_combat_target="self_or_ally",
            target_user_id="u1",
            caster_user_id="u1",
            target_state_json=state_json,
        )
        self.assertTrue(ok)

    def test_ooc_eligibility_ally(self):
        spell = _make_ooc_spell()
        caster_state: dict = {"spellcasting": {"slots": {"1": {"used": 0, "max": 2}}}}
        ally_state: dict = {}
        ok, _ = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json=caster_state,
            slot_level=1,
            variant_key=None,
            out_of_combat_target="self_or_ally",
            target_user_id="u2",
            caster_user_id="u1",
            target_state_json=ally_state,
        )
        self.assertTrue(ok)


# ---------------------------------------------------------------------------
# 9. Spell context
# ---------------------------------------------------------------------------

class ProtectionFromEvilAndGoodSpellContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.combat_service.spells.spell_context_resolve import SpellContextResolveMixin
        cls.meta = SpellContextResolveMixin.UTILITY_SPELL_CONTEXT_META[
            "protection_from_evil_and_good"
        ]

    def test_type_defense_buff(self):
        self.assertEqual(self.meta["type"], "defense_buff")

    def test_subtype(self):
        self.assertEqual(self.meta["subtype"], "protection_from_evil_and_good")

    def test_requires_concentration_true(self):
        self.assertTrue(self.meta["requiresConcentration"])

    def test_duration_seconds(self):
        self.assertEqual(self.meta["durationSeconds"], 600)

    def test_protected_creature_types_all_six(self):
        for t in ["aberration", "celestial", "elemental", "fey", "fiend", "undead"]:
            self.assertIn(t, self.meta["protectedCreatureTypes"])

    def test_condition_immunity_true(self):
        self.assertTrue(self.meta["conditionImmunity"])

    def test_immune_conditions_charmed(self):
        self.assertIn("charmed", self.meta["immuneConditions"])

    def test_immune_conditions_frightened(self):
        self.assertIn("frightened", self.meta["immuneConditions"])

    def test_immune_conditions_possessed(self):
        self.assertIn("possessed", self.meta["immuneConditions"])

    def test_saving_throw_advantage_deferred(self):
        self.assertFalse(self.meta["savingThrowAdvantageDeferred"])

    def test_saving_throw_advantage_not_in_v1(self):
        self.assertTrue(self.meta["savingThrowAdvantageAgainstCreatureTypes"])

    def test_possessed_supported(self):
        self.assertTrue(self.meta["possessedConditionSupported"])

    def test_ooc_castable(self):
        self.assertTrue(self.meta["outOfCombatCastable"])

    def test_ooc_target(self):
        self.assertEqual(self.meta["outOfCombatTarget"], "self_or_ally")


# ---------------------------------------------------------------------------
# 10. Condition immunity: handler integration
# ---------------------------------------------------------------------------

def _make_attacker_participant(creature_type: str | None = None) -> dict:
    return {
        "id": "att1",
        "ref_id": "att-ref",
        "kind": "session_entity",
        "display_name": "Attacker",
        "team": "enemies",
        "creature_type": creature_type,
        "active_effects": [],
    }


def _make_target_participant_for_handler(protected: bool = True) -> dict:
    target: dict = {
        "id": "tgt1",
        "ref_id": "tgt-ref",
        "kind": "session_entity",
        "display_name": "Hero",
        "team": "players",
        "active_effects": [],
    }
    if protected:
        target["active_effects"] = [_make_protection_effect()]
    return target


def _spell_ctx(key: str = "charm_person", name: str = "Charm Person") -> dict:
    return {
        "spell_name": name,
        "spell_canonical_key": key,
        "save_ability": "wisdom",
        "save_dc": 14,
        "save_success_outcome": "none",
        "concentration": False,
    }


class ConditionImmunityHandlerTests(unittest.IsolatedAsyncioTestCase):
    # --- Animal Friendship ---

    async def test_animal_friendship_blocked_fiend(self):
        attacker = _make_attacker_participant("fiend")
        target = _make_target_participant_for_handler(protected=True)
        result = await CombatService._cast_animal_friendship_automation(
            MagicMock(),
            "sess",
            attacker=attacker,
            attacker_model=MagicMock(),
            actor_user_id="u1",
            is_gm=False,
            req=MagicMock(),
            state=MagicMock(),
            spell_context=_spell_ctx("animal_friendship", "Amizade com Animais"),
            target_participant=target,
        )
        self.assertTrue(result.get("immune"))
        self.assertEqual(result["immune_reason"], "protection_from_evil_and_good")
        charmed = [e for e in target["active_effects"] if e.get("condition_type") == "charmed"]
        self.assertEqual(charmed, [])

    async def test_animal_friendship_blocked_undead(self):
        attacker = _make_attacker_participant("undead")
        target = _make_target_participant_for_handler(protected=True)
        result = await CombatService._cast_animal_friendship_automation(
            MagicMock(),
            "sess",
            attacker=attacker,
            attacker_model=MagicMock(),
            actor_user_id="u1",
            is_gm=False,
            req=MagicMock(),
            state=MagicMock(),
            spell_context=_spell_ctx("animal_friendship", "Amizade com Animais"),
            target_participant=target,
        )
        self.assertTrue(result.get("immune"))
        charmed = [e for e in target["active_effects"] if e.get("condition_type") == "charmed"]
        self.assertEqual(charmed, [])

    async def test_animal_friendship_not_blocked_humanoid(self):
        from app.schemas.roll import RollResult
        from datetime import datetime, timezone

        attacker = _make_attacker_participant("humanoid")
        target = _make_target_participant_for_handler(protected=True)
        roll_fail = RollResult(
            event_id="r1", roll_type="save", actor_kind="session_entity",
            actor_ref_id="tgt-ref", actor_display_name="Hero",
            rolls=[2], selected_roll=2, advantage_mode="normal",
            modifier_used=0, override_used=False, formula="1d20",
            total=2, ability="wisdom", dc=14, success=False,
            timestamp=datetime.now(timezone.utc),
        )
        with (
            patch("app.services.combat_service.spell_automation.resolve_saving_throw", return_value=roll_fail),
            patch.object(CombatService, "_build_roll_actor_stats_for_save", return_value=MagicMock()),
            patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=0),
            patch.object(CombatService, "_append_effect_to_participant",
                         side_effect=lambda p, e: p.setdefault("active_effects", []).append(e)),
            patch("app.services.combat_service.spell_automation.flag_modified"),
        ):
            result = await CombatService._cast_animal_friendship_automation(
                MagicMock(), "sess",
                attacker=attacker, attacker_model=MagicMock(), actor_user_id="u1",
                is_gm=False, req=MagicMock(), state=MagicMock(),
                spell_context=_spell_ctx("animal_friendship", "Amizade com Animais"),
                target_participant=target,
            )
        self.assertFalse(result.get("immune"))
        charmed = [e for e in target["active_effects"] if e.get("condition_type") == "charmed"]
        self.assertEqual(len(charmed), 1)

    async def test_animal_friendship_not_blocked_no_protection(self):
        from app.schemas.roll import RollResult
        from datetime import datetime, timezone

        attacker = _make_attacker_participant("fiend")
        target = _make_target_participant_for_handler(protected=False)
        roll_fail = RollResult(
            event_id="r1", roll_type="save", actor_kind="session_entity",
            actor_ref_id="tgt-ref", actor_display_name="Hero",
            rolls=[2], selected_roll=2, advantage_mode="normal",
            modifier_used=0, override_used=False, formula="1d20",
            total=2, ability="wisdom", dc=14, success=False,
            timestamp=datetime.now(timezone.utc),
        )
        with (
            patch("app.services.combat_service.spell_automation.resolve_saving_throw", return_value=roll_fail),
            patch.object(CombatService, "_build_roll_actor_stats_for_save", return_value=MagicMock()),
            patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=0),
            patch.object(CombatService, "_append_effect_to_participant",
                         side_effect=lambda p, e: p.setdefault("active_effects", []).append(e)),
            patch("app.services.combat_service.spell_automation.flag_modified"),
        ):
            result = await CombatService._cast_animal_friendship_automation(
                MagicMock(), "sess",
                attacker=attacker, attacker_model=MagicMock(), actor_user_id="u1",
                is_gm=False, req=MagicMock(), state=MagicMock(),
                spell_context=_spell_ctx("animal_friendship", "Amizade com Animais"),
                target_participant=target,
            )
        self.assertFalse(result.get("immune"))

    # --- Charm Person ---

    async def test_charm_person_blocked_fiend(self):
        attacker = _make_attacker_participant("fiend")
        target = _make_target_participant_for_handler(protected=True)
        result = await CombatService._cast_charm_person_automation(
            MagicMock(), "sess",
            attacker=attacker, attacker_model=MagicMock(), actor_user_id="u1",
            is_gm=False, req=MagicMock(), state=MagicMock(),
            spell_context=_spell_ctx(),
            target_participant=target,
        )
        self.assertTrue(result.get("immune"))
        self.assertEqual(result["immune_reason"], "protection_from_evil_and_good")
        charmed = [e for e in target["active_effects"] if e.get("condition_type") == "charmed"]
        self.assertEqual(charmed, [])

    async def test_charm_person_not_blocked_humanoid(self):
        from app.schemas.roll import RollResult
        from datetime import datetime, timezone

        attacker = _make_attacker_participant("humanoid")
        target = _make_target_participant_for_handler(protected=True)
        roll_pass = RollResult(
            event_id="r1", roll_type="save", actor_kind="session_entity",
            actor_ref_id="tgt-ref", actor_display_name="Hero",
            rolls=[18], selected_roll=18, advantage_mode="normal",
            modifier_used=0, override_used=False, formula="1d20",
            total=18, ability="wisdom", dc=14, success=True,
            timestamp=datetime.now(timezone.utc),
        )
        with (
            patch("app.services.combat_service.spell_automation.resolve_saving_throw", return_value=roll_pass),
            patch.object(CombatService, "_build_roll_actor_stats_for_save", return_value=MagicMock()),
            patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=0),
        ):
            result = await CombatService._cast_charm_person_automation(
                MagicMock(), "sess",
                attacker=attacker, attacker_model=MagicMock(), actor_user_id="u1",
                is_gm=False, req=MagicMock(), state=MagicMock(),
                spell_context=_spell_ctx(),
                target_participant=target,
            )
        self.assertFalse(result.get("immune"))

    async def test_charm_person_not_blocked_no_protection(self):
        from app.schemas.roll import RollResult
        from datetime import datetime, timezone

        attacker = _make_attacker_participant("fiend")
        target = _make_target_participant_for_handler(protected=False)
        roll_pass = RollResult(
            event_id="r1", roll_type="save", actor_kind="session_entity",
            actor_ref_id="tgt-ref", actor_display_name="Hero",
            rolls=[18], selected_roll=18, advantage_mode="normal",
            modifier_used=0, override_used=False, formula="1d20",
            total=18, ability="wisdom", dc=14, success=True,
            timestamp=datetime.now(timezone.utc),
        )
        with (
            patch("app.services.combat_service.spell_automation.resolve_saving_throw", return_value=roll_pass),
            patch.object(CombatService, "_build_roll_actor_stats_for_save", return_value=MagicMock()),
            patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=0),
        ):
            result = await CombatService._cast_charm_person_automation(
                MagicMock(), "sess",
                attacker=attacker, attacker_model=MagicMock(), actor_user_id="u1",
                is_gm=False, req=MagicMock(), state=MagicMock(),
                spell_context=_spell_ctx(),
                target_participant=target,
            )
        self.assertFalse(result.get("immune"))

    # --- Declarative effects apply_condition path ---

    def _make_minimal_state(self, attacker: dict, target: dict) -> CombatState:
        return CombatState(
            id="c1", session_id="s1", phase=CombatPhase.active,
            round=1, current_turn_index=0,
            participants=[attacker, target], use_map=False,
        )

    def _make_apply_condition_effect(self, condition: str) -> "SpellDeclarativeEffect":
        from app.schemas.base_spell_effects import ApplyConditionParams, SpellDeclarativeEffect as SDE
        return SDE(type="apply_condition", target="selected_target",
                   params=ApplyConditionParams(condition=condition))

    def test_declarative_charmed_blocked_fiend(self):
        attacker = _make_attacker_participant("fiend")
        target = _make_target_participant_for_handler(protected=True)
        state = self._make_minimal_state(attacker, target)
        effect = self._make_apply_condition_effect("charmed")
        created = CombatService._apply_single_declarative_effect(
            state=state, attacker=attacker, target_participant=target,
            spell_context=_spell_ctx(), effect=effect,
            effect_group_id="grp1", on_end_effects=[],
        )
        self.assertEqual(created, [])
        charmed = [e for e in target["active_effects"] if e.get("condition_type") == "charmed"]
        self.assertEqual(charmed, [])

    def test_declarative_charmed_not_blocked_humanoid(self):
        attacker = _make_attacker_participant("humanoid")
        target = _make_target_participant_for_handler(protected=True)
        state = self._make_minimal_state(attacker, target)
        effect = self._make_apply_condition_effect("charmed")
        with patch.object(CombatService, "_append_effect_to_participant",
                          side_effect=lambda p, e: p.setdefault("active_effects", []).append(e)):
            created = CombatService._apply_single_declarative_effect(
                state=state, attacker=attacker, target_participant=target,
                spell_context=_spell_ctx(), effect=effect,
                effect_group_id="grp1", on_end_effects=[],
            )
        self.assertEqual(len(created), 1)

    def test_declarative_frightened_blocked_undead(self):
        attacker = _make_attacker_participant("undead")
        target = _make_target_participant_for_handler(protected=True)
        state = self._make_minimal_state(attacker, target)
        effect = self._make_apply_condition_effect("frightened")
        created = CombatService._apply_single_declarative_effect(
            state=state, attacker=attacker, target_participant=target,
            spell_context=_spell_ctx(), effect=effect,
            effect_group_id="grp1", on_end_effects=[],
        )
        self.assertEqual(created, [])

    def test_declarative_charmed_no_protection(self):
        attacker = _make_attacker_participant("fiend")
        target = _make_target_participant_for_handler(protected=False)
        state = self._make_minimal_state(attacker, target)
        effect = self._make_apply_condition_effect("charmed")
        with patch.object(CombatService, "_append_effect_to_participant",
                          side_effect=lambda p, e: p.setdefault("active_effects", []).append(e)):
            created = CombatService._apply_single_declarative_effect(
                state=state, attacker=attacker, target_participant=target,
                spell_context=_spell_ctx(), effect=effect,
                effect_group_id="grp1", on_end_effects=[],
            )
        self.assertEqual(len(created), 1)
