from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_predicates import (
    COMMAND_VARIANTS,
    COMMAND_VARIANT_LABELS,
    is_action_blocked,
    is_movement_blocked,
    is_undead_participant,
    target_cannot_understand_command,
)
from app.services.combat import CombatService as _CombatServiceForGrovel
from app.services.combat_service.spell_automation import (
    CombatSpellAutomationMixin,
    _build_command_effect_metadata,
)
from app.services.combat_service.exceptions import CombatServiceError
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


SEED_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
)


def _first(value):
    mock = MagicMock()
    mock.first.return_value = value
    return mock


def _make_state(caster_id: str = "p1", target_id: str = "p2", **target_extra) -> CombatState:
    target = {
        "id": target_id,
        "ref_id": "u2",
        "kind": "npc",
        "display_name": "Goblin",
        "active_effects": [],
    }
    target.update(target_extra)
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
            target,
        ],
    )


def _make_db() -> MagicMock:
    db = MagicMock()
    sj = SimpleNamespace(state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 2}}}})
    db.exec.return_value = _first(sj)
    return db


def _spell_context(save_dc: int = 14, slot_level: int = 1) -> dict:
    return {
        "spell_name": "Comando",
        "spell_key": "command",
        "spell_canonical_key": "command",
        "slot_level": slot_level,
        "save_ability": "wisdom",
        "save_dc": save_dc,
        "max_targets": slot_level,
    }


def _mock_save_result(success: bool):
    r = MagicMock()
    r.success = success
    r.total = 12 if not success else 18
    return r


async def _cast(
    variant_key: str = "halt",
    save_success: bool = False,
    target_extra: dict | None = None,
    slot_level: int = 1,
) -> tuple[dict, dict]:
    db = _make_db()
    state = _make_state(**(target_extra or {}))
    caster = next(p for p in state.participants if p["id"] == "p1")
    target = next(p for p in state.participants if p["id"] == "p2")

    req = SimpleNamespace(variant_key=variant_key, roll_source="server", override_resource_limit=False)
    sc = _spell_context(slot_level=slot_level)

    save_result = _mock_save_result(save_success)

    with (
        patch("app.services.combat_service.spell_automation.flag_modified"),
        patch(
            "app.services.combat_service.spell_automation.resolve_saving_throw",
            return_value=save_result,
        ),
        patch.object(
            CombatService,
            "_build_roll_actor_stats_for_save",
            return_value=MagicMock(),
        ),
    ):
        result = await CombatService._cast_command_automation(
            db=db,
            session_id="sess1",
            attacker=caster,
            attacker_model=MagicMock(),
            actor_user_id="u1",
            is_gm=False,
            req=req,
            state=state,
            spell_context=sc,
            target_participant=target,
        )
    return result, target


# ---------------------------------------------------------------------------
# 1. Seed
# ---------------------------------------------------------------------------

class CommandSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SEED_PATH, encoding="utf-8") as f:
            data = json.load(f)
        cls.entry = next(
            (s for s in data.get("spells", []) if s.get("canonicalKey") == "command"), None
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "command not found in base_spells.seed.json")

    def test_level(self):
        self.assertEqual(self.entry["level"], 1)

    def test_school(self):
        self.assertEqual(self.entry["school"], "enchantment")

    def test_classes_cleric(self):
        self.assertIn("Cleric", self.entry["classesJson"])

    def test_classes_paladin(self):
        self.assertIn("Paladin", self.entry["classesJson"])

    def test_range_meters(self):
        self.assertEqual(self.entry["rangeMeters"], 18)

    def test_duration_seconds(self):
        self.assertEqual(self.entry["durationSeconds"], 6)

    def test_not_concentration(self):
        self.assertFalse(self.entry["concentration"])

    def test_not_ritual(self):
        self.assertFalse(self.entry["ritual"])

    def test_resolution_type(self):
        self.assertEqual(self.entry["resolutionType"], "save")

    def test_saving_throw_ability(self):
        self.assertEqual(self.entry["savingThrowAbility"], "wisdom")

    def test_selection_type(self):
        self.assertEqual(self.entry["selectionType"], "single_target")

    def test_effect_timing(self):
        self.assertEqual(self.entry["effectTiming"], "persistent")

    def test_max_targets(self):
        self.assertEqual(self.entry["maxTargets"], 1)

    def test_upcast_mode(self):
        self.assertEqual(self.entry["upcast"]["mode"], "additional_targets")

    def test_upcast_per_level(self):
        self.assertEqual(self.entry["upcast"]["perLevel"], 1)

    def test_no_damage_dice(self):
        self.assertIsNone(self.entry.get("damageDice"))

    def test_no_cantrip_scaling(self):
        self.assertIsNone(self.entry.get("cantripScaling"))

    def test_ooc_castable_absent_or_false(self):
        self.assertFalse(self.entry.get("outOfCombatCastable", False))


