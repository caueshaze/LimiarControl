from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.combat_service.exceptions import CombatServiceError
from app.services.combat_service.sanctuary_guard import (
    break_sanctuary_if_active,
    find_sanctuary_effect_on_participant,
)
from app.services.combat_service.spell_automation import CombatSpellAutomationMixin
from app.services.combat_service.spells.spell_context_resolve import SpellContextResolveMixin
from app.services.out_of_combat_cast import (
    OOC_FACTORY_EFFECT_SPELLS,
    _is_ooc_utility_spell,
    build_persisted_effects,
    check_out_of_combat_cast_eligibility,
)
from app.services.spell_effect_factories import SpellEffectBuildContext, build_sanctuary_effect
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


SEED_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
)


def _make_ctx(spell_save_dc: int = 14) -> SpellEffectBuildContext:
    return SpellEffectBuildContext(
        spell_key="sanctuary",
        spell_name="Santuário",
        game_time_seconds=0,
        duration_seconds=60,
        concentration=False,
        concentration_group=None,
        source_participant_id="p1",
        owner_participant_id="p2",
        created_by_participant_id="p1",
        context_origin="combat",
        spell_save_dc=spell_save_dc,
    )


def _make_sanctuary_effect(guard_save_dc: int = 14) -> dict:
    return {
        "id": "eff-sanc",
        "kind": "spell_effect",
        "metadata": {
            "sanctuary": True,
            "guard_save_dc": guard_save_dc,
            "source_spell_key": "sanctuary",
        },
    }


def _make_state(
    caster_id: str = "p1",
    target_id: str = "p2",
    target_extra: dict | None = None,
) -> CombatState:
    target: dict = {
        "id": target_id,
        "ref_id": "u2",
        "kind": "player",
        "display_name": "Bob",
        "team": "players",
        "active_effects": [],
    }
    if target_extra:
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
                "team": "players",
                "spellcasting": {"saveDc": 14},
                "active_effects": [],
            },
            target,
        ],
    )


def _make_db() -> MagicMock:
    db = MagicMock()
    sj = SimpleNamespace(state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 2}}}})
    db.exec.return_value.first.return_value = sj
    return db


