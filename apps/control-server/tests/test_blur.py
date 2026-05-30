from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_attacks import resolve_attack_advantage
from app.services.combat_service.condition_effects_predicates import (
    attacker_ignores_incoming_attack_disadvantage_from_sight,
)
from app.services.combat_service.spell_automation import CombatSpellAutomationMixin
from app.services.out_of_combat_cast import (
    _is_ooc_utility_spell,
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


def _blur_effect(effect_id: str = "fx-blur") -> dict:
    return {
        "id": effect_id,
        "kind": "spell_effect",
        "source_participant_id": "caster-1",
        "duration_type": "timed",
        "expires_at_game_time_seconds": 999999,
        "metadata": {
            "source_spell_key": "blur",
            "source_spell_name": "Reflexos",
            "mechanical": True,
            "utility": "blur",
            "concentration": True,
            "concentration_group": "cg-blur",
            "defense_modifier": True,
            "illusion_defense": True,
            "attack_disadvantage_against_target": True,
            "grants_ac_bonus": False,
            "grants_resistance": False,
            "declarative_effect": {
                "type": "attack_disadvantage_against_target",
                "params": {
                    "mode": "disadvantage",
                    "roll_types": ["attack"],
                    "source": "blur",
                    "requires_attacker_sight": True,
                    "ignored_by_senses": ["blindsight", "truesight"],
                    "consume_on_apply": False,
                },
            },
        },
    }


def _make_spell_ooc(**kwargs):
    defaults = dict(
        canonical_key="blur",
        name_pt="Reflexos",
        name_en="Blur",
        level=2,
        concentration=True,
        out_of_combat_castable=True,
        out_of_combat_target="self",
        effects_json=None,
        variants_json=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _slots_state(level: int = 2, used: int = 0, max_slots: int = 3) -> dict:
    return {"spellcasting": {"slots": {str(level): {"used": used, "max": max_slots}}}}


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

class BlurSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SEED_PATH, encoding="utf-8") as f:
            data = json.load(f)
        cls.entry = next(
            (s for s in data.get("spells", []) if s.get("canonicalKey") == "blur"), None
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "blur not found in base_spells.seed.json")

    def test_level(self):
        self.assertEqual(self.entry["level"], 2)

    def test_school(self):
        self.assertEqual(self.entry["school"], "illusion")

    def test_classes(self):
        classes = self.entry["classesJson"]
        self.assertIn("Sorcerer", classes)
        self.assertIn("Wizard", classes)

    def test_range_meters(self):
        self.assertEqual(self.entry["rangeMeters"], 0)

    def test_duration_seconds(self):
        self.assertEqual(self.entry["durationSeconds"], 60)

    def test_concentration(self):
        self.assertTrue(self.entry["concentration"])

    def test_not_ritual(self):
        self.assertFalse(self.entry["ritual"])

    def test_resolution_type(self):
        self.assertEqual(self.entry["resolutionType"], "utility")

    def test_selection_type(self):
        self.assertEqual(self.entry["selectionType"], "self")

    def test_target_anchor(self):
        self.assertEqual(self.entry["targetAnchor"], "caster")

    def test_attack_type(self):
        self.assertEqual(self.entry["attackType"], "none")

    def test_out_of_combat_castable(self):
        self.assertTrue(self.entry.get("outOfCombatCastable"))

    def test_out_of_combat_target(self):
        self.assertEqual(self.entry.get("outOfCombatTarget"), "self")

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

class BlurTargetingSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sem = resolve_spell_targeting_semantics({"canonicalKey": "blur"})

    def test_selection_type(self):
        self.assertEqual(self.sem.selection_type, "self")

    def test_origin_type(self):
        self.assertEqual(self.sem.origin_type, "caster")

    def test_target_anchor(self):
        self.assertEqual(self.sem.target_anchor, "caster")

    def test_attack_type(self):
        self.assertEqual(self.sem.attack_type, "none")

    def test_range_kind(self):
        self.assertEqual(self.sem.range_kind, "self")

    def test_effect_timing(self):
        self.assertEqual(self.sem.effect_timing, "persistent")


# ---------------------------------------------------------------------------
# 3. Registry
# ---------------------------------------------------------------------------

class BlurRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY.get("blur")

    def test_registry_entry_exists(self):
        self.assertIsNotNone(self.spec)

    def test_default_mode(self):
        self.assertEqual(self.spec.default_mode, "utility")

    def test_requires_effect_payload(self):
        self.assertFalse(self.spec.requires_effect_payload)

    def test_handler_name(self):
        self.assertEqual(self.spec.handler_name, "_cast_blur_automation")


# ---------------------------------------------------------------------------
# 4. Automation handler (combat cast)
# ---------------------------------------------------------------------------

class BlurAutomationTests(unittest.IsolatedAsyncioTestCase):
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
                    "action_used": False,
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
        target_participant=None,
        variant_key=None,
        caster_id: str = "p1",
    ) -> dict:
        db = self._make_db()
        state = self._make_state(caster_id=caster_id)
        attacker = next(p for p in state.participants if p["id"] == caster_id)
        if target_participant is None:
            target_participant = attacker

        req = SimpleNamespace(
            variant_key=variant_key,
            roll_source="server",
            override_resource_limit=False,
        )
        spell_context = {"spell_name": "Reflexos", "spell_key": "blur", "spell_canonical_key": "blur", "slot_level": 2}

        with patch.object(CombatService, "_clear_concentration_for_source", return_value={"removed_effects": [], "removed_area_effects": []}), \
             patch.object(CombatService, "_sync_area_effects_if_changed"), \
             patch.object(CombatService, "_append_effect_to_participant", side_effect=lambda p, e: p.setdefault("active_effects", []).append(e)), \
             patch("app.services.combat_service.spells.automation._buffs_defense.flag_modified"), \
             patch("app.services.combat_service.spells.automation._buffs_defense.get_game_time_seconds", return_value=100):
            return await CombatService._cast_blur_automation(
                db=db,
                session_id="sess1",
                attacker=attacker,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=spell_context,
                target_participant=target_participant,
            ), attacker

    async def test_creates_effect_on_caster(self):
        result, caster = await self._cast()
        self.assertEqual(len(caster["active_effects"]), 1)

    async def test_no_effect_created_when_target_mismatch_raises(self):
        state = self._make_state()
        attacker = state.participants[0]
        wrong_target = state.participants[1]
        req = SimpleNamespace(variant_key=None, roll_source="server", override_resource_limit=False)
        with self.assertRaises(Exception) as ctx:
            await CombatService._cast_blur_automation(
                db=self._make_db(),
                session_id="sess1",
                attacker=attacker,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context={"spell_name": "Reflexos", "spell_key": "blur", "spell_canonical_key": "blur", "slot_level": 2},
                target_participant=wrong_target,
            )
        self.assertIn("próprio conjurador", str(ctx.exception))

    async def test_effect_source_spell_key(self):
        _, caster = await self._cast()
        effect = caster["active_effects"][0]
        self.assertEqual(effect["metadata"]["source_spell_key"], "blur")

    async def test_effect_concentration_true(self):
        _, caster = await self._cast()
        self.assertTrue(caster["active_effects"][0]["metadata"]["concentration"])

    async def test_effect_has_concentration_group(self):
        _, caster = await self._cast()
        self.assertIsNotNone(caster["active_effects"][0]["metadata"].get("concentration_group"))

    async def test_metadata_attack_disadvantage_against_target_true(self):
        _, caster = await self._cast()
        self.assertTrue(caster["active_effects"][0]["metadata"]["attack_disadvantage_against_target"])

    async def test_metadata_grants_ac_bonus_false(self):
        _, caster = await self._cast()
        self.assertFalse(caster["active_effects"][0]["metadata"]["grants_ac_bonus"])

    async def test_metadata_grants_resistance_false(self):
        _, caster = await self._cast()
        self.assertFalse(caster["active_effects"][0]["metadata"]["grants_resistance"])

    async def test_declarative_effect_type(self):
        _, caster = await self._cast()
        decl = caster["active_effects"][0]["metadata"]["declarative_effect"]
        self.assertEqual(decl["type"], "attack_disadvantage_against_target")

    async def test_declarative_effect_mode_disadvantage(self):
        _, caster = await self._cast()
        params = caster["active_effects"][0]["metadata"]["declarative_effect"]["params"]
        self.assertEqual(params["mode"], "disadvantage")

    async def test_variant_key_raises_400(self):
        state = self._make_state()
        attacker = state.participants[0]
        req = SimpleNamespace(variant_key="some_variant", roll_source="server")
        with self.assertRaises(Exception) as ctx:
            await CombatService._cast_blur_automation(
                db=self._make_db(),
                session_id="sess1",
                attacker=attacker,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context={"spell_name": "Reflexos", "spell_key": "blur", "spell_canonical_key": "blur", "slot_level": 2},
                target_participant=attacker,
            )
        self.assertIn("variante", str(ctx.exception).lower())

    async def test_no_damage_no_attack_roll(self):
        result, _ = await self._cast()
        self.assertEqual(result.get("damage", 0), 0)
        self.assertIsNone(result.get("roll_result"))

    async def test_action_kind_utility(self):
        result, _ = await self._cast()
        self.assertEqual(result.get("action_kind"), "utility")

    async def test_recast_substitutes_blur_effect(self):
        state = self._make_state()
        attacker = state.participants[0]
        old_effect = _blur_effect("old-blur")
        attacker["active_effects"] = [old_effect]
        req = SimpleNamespace(variant_key=None, roll_source="server", override_resource_limit=False)
        spell_context = {"spell_name": "Reflexos", "spell_key": "blur", "spell_canonical_key": "blur", "slot_level": 2}

        with patch.object(CombatService, "_clear_concentration_for_source", return_value={"removed_effects": [], "removed_area_effects": []}), \
             patch.object(CombatService, "_sync_area_effects_if_changed"), \
             patch.object(CombatService, "_normalize_lookup", side_effect=lambda x: x), \
             patch.object(CombatService, "_get_effect_metadata", side_effect=lambda e: e.get("metadata", {})), \
             patch.object(CombatService, "_append_effect_to_participant", side_effect=lambda p, e: p.setdefault("active_effects", []).append(e)), \
             patch("app.services.combat_service.spells.automation._buffs_defense.flag_modified"), \
             patch("app.services.combat_service.spells.automation._buffs_defense.get_game_time_seconds", return_value=100):
            await CombatService._cast_blur_automation(
                db=self._make_db(),
                session_id="sess1",
                attacker=attacker,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=spell_context,
                target_participant=attacker,
            )

        keys = [e["metadata"]["source_spell_key"] for e in attacker.get("active_effects", [])]
        self.assertEqual(keys.count("blur"), 1, "Should have exactly one blur effect after recast")
        self.assertNotIn("old-blur", [e["id"] for e in attacker.get("active_effects", [])])