# ---------------------------------------------------------------------------
# 2. Targeting semantics
# ---------------------------------------------------------------------------

class CommandTargetingSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sem = resolve_spell_targeting_semantics({"canonicalKey": "command"})

    def test_selection_type(self):
        self.assertEqual(self.sem.selection_type, "single_target")

    def test_origin_type(self):
        self.assertEqual(self.sem.origin_type, "caster")

    def test_target_anchor(self):
        self.assertEqual(self.sem.target_anchor, "target")

    def test_attack_type(self):
        self.assertEqual(self.sem.attack_type, "none")

    def test_range_kind(self):
        self.assertEqual(self.sem.range_kind, "distance")

    def test_effect_timing(self):
        self.assertEqual(self.sem.effect_timing, "persistent")


# ---------------------------------------------------------------------------
# 3. Registry
# ---------------------------------------------------------------------------

class CommandRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY.get("command")

    def test_registry_entry_exists(self):
        self.assertIsNotNone(self.spec)

    def test_default_mode(self):
        self.assertEqual(self.spec.default_mode, "save")

    def test_requires_effect_payload(self):
        self.assertFalse(self.spec.requires_effect_payload)

    def test_handler_name(self):
        self.assertEqual(self.spec.handler_name, "_cast_command_automation")


# ---------------------------------------------------------------------------
# 4. Variants
# ---------------------------------------------------------------------------

class CommandVariantsTests(unittest.TestCase):
    def test_contains_approach(self):
        self.assertIn("approach", COMMAND_VARIANTS)

    def test_contains_drop(self):
        self.assertIn("drop", COMMAND_VARIANTS)

    def test_contains_flee(self):
        self.assertIn("flee", COMMAND_VARIANTS)

    def test_contains_grovel(self):
        self.assertIn("grovel", COMMAND_VARIANTS)

    def test_contains_halt(self):
        self.assertIn("halt", COMMAND_VARIANTS)

    def test_excludes_stunned(self):
        self.assertNotIn("stunned", COMMAND_VARIANTS)

    def test_excludes_die(self):
        self.assertNotIn("die", COMMAND_VARIANTS)

    def test_grovel_label_singular(self):
        self.assertEqual(COMMAND_VARIANT_LABELS["grovel"], "Prostre-se")

    def test_halt_label(self):
        self.assertEqual(COMMAND_VARIANT_LABELS["halt"], "Pare")


# ---------------------------------------------------------------------------
# 5. Automation handler
# ---------------------------------------------------------------------------

class CommandAutomationTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_success_no_effect(self):
        _, target = await _cast(variant_key="halt", save_success=True)
        spell_effects = [e for e in target["active_effects"] if e.get("kind") == "spell_effect"]
        self.assertEqual(len(spell_effects), 0)

    async def test_save_failure_applies_effect(self):
        _, target = await _cast(variant_key="halt", save_success=False)
        spell_effects = [e for e in target["active_effects"] if e.get("kind") == "spell_effect"]
        self.assertEqual(len(spell_effects), 1)

    async def test_effect_has_command_word(self):
        _, target = await _cast(variant_key="grovel", save_success=False)
        effect = next(e for e in target["active_effects"] if e.get("kind") == "spell_effect")
        self.assertEqual(effect["metadata"]["command_word"], "grovel")

    async def test_action_kind_saving_throw(self):
        result, _ = await _cast(variant_key="halt", save_success=False)
        self.assertEqual(result.get("action_kind"), "saving_throw")

    async def test_result_is_saved_true_on_success(self):
        result, _ = await _cast(variant_key="halt", save_success=True)
        self.assertTrue(result["is_saved"])

    async def test_result_is_saved_false_on_failure(self):
        result, _ = await _cast(variant_key="halt", save_success=False)
        self.assertFalse(result["is_saved"])

    async def test_no_damage_no_healing(self):
        result, _ = await _cast(variant_key="halt", save_success=False)
        self.assertFalse(result.get("damage"))
        self.assertFalse(result.get("healing"))

    async def test_no_concentration(self):
        _, target = await _cast(variant_key="halt", save_success=False)
        effect = next(e for e in target["active_effects"] if e.get("kind") == "spell_effect")
        self.assertFalse(effect["metadata"].get("concentration"))

    async def test_undead_is_immune(self):
        result, _ = await _cast(
            variant_key="halt",
            target_extra={"creature_type": "undead"},
        )
        self.assertTrue(result.get("immune"))
        self.assertEqual(result.get("immune_reason"), "undead")

    async def test_undead_result_no_effect_on_participant(self):
        _, target = await _cast(
            variant_key="halt",
            target_extra={"creature_type": "undead"},
        )
        spell_effects = [e for e in target["active_effects"] if e.get("kind") == "spell_effect"]
        self.assertEqual(len(spell_effects), 0)

    async def test_cannot_understand_is_immune(self):
        result, _ = await _cast(
            variant_key="halt",
            target_extra={"metadata": {"cannot_understand_command": True}},
        )
        self.assertTrue(result.get("immune"))
        self.assertEqual(result.get("immune_reason"), "cannot_understand")

    async def test_language_check_no_metadata_assumes_understands(self):
        # Target has no language metadata → assumes understands → no immune
        result, _ = await _cast(variant_key="halt", save_success=True)
        self.assertFalse(result.get("immune", False))

    async def test_missing_target_raises_400(self):
        db = _make_db()
        state = _make_state()
        caster = next(p for p in state.participants if p["id"] == "p1")
        req = SimpleNamespace(variant_key="halt", roll_source="server", override_resource_limit=False)
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_command_automation(
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

    async def test_missing_variant_key_raises_400(self):
        db = _make_db()
        state = _make_state()
        caster = state.participants[0]
        target = state.participants[1]
        req = SimpleNamespace(variant_key=None, roll_source="server", override_resource_limit=False)
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_command_automation(
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

    async def test_invalid_variant_key_raises_400(self):
        db = _make_db()
        state = _make_state()
        caster = state.participants[0]
        target = state.participants[1]
        req = SimpleNamespace(variant_key="die", roll_source="server", override_resource_limit=False)
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_command_automation(
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


# ---------------------------------------------------------------------------
# 6. Effect metadata per variant
# ---------------------------------------------------------------------------

class CommandEffectTests(unittest.TestCase):
    def _meta(self, variant: str) -> dict:
        caster = {"id": "c1"}
        target = {"id": "t1"}
        label = COMMAND_VARIANT_LABELS[variant]
        return _build_command_effect_metadata(variant, label, caster, target)

    def test_halt_action_blocked_true(self):
        self.assertTrue(self._meta("halt").get("action_blocked"))

    def test_halt_movement_blocked_true(self):
        self.assertTrue(self._meta("halt").get("movement_blocked"))

    def test_grovel_apply_prone_on_turn_start_true(self):
        self.assertTrue(self._meta("grovel").get("apply_prone_on_turn_start"))

    def test_grovel_action_blocked_true(self):
        self.assertTrue(self._meta("grovel").get("action_blocked"))

    def test_grovel_movement_blocked_true(self):
        self.assertTrue(self._meta("grovel").get("movement_blocked"))

    def test_drop_must_drop_held_items_true(self):
        self.assertTrue(self._meta("drop").get("must_drop_held_items"))

    def test_flee_forced_movement_intent_away(self):
        self.assertEqual(self._meta("flee")["forced_movement_intent"], "away_from_caster")

    def test_flee_anchor_is_caster_id(self):
        self.assertEqual(self._meta("flee")["forced_movement_anchor_participant_id"], "c1")

    def test_approach_forced_movement_intent_toward(self):
        self.assertEqual(self._meta("approach")["forced_movement_intent"], "toward_caster")

    def test_all_commands_have_commanded_true(self):
        for variant in COMMAND_VARIANTS:
            with self.subTest(variant=variant):
                self.assertTrue(self._meta(variant).get("commanded"))

    def test_all_commands_source_spell_key_command(self):
        for variant in COMMAND_VARIANTS:
            with self.subTest(variant=variant):
                self.assertEqual(self._meta(variant)["source_spell_key"], "command")

    def test_all_commands_no_concentration(self):
        for variant in COMMAND_VARIANTS:
            with self.subTest(variant=variant):
                self.assertFalse(self._meta(variant).get("concentration"))

    def test_flee_does_not_have_movement_blocked(self):
        self.assertNotIn("movement_blocked", self._meta("flee"))

    def test_approach_does_not_have_movement_blocked(self):
        self.assertNotIn("movement_blocked", self._meta("approach"))


# ---------------------------------------------------------------------------
# 7. Predicate tests
# ---------------------------------------------------------------------------

class CommandPredicateTests(unittest.TestCase):
    def _participant_with_effect(self, metadata: dict) -> dict:
        return {
            "id": "t1",
            "active_effects": [
                {
                    "id": "eff-1",
                    "kind": "spell_effect",
                    "metadata": metadata,
                }
            ],
        }

    def test_is_action_blocked_with_halt_effect(self):
        p = self._participant_with_effect({"action_blocked": True, "source_spell_key": "command"})
        self.assertTrue(is_action_blocked(p))

    def test_is_movement_blocked_with_halt_effect(self):
        p = self._participant_with_effect({"movement_blocked": True, "source_spell_key": "command"})
        self.assertTrue(is_movement_blocked(p))

    def test_is_action_blocked_without_command_effect(self):
        p = {"id": "t1", "active_effects": []}
        self.assertFalse(is_action_blocked(p))

    def test_is_movement_blocked_without_command_effect(self):
        p = {"id": "t1", "active_effects": []}
        self.assertFalse(is_movement_blocked(p))

    def test_halt_effect_does_not_add_condition(self):
        p = self._participant_with_effect({"action_blocked": True, "movement_blocked": True})
        effect = p["active_effects"][0]
        self.assertEqual(effect["kind"], "spell_effect")
        self.assertNotEqual(effect["kind"], "condition")

    def test_flee_does_not_block_movement_via_predicate(self):
        # flee has must_use_movement but NOT movement_blocked
        meta = _build_command_effect_metadata("flee", "Fuja", {"id": "c1"}, {"id": "t1"})
        p = {"id": "t1", "active_effects": [{"id": "eff-1", "kind": "spell_effect", "metadata": meta}]}
        self.assertFalse(is_movement_blocked(p))

    def test_is_undead_participant_true_on_creature_type(self):
        p = {"id": "t1", "creature_type": "undead"}
        self.assertTrue(is_undead_participant(p))

    def test_is_undead_participant_false_on_humanoid(self):
        p = {"id": "t1", "creature_type": "humanoid"}
        self.assertFalse(is_undead_participant(p))

    def test_is_undead_participant_metadata_fallback(self):
        p = {"id": "t1", "metadata": {"creature_type": "undead"}}
        self.assertTrue(is_undead_participant(p))

    def test_target_cannot_understand_command_explicit_flag(self):
        caster = {"id": "c1"}
        target = {"id": "t1", "metadata": {"cannot_understand_command": True}}
        self.assertTrue(target_cannot_understand_command(caster, target))

    def test_target_understands_languages_false(self):
        caster = {"id": "c1"}
        target = {"id": "t1", "metadata": {"understands_languages": False}}
        self.assertTrue(target_cannot_understand_command(caster, target))

    def test_target_no_metadata_assumes_understands(self):
        caster = {"id": "c1"}
        target = {"id": "t1"}
        self.assertFalse(target_cannot_understand_command(caster, target))

    def test_language_intersection_mismatch(self):
        caster = {"id": "c1", "languages": ["common"]}
        target = {"id": "t1", "languages": ["goblin"]}
        self.assertTrue(target_cannot_understand_command(caster, target))

    def test_language_intersection_match(self):
        caster = {"id": "c1", "languages": ["common"]}
        target = {"id": "t1", "languages": ["common", "goblin"]}
        self.assertFalse(target_cannot_understand_command(caster, target))


# ---------------------------------------------------------------------------
# 8. Grovel hook
# ---------------------------------------------------------------------------

class CommandGravelTests(unittest.TestCase):
    def _participant_with_grovel(self, already_prone: bool = False) -> dict:
        effects: list[dict] = [
            {
                "id": "eff-g",
                "kind": "spell_effect",
                "metadata": {
                    "source_spell_key": "command",
                    "command_word": "grovel",
                    "apply_prone_on_turn_start": True,
                },
            }
        ]
        if already_prone:
            effects.append({
                "id": "eff-prone",
                "kind": "condition",
                "condition_type": "prone",
                "metadata": {},
            })
        return {"id": "t1", "active_effects": effects}

    def _state_with(self, participant: dict) -> CombatState:
        return CombatState(
            id="c1",
            session_id="sess1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[participant],
        )

    def test_grovel_effect_has_apply_prone_on_turn_start(self):
        meta = _build_command_effect_metadata("grovel", "Prostre-se", {"id": "c1"}, {"id": "t1"})
        self.assertTrue(meta.get("apply_prone_on_turn_start"))

    def test_grovel_hook_applies_prone_on_turn_start(self):
        p = self._participant_with_grovel(already_prone=False)
        state = self._state_with(p)
        with patch("app.services.combat_service.lifecycle_turns.flag_modified"):
            _CombatServiceForGrovel._apply_command_grovel_prone(state, "t1")
        conditions = [e for e in p["active_effects"] if e.get("kind") == "condition"]
        prone_conditions = [e for e in conditions if e.get("condition_type") == "prone"]
        self.assertEqual(len(prone_conditions), 1)

    def test_grovel_hook_idempotent(self):
        p = self._participant_with_grovel(already_prone=True)
        state = self._state_with(p)
        with patch("app.services.combat_service.lifecycle_turns.flag_modified"):
            _CombatServiceForGrovel._apply_command_grovel_prone(state, "t1")
        conditions = [e for e in p["active_effects"] if e.get("kind") == "condition" and e.get("condition_type") == "prone"]
        self.assertEqual(len(conditions), 1)

    def test_halt_hook_does_not_apply_prone(self):
        p = {
            "id": "t1",
            "active_effects": [
                {
                    "id": "eff-h",
                    "kind": "spell_effect",
                    "metadata": {
                        "source_spell_key": "command",
                        "command_word": "halt",
                        "action_blocked": True,
                        "movement_blocked": True,
                    },
                }
            ],
        }
        state = self._state_with(p)
        with patch("app.services.combat_service.lifecycle_turns.flag_modified"):
            _CombatServiceForGrovel._apply_command_grovel_prone(state, "t1")
        conditions = [e for e in p["active_effects"] if e.get("kind") == "condition"]
        self.assertEqual(len(conditions), 0)


# ---------------------------------------------------------------------------
# 9. Upcast
# ---------------------------------------------------------------------------

class CommandUpcastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SEED_PATH, encoding="utf-8") as f:
            data = json.load(f)
        cls.entry = next(
            (s for s in data.get("spells", []) if s.get("canonicalKey") == "command"), None
        )

    def test_seed_has_max_targets_1(self):
        self.assertEqual(self.entry["maxTargets"], 1)

    def test_seed_upcast_mode_additional_targets(self):
        self.assertEqual(self.entry["upcast"]["mode"], "additional_targets")

    def test_seed_upcast_per_level_1(self):
        self.assertEqual(self.entry["upcast"]["perLevel"], 1)


# ---------------------------------------------------------------------------
# 10. Spell context
# ---------------------------------------------------------------------------

class CommandSpellContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.combat_service.spells.spell_context_resolve import SpellContextResolveMixin
        cls.meta = SpellContextResolveMixin._COMMAND_UTILITY_META

    def test_type_control(self):
        self.assertEqual(self.meta["type"], "control")

    def test_subtype_command(self):
        self.assertEqual(self.meta["subtype"], "command")

    def test_save_ability_wisdom(self):
        self.assertEqual(self.meta["saveAbility"], "wisdom")

    def test_requires_variant_key_true(self):
        self.assertTrue(self.meta["requiresVariantKey"])

    def test_allowed_commands_list(self):
        for cmd in ["approach", "drop", "flee", "grovel", "halt"]:
            self.assertIn(cmd, self.meta["allowedCommands"])

    def test_invalid_against_undead_true(self):
        self.assertTrue(self.meta["invalidAgainstUndead"])

    def test_requires_shared_language_true(self):
        self.assertTrue(self.meta["requiresSharedLanguage"])

    def test_supports_upcast_additional_targets(self):
        self.assertTrue(self.meta["supportsUpcastAdditionalTargets"])

    def test_ooc_castable_false(self):
        self.assertFalse(self.meta["outOfCombatCastable"])