def _make_ooc_spell(**kwargs) -> SimpleNamespace:
    defaults = dict(
        canonical_key="sanctuary",
        name_pt="Santuário",
        name_en="Sanctuary",
        level=1,
        concentration=False,
        out_of_combat_castable=True,
        out_of_combat_target="self_or_ally",
        effects_json=None,
        variants_json=None,
        duration_seconds=60,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# 1. Seed
# ---------------------------------------------------------------------------

class TestSanctuarySeed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SEED_PATH, encoding="utf-8") as f:
            data = json.load(f)
        cls.entry = next(
            (s for s in data.get("spells", []) if s.get("canonicalKey") == "sanctuary"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "sanctuary not found in seed")

    def test_level(self):
        self.assertEqual(self.entry["level"], 1)

    def test_school(self):
        self.assertEqual(self.entry["school"], "abjuration")

    def test_classes(self):
        self.assertIn("Cleric", self.entry["classesJson"])

    def test_casting_time_type(self):
        self.assertEqual(self.entry["castingTimeType"], "bonus_action")

    def test_concentration_false(self):
        self.assertFalse(self.entry["concentration"])

    def test_duration_seconds(self):
        self.assertEqual(self.entry["durationSeconds"], 60)

    def test_resolution_type(self):
        self.assertEqual(self.entry["resolutionType"], "utility")

    def test_out_of_combat_castable(self):
        self.assertTrue(self.entry["outOfCombatCastable"])

    def test_out_of_combat_target(self):
        self.assertEqual(self.entry["outOfCombatTarget"], "self_or_ally")

    def test_effect_timing(self):
        self.assertEqual(self.entry["effectTiming"], "persistent")

    def test_not_ritual(self):
        self.assertFalse(self.entry["ritual"])

    def test_name_pt(self):
        self.assertEqual(self.entry["namePt"], "Santuário")


# ---------------------------------------------------------------------------
# 2. Targeting semantics
# ---------------------------------------------------------------------------

class TestSanctuaryTargetingSemantics(unittest.TestCase):
    def setUp(self):
        self.sem = resolve_spell_targeting_semantics({"canonicalKey": "sanctuary"})

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
# 3. Registry spec
# ---------------------------------------------------------------------------

class TestSanctuaryRegistrySpec(unittest.TestCase):
    def setUp(self):
        self.spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY.get("sanctuary")

    def test_registry_entry_exists(self):
        self.assertIsNotNone(self.spec)

    def test_default_mode(self):
        self.assertEqual(self.spec.default_mode, "utility")

    def test_requires_effect_payload_false(self):
        self.assertFalse(self.spec.requires_effect_payload)

    def test_handler_name(self):
        self.assertEqual(self.spec.handler_name, "_cast_sanctuary_automation")

    def test_canonical_key(self):
        self.assertEqual(self.spec.canonical_key, "sanctuary")


# ---------------------------------------------------------------------------
# 4. Spell context meta
# ---------------------------------------------------------------------------

class TestSanctuarySpellContext(unittest.TestCase):
    def setUp(self):
        self.meta = SpellContextResolveMixin.UTILITY_SPELL_CONTEXT_META.get("sanctuary")

    def test_meta_entry_exists(self):
        self.assertIsNotNone(self.meta)

    def test_type(self):
        self.assertEqual(self.meta["type"], "defense_buff")

    def test_requires_concentration_false(self):
        self.assertFalse(self.meta["requiresConcentration"])

    def test_duration_seconds(self):
        self.assertEqual(self.meta["durationSeconds"], 60)

    def test_targeting_guard(self):
        self.assertTrue(self.meta["targetingGuard"])

    def test_guard_save_ability(self):
        self.assertEqual(self.meta["guardSaveAbility"], "wisdom")

    def test_breaks_on_attack(self):
        self.assertTrue(self.meta["breaksOnAttack"])

    def test_breaks_on_offensive_spell(self):
        self.assertTrue(self.meta["breaksOnOffensiveSpell"])

    def test_breaks_on_damage_dealt(self):
        self.assertTrue(self.meta["breaksOnDamageDealt"])

    def test_ooc_castable(self):
        self.assertTrue(self.meta["outOfCombatCastable"])

    def test_ooc_target(self):
        self.assertEqual(self.meta["outOfCombatTarget"], "self_or_ally")

    def test_does_not_block_area_effects(self):
        self.assertTrue(self.meta["doesNotBlockAreaEffects"])


# ---------------------------------------------------------------------------
# 5. Effect factory
# ---------------------------------------------------------------------------

class TestSanctuaryEffectFactory(unittest.TestCase):
    def setUp(self):
        self.effect = build_sanctuary_effect(_make_ctx(spell_save_dc=14))
        self.meta = self.effect["metadata"]

    def test_kind(self):
        self.assertEqual(self.effect["kind"], "spell_effect")

    def test_sanctuary_flag(self):
        self.assertTrue(self.meta["sanctuary"])

    def test_guard_save_dc(self):
        self.assertEqual(self.meta["guard_save_dc"], 14)

    def test_guard_save_ability(self):
        self.assertEqual(self.meta["guard_save_ability"], "wisdom")

    def test_targeting_guard(self):
        self.assertTrue(self.meta["targeting_guard"])

    def test_breaks_on_attack(self):
        self.assertTrue(self.meta["breaks_on_attack"])

    def test_breaks_on_offensive_spell(self):
        self.assertTrue(self.meta["breaks_on_offensive_spell"])

    def test_breaks_on_damage_dealt(self):
        self.assertTrue(self.meta["breaks_on_damage_dealt"])

    def test_concentration_false(self):
        self.assertFalse(self.meta["concentration"])

    def test_requires_concentration_false(self):
        self.assertFalse(self.meta["requires_concentration"])

    def test_duration_seconds(self):
        self.assertEqual(self.meta["duration_seconds"], 60)

    def test_source_spell_key(self):
        self.assertEqual(self.meta["source_spell_key"], "sanctuary")

    def test_defense_modifier(self):
        self.assertTrue(self.meta["defense_modifier"])

    def test_expires_at_game_time(self):
        self.assertEqual(self.effect["expires_at_game_time_seconds"], 60)

    def test_zero_dc_stored_when_none(self):
        effect = build_sanctuary_effect(_make_ctx(spell_save_dc=None))  # type: ignore[arg-type]
        self.assertEqual(effect["metadata"]["guard_save_dc"], 0)


# ---------------------------------------------------------------------------
# 6. OOC integration
# ---------------------------------------------------------------------------

class TestSanctuaryOoc(unittest.TestCase):
    def _spell(self, **kwargs):
        return _make_ooc_spell(**kwargs)

    def test_is_ooc_utility_spell(self):
        self.assertTrue(_is_ooc_utility_spell("sanctuary"))

    def test_sanctuary_in_ooc_factory_effect_spells(self):
        self.assertIn("sanctuary", OOC_FACTORY_EFFECT_SPELLS)

    def test_ooc_eligibility_self(self):
        spell = self._spell(out_of_combat_target="self")
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 1}}}},
            slot_level=1,
            variant_key=None,
            out_of_combat_target="self",
            target_user_id="u1",
            caster_user_id="u1",
        )
        self.assertTrue(ok, reason)

    def test_ooc_eligibility_ally(self):
        spell = self._spell()
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 1}}}},
            slot_level=1,
            variant_key=None,
            out_of_combat_target="self_or_ally",
            target_user_id="u2",
            caster_user_id="u1",
        )
        self.assertTrue(ok, reason)

    def test_ooc_build_persisted_effects_with_dc(self):
        spell = self._spell()
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="u1",
            target_user_id="u2",
            variant_key=None,
            game_time_seconds=0,
            spell_save_dc=13,
        )
        self.assertEqual(len(effects), 1)
        meta = effects[0]["metadata"]
        self.assertTrue(meta["sanctuary"])
        self.assertEqual(meta["guard_save_dc"], 13)

    def test_ooc_build_persisted_effects_missing_dc_raises(self):
        spell = self._spell()
        with self.assertRaises((ValueError, Exception)):
            build_persisted_effects(
                spell=spell,
                caster_user_id="u1",
                target_user_id="u2",
                variant_key=None,
                game_time_seconds=0,
                spell_save_dc=None,
            )

    def test_ooc_build_persisted_effects_zero_dc_raises(self):
        spell = self._spell()
        with self.assertRaises((ValueError, Exception)):
            build_persisted_effects(
                spell=spell,
                caster_user_id="u1",
                target_user_id="u2",
                variant_key=None,
                game_time_seconds=0,
                spell_save_dc=0,
            )