# ---------------------------------------------------------------------------
# 5. Disadvantage resolution via resolve_attack_advantage
# ---------------------------------------------------------------------------

class BlurDisadvantageTests(unittest.TestCase):
    def _make_target_with_blur(self, participant_id: str = "t1") -> dict:
        return {
            "id": participant_id,
            "kind": "player",
            "active_effects": [_blur_effect()],
        }

    def _make_attacker(self, senses: dict | None = None, does_not_rely_on_sight: bool = False) -> dict:
        a = {"id": "a1", "kind": "session_entity", "active_effects": []}
        if senses is not None:
            a["senses"] = senses
        if does_not_rely_on_sight:
            a["does_not_rely_on_sight"] = True
        return a

    def test_normal_attacker_gets_disadvantage(self):
        attacker = self._make_attacker()
        target = self._make_target_with_blur()
        ctx = resolve_attack_advantage(attacker, target)
        self.assertIn("blur", ctx.disadvantage_sources)
        self.assertEqual(ctx.result, "disadvantage")

    def test_attacker_with_truesight_ignores_blur(self):
        attacker = self._make_attacker(senses={"truesightMeters": 18})
        target = self._make_target_with_blur()
        ctx = resolve_attack_advantage(attacker, target)
        self.assertNotIn("blur", ctx.disadvantage_sources)

    def test_attacker_with_blindsight_ignores_blur(self):
        attacker = self._make_attacker(senses={"blindsightMeters": 9})
        target = self._make_target_with_blur()
        ctx = resolve_attack_advantage(attacker, target)
        self.assertNotIn("blur", ctx.disadvantage_sources)

    def test_attacker_does_not_rely_on_sight_ignores_blur(self):
        attacker = self._make_attacker(does_not_rely_on_sight=True)
        target = self._make_target_with_blur()
        ctx = resolve_attack_advantage(attacker, target)
        self.assertNotIn("blur", ctx.disadvantage_sources)

    def test_attack_against_target_without_blur_unaffected(self):
        attacker = self._make_attacker()
        target = {"id": "t1", "kind": "player", "active_effects": []}
        ctx = resolve_attack_advantage(attacker, target)
        self.assertNotIn("blur", ctx.disadvantage_sources)

    def test_multiple_blur_effects_one_source(self):
        attacker = self._make_attacker()
        target = {
            "id": "t1",
            "kind": "player",
            "active_effects": [_blur_effect("fx1"), _blur_effect("fx2")],
        }
        ctx = resolve_attack_advantage(attacker, target)
        self.assertEqual(ctx.disadvantage_sources.count("blur"), 1)

    def test_blur_consume_on_apply_false_no_id_in_consumed(self):
        attacker = self._make_attacker()
        target = self._make_target_with_blur()
        ctx = resolve_attack_advantage(attacker, target)
        self.assertNotIn("fx-blur", ctx.consumed_effect_ids_on_roll)