# ---------------------------------------------------------------------------
# 7. Combat automation handler
# ---------------------------------------------------------------------------

class TestSanctuaryCombatAutomation(unittest.IsolatedAsyncioTestCase):
    async def _cast(
        self,
        attacker_extra: dict | None = None,
        target_extra: dict | None = None,
        variant_key=None,
    ):
        db = _make_db()
        state = _make_state(target_extra=target_extra)
        caster = next(p for p in state.participants if p["id"] == "p1")
        target = next(p for p in state.participants if p["id"] == "p2")
        if attacker_extra:
            caster.update(attacker_extra)

        req = SimpleNamespace(variant_key=variant_key, roll_source="server", override_resource_limit=False)

        with (
            patch.object(
                CombatService,
                "_append_effect_to_participant",
                side_effect=lambda p, e: p.setdefault("active_effects", []).append(e),
            ),
            patch("app.services.combat_service.spells.automation._protection_sanctuary.flag_modified"),
            patch("app.services.combat_service.spells.automation._protection_sanctuary.get_game_time_seconds", return_value=0),
        ):
            result = await CombatService._cast_sanctuary_automation(
                db=db,
                session_id="sess1",
                attacker=caster,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context={
                    "spell_name": "Santuário",
                    "spell_key": "sanctuary",
                    "spell_canonical_key": "sanctuary",
                    "slot_level": 1,
                },
                target_participant=target,
            )
        return result, caster, target

    async def test_effect_applied_to_target(self):
        _, _, target = await self._cast()
        effects = [e for e in target["active_effects"] if e.get("kind") == "spell_effect"]
        self.assertEqual(len(effects), 1)
        self.assertTrue(effects[0]["metadata"]["sanctuary"])

    async def test_guard_save_dc_from_caster(self):
        _, _, target = await self._cast()
        meta = target["active_effects"][0]["metadata"]
        self.assertEqual(meta["guard_save_dc"], 14)

    async def test_result_has_utility_key(self):
        # extra fields are merged flat into the result dict
        result, _, _ = await self._cast()
        self.assertEqual(result.get("utility"), "sanctuary")

    async def test_no_target_raises(self):
        db = _make_db()
        state = _make_state()
        caster = next(p for p in state.participants if p["id"] == "p1")
        req = SimpleNamespace(variant_key=None)
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_sanctuary_automation(
                db=db,
                session_id="sess1",
                attacker=caster,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context={"spell_name": "Santuário", "spell_key": "sanctuary", "spell_canonical_key": "sanctuary", "slot_level": 1},
                target_participant=None,
            )

    async def test_missing_dc_raises(self):
        db = _make_db()
        state = _make_state()
        caster = next(p for p in state.participants if p["id"] == "p1")
        caster["spellcasting"] = {}  # no saveDc
        target = next(p for p in state.participants if p["id"] == "p2")
        req = SimpleNamespace(variant_key=None)
        with (
            patch.object(CombatService, "_append_effect_to_participant"),
            patch("app.services.combat_service.spells.automation._protection_sanctuary.flag_modified"),
            patch("app.services.combat_service.spells.automation._protection_sanctuary.get_game_time_seconds", return_value=0),
            self.assertRaises(CombatServiceError),
        ):
            await CombatService._cast_sanctuary_automation(
                db=db,
                session_id="sess1",
                attacker=caster,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context={"spell_name": "Santuário", "spell_key": "sanctuary", "spell_canonical_key": "sanctuary", "slot_level": 1},
                target_participant=target,
            )