# ---------------------------------------------------------------------------
# 6. Senses helper
# ---------------------------------------------------------------------------

class BlurSensesHelperTests(unittest.TestCase):
    def _a(self, **kwargs) -> dict:
        return dict(kwargs)

    def test_senses_dict_truesight_camel(self):
        self.assertTrue(attacker_ignores_incoming_attack_disadvantage_from_sight(
            {"senses": {"truesightMeters": 18}}
        ))

    def test_senses_dict_truesight_snake(self):
        self.assertTrue(attacker_ignores_incoming_attack_disadvantage_from_sight(
            {"senses": {"truesight_meters": 18}}
        ))

    def test_senses_dict_truesight_bare(self):
        self.assertTrue(attacker_ignores_incoming_attack_disadvantage_from_sight(
            {"senses": {"truesight": 18}}
        ))

    def test_senses_dict_blindsight_camel(self):
        self.assertTrue(attacker_ignores_incoming_attack_disadvantage_from_sight(
            {"senses": {"blindsightMeters": 9}}
        ))

    def test_senses_dict_blindsight_snake(self):
        self.assertTrue(attacker_ignores_incoming_attack_disadvantage_from_sight(
            {"senses": {"blindsight_meters": 9}}
        ))

    def test_senses_dict_blindsight_bare(self):
        self.assertTrue(attacker_ignores_incoming_attack_disadvantage_from_sight(
            {"senses": {"blindsight": 9}}
        ))

    def test_senses_list_truesight(self):
        self.assertTrue(attacker_ignores_incoming_attack_disadvantage_from_sight(
            {"senses": [{"type": "truesight", "range_meters": 18}]}
        ))

    def test_senses_list_blindsight(self):
        self.assertTrue(attacker_ignores_incoming_attack_disadvantage_from_sight(
            {"senses": [{"type": "blindsight", "range_meters": 9}]}
        ))

    def test_metadata_senses_truesight(self):
        self.assertTrue(attacker_ignores_incoming_attack_disadvantage_from_sight(
            {"metadata": {"senses": {"truesightMeters": 18}}}
        ))

    def test_no_senses_returns_false(self):
        self.assertFalse(attacker_ignores_incoming_attack_disadvantage_from_sight({}))

    def test_darkvision_only_returns_false(self):
        self.assertFalse(attacker_ignores_incoming_attack_disadvantage_from_sight(
            {"senses": {"darkvisionMeters": 18}}
        ))

    def test_does_not_rely_on_sight_flag(self):
        self.assertTrue(attacker_ignores_incoming_attack_disadvantage_from_sight(
            {"does_not_rely_on_sight": True}
        ))

    def test_malformed_senses_safe(self):
        self.assertFalse(attacker_ignores_incoming_attack_disadvantage_from_sight(
            {"senses": "invalid_string"}
        ))

    def test_senses_none_safe(self):
        self.assertFalse(attacker_ignores_incoming_attack_disadvantage_from_sight(
            {"senses": None}
        ))


# ---------------------------------------------------------------------------
# 7. OOC
# ---------------------------------------------------------------------------

class BlurOocTests(unittest.TestCase):
    def test_blur_in_special_ooc_utility_spells(self):
        self.assertTrue(_is_ooc_utility_spell("blur"))

    def test_check_ooc_eligibility_accepts(self):
        spell = _make_spell_ooc()
        state_json = _slots_state(level=2)
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json=state_json,
            slot_level=2,
            variant_key=None,
            out_of_combat_target="self",
            target_user_id="u1",
            caster_user_id="u1",
        )
        self.assertTrue(ok, reason)
        self.assertIsNone(reason)

    def test_build_persisted_effects_creates_effect(self):
        spell = _make_spell_ooc()
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="u1",
            target_user_id="u1",
            variant_key=None,
            game_time_seconds=100,
        )
        self.assertEqual(len(effects), 1)

    def test_persisted_effect_concentration_metadata(self):
        spell = _make_spell_ooc()
        effects = build_persisted_effects(
            spell=spell, caster_user_id="u1", target_user_id="u1",
            variant_key=None, game_time_seconds=100,
        )
        md = effects[0]["metadata"]
        self.assertEqual(md["source_spell_key"], "blur")
        self.assertTrue(md["concentration"])
        self.assertIsNotNone(md.get("concentration_group"))

    def test_persisted_effect_has_declarative_effect(self):
        spell = _make_spell_ooc()
        effects = build_persisted_effects(
            spell=spell, caster_user_id="u1", target_user_id="u1",
            variant_key=None, game_time_seconds=100,
        )
        decl = effects[0]["metadata"]["declarative_effect"]
        self.assertEqual(decl["type"], "attack_disadvantage_against_target")
        self.assertEqual(decl["params"]["mode"], "disadvantage")

    def test_persisted_effect_duration_60(self):
        spell = _make_spell_ooc()
        effects = build_persisted_effects(
            spell=spell, caster_user_id="u1", target_user_id="u1",
            variant_key=None, game_time_seconds=100,
        )
        self.assertEqual(effects[0]["expires_at_game_time_seconds"], 160)

    def test_persisted_effect_created_out_of_combat(self):
        spell = _make_spell_ooc()
        effects = build_persisted_effects(
            spell=spell, caster_user_id="u1", target_user_id="u1",
            variant_key=None, game_time_seconds=100,
        )
        self.assertTrue(effects[0]["metadata"]["created_out_of_combat"])

    def test_ooc_target_ally_rejected(self):
        """outOfCombatTarget='self' means targeting another player is rejected."""
        spell = _make_spell_ooc()
        state_json = _slots_state(level=2)
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json=state_json,
            slot_level=2,
            variant_key=None,
            out_of_combat_target="self",
            target_user_id="u2",   # different from caster
            caster_user_id="u1",
        )
        self.assertFalse(ok)
        self.assertIn("only target yourself", reason)

    def test_ooc_no_slots_rejected(self):
        spell = _make_spell_ooc()
        state_json = _slots_state(level=2, used=3, max_slots=3)
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell, state_json=state_json, slot_level=2, variant_key=None,
        )
        self.assertFalse(ok)
        self.assertIn("spell slot", reason)