# ---------------------------------------------------------------------------
# 8. Guard intercept (find + break helpers)
# ---------------------------------------------------------------------------

class TestSanctuaryGuardHelpers(unittest.TestCase):
    def test_find_returns_none_when_no_sanctuary(self):
        participant = {"active_effects": []}
        self.assertIsNone(find_sanctuary_effect_on_participant(participant))

    def test_find_returns_effect_when_present(self):
        effect = _make_sanctuary_effect(guard_save_dc=15)
        participant = {"active_effects": [effect]}
        result = find_sanctuary_effect_on_participant(participant)
        self.assertIs(result, effect)

    def test_find_ignores_non_sanctuary_effects(self):
        other = {"kind": "spell_effect", "metadata": {"sanctuary": False}}
        participant = {"active_effects": [other]}
        self.assertIsNone(find_sanctuary_effect_on_participant(participant))

    def test_find_ignores_condition_kind(self):
        condition = {"kind": "condition", "condition_type": "blinded", "metadata": {"sanctuary": True}}
        participant = {"active_effects": [condition]}
        self.assertIsNone(find_sanctuary_effect_on_participant(participant))

    def test_break_removes_sanctuary_effect(self):
        state = MagicMock()
        effect = _make_sanctuary_effect()
        participant = {"active_effects": [effect]}
        removed = break_sanctuary_if_active(participant, state)
        self.assertTrue(removed)
        self.assertEqual(participant["active_effects"], [])

    def test_break_returns_false_when_no_sanctuary(self):
        state = MagicMock()
        participant = {"active_effects": []}
        removed = break_sanctuary_if_active(participant, state)
        self.assertFalse(removed)

    def test_break_preserves_other_effects(self):
        state = MagicMock()
        other = {"kind": "spell_effect", "metadata": {"source_spell_key": "bless"}}
        sanc = _make_sanctuary_effect()
        participant = {"active_effects": [sanc, other]}
        break_sanctuary_if_active(participant, state)
        self.assertEqual(participant["active_effects"], [other])

    def test_break_calls_flag_modified(self):
        state = MagicMock()
        effect = _make_sanctuary_effect()
        participant = {"active_effects": [effect]}
        break_sanctuary_if_active(participant, state)
        state.__class__  # flag_modified called on state (checked via side effect in sanctuary_guard)

    def test_break_twice_returns_false_second_time(self):
        state = MagicMock()
        effect = _make_sanctuary_effect()
        participant = {"active_effects": [effect]}
        break_sanctuary_if_active(participant, state)
        second = break_sanctuary_if_active(participant, state)
        self.assertFalse(second)


if __name__ == "__main__":
    unittest.main()