# ---------------------------------------------------------------------------
# 8. Spell context utility meta
# ---------------------------------------------------------------------------

class BlurSpellContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.combat_service.spells.spell_context_resolve import SpellContextResolveMixin
        cls.meta = SpellContextResolveMixin.UTILITY_SPELL_CONTEXT_META["blur"]

    def test_type_defense_buff(self):
        self.assertEqual(self.meta["type"], "defense_buff")

    def test_subtype_blur(self):
        self.assertEqual(self.meta["subtype"], "blur")

    def test_requires_concentration(self):
        self.assertTrue(self.meta["requiresConcentration"])

    def test_duration_seconds(self):
        self.assertEqual(self.meta["durationSeconds"], 60)

    def test_attack_disadvantage_against_target(self):
        self.assertTrue(self.meta["attackDisadvantageAgainstTarget"])

    def test_ignored_by_blindsight(self):
        self.assertTrue(self.meta["ignoredByBlindsight"])

    def test_ignored_by_truesight(self):
        self.assertTrue(self.meta["ignoredByTruesight"])

    def test_grants_ac_bonus_false(self):
        self.assertFalse(self.meta["grantsACBonus"])

    def test_ooc_castable(self):
        self.assertTrue(self.meta["outOfCombatCastable"])

    def test_ooc_target_self(self):
        self.assertEqual(self.meta["outOfCombatTarget"], "self")


if __name__ == "__main__":
    unittest.main()
