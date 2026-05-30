from __future__ import annotations

import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_attacks import resolve_attack_advantage
from app.services.combat_service.spell_automation import CombatSpellAutomationMixin
from app.services.out_of_combat_cast import _is_ooc_utility_spell
from app.services.spell_effect_factories import (
    SpellEffectBuildContext,
    build_compelled_duel_effect,
)
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics
from app.services import compelled_duel as cd


def _first(value):
    mock = MagicMock()
    mock.first.return_value = value
    return mock


def _effect(caster_ref="cref", target_ref="tref", dc=14, group="grp-1"):
    ctx = SpellEffectBuildContext(
        spell_key="compelled_duel",
        spell_name="Duelo Compelido",
        game_time_seconds=0,
        duration_seconds=60,
        concentration=True,
        concentration_group=group,
        source_participant_id="cpid",
        owner_participant_id="tpid",
        created_by_participant_id="cpid",
        context_origin="combat",
        spell_save_dc=dc,
        extra_metadata={"duel_caster_ref_id": caster_ref, "duel_target_ref_id": target_ref},
    )
    return build_compelled_duel_effect(ctx)


def _state(caster_team="players", target_team="enemies", ally_team=None):
    parts = [
        {"id": "cpid", "ref_id": "cref", "kind": "player", "team": caster_team, "display_name": "Pal", "active_effects": []},
        {"id": "tpid", "ref_id": "tref", "kind": "session_entity", "team": target_team, "display_name": "Orc", "active_effects": [_effect()]},
    ]
    if ally_team is not None:
        parts.append({"id": "apid", "ref_id": "aref", "kind": "player", "team": ally_team, "display_name": "Ally", "active_effects": []})
    parts.append({"id": "opid", "ref_id": "oref", "kind": "session_entity", "team": "enemies", "display_name": "Other", "active_effects": []})
    return CombatState(
        id="c1", session_id="s1", phase=CombatPhase.active, round=1, current_turn_index=0,
        participants=parts,
    )


class CompelledDuelSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        cls.entry = next((s for s in data.get("spells", []) if s.get("canonicalKey") == "compelled_duel"), None)

    def test_seed_contract(self):
        self.assertIsNotNone(self.entry)
        self.assertEqual(self.entry["level"], 1)
        self.assertEqual(self.entry["school"], "enchantment")
        self.assertEqual(self.entry["classesJson"], ["Paladin"])
        self.assertEqual(self.entry["castingTimeType"], "bonus_action")
        self.assertEqual(self.entry["durationSeconds"], 60)
        self.assertTrue(self.entry["concentration"])
        self.assertEqual(self.entry["savingThrowAbility"], "wisdom")
        self.assertFalse(self.entry["outOfCombatCastable"])


class CompelledDuelSemanticsRegistryTests(unittest.TestCase):
    def test_targeting_override(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "compelled_duel"})
        self.assertEqual(sem.selection_type, "single_target")
        self.assertEqual(sem.target_anchor, "target")
        self.assertEqual(sem.range_kind, "distance")
        self.assertEqual(sem.effect_timing, "persistent")

    def test_registry_entry(self):
        spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY.get("compelled_duel")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.default_mode, "save")
        self.assertFalse(spec.requires_effect_payload)
        self.assertEqual(spec.handler_name, "_cast_compelled_duel_automation")

    def test_not_ooc_castable(self):
        self.assertFalse(_is_ooc_utility_spell("compelled_duel"))


class CompelledDuelFactoryTests(unittest.TestCase):
    def test_metadata(self):
        md = _effect(dc=15)["metadata"]
        self.assertTrue(md["compelled_duel"])
        self.assertEqual(md["duel_caster_ref_id"], "cref")
        self.assertEqual(md["duel_target_ref_id"], "tref")
        self.assertTrue(md["movement_restriction"])
        self.assertEqual(md["movement_restriction_save_dc"], 15)
        self.assertTrue(md["concentration"])
        self.assertEqual(md["max_distance_meters"], 9)

    def test_declarative_disadvantage(self):
        decl = _effect()["metadata"]["declarative_effect"]
        self.assertEqual(decl["type"], "roll_disadvantage_modifier")
        self.assertEqual(decl["params"]["mode"], "disadvantage")
        self.assertEqual(decl["params"]["roll_types"], ["attack"])
        self.assertEqual(decl["params"]["applies_unless_attacking_ref_id"], "cref")


class CompelledDuelAttackDisadvantageTests(unittest.TestCase):
    def _attacker(self):
        return {"id": "tpid", "ref_id": "tref", "active_effects": [_effect()]}

    def test_attacking_caster_no_disadvantage(self):
        caster = {"id": "cpid", "ref_id": "cref", "active_effects": []}
        ctx = resolve_attack_advantage(self._attacker(), caster, "melee")
        self.assertNotIn("Duelo Compelido", ctx.disadvantage_sources)
        self.assertEqual(ctx.result, "normal")

    def test_attacking_other_has_disadvantage(self):
        other = {"id": "opid", "ref_id": "oref", "active_effects": []}
        ctx = resolve_attack_advantage(self._attacker(), other, "melee")
        self.assertIn("Duelo Compelido", ctx.disadvantage_sources)
        self.assertEqual(ctx.result, "disadvantage")

    def test_uncompelled_attacker_unaffected(self):
        attacker = {"id": "x", "ref_id": "xref", "active_effects": []}
        other = {"id": "opid", "ref_id": "oref", "active_effects": []}
        ctx = resolve_attack_advantage(attacker, other, "melee")
        self.assertEqual(ctx.result, "normal")


class CompelledDuelBreakTests(unittest.TestCase):
    def test_caster_attacks_target_keeps(self):
        state = _state()
        cd.break_compelled_duel_if_caster_attacks_other(state, "cref", "tref")
        self.assertIsNotNone(cd.find_compelled_duel_effect_on_target(state.participants[1]))

    def test_caster_attacks_other_removes(self):
        state = _state()
        removed = cd.break_compelled_duel_if_caster_attacks_other(state, "cref", "oref")
        self.assertEqual(len(removed), 1)
        self.assertIsNone(cd.find_compelled_duel_effect_on_target(state.participants[1]))

    def test_ally_damages_target_removes(self):
        state = _state(caster_team="players", ally_team="allies")
        removed = cd.break_compelled_duel_if_ally_harms_target(state, "aref", "tref")
        self.assertEqual(len(removed), 1)

    def test_caster_self_does_not_break_via_ally_helper(self):
        state = _state()
        removed = cd.break_compelled_duel_if_ally_harms_target(state, "cref", "tref")
        self.assertEqual(removed, [])
        self.assertIsNotNone(cd.find_compelled_duel_effect_on_target(state.participants[1]))

    def test_enemy_damages_target_keeps(self):
        # An enemy of the caster (same side as the target) damaging the target does not end it.
        state = _state(caster_team="players", target_team="enemies")
        removed = cd.break_compelled_duel_if_ally_harms_target(state, "oref", "tref")
        self.assertEqual(removed, [])

    def test_target_defeated_removes(self):
        state = _state()
        removed = cd.break_compelled_duel_on_target_defeated(state, "tref")
        self.assertEqual(len(removed), 1)

    def test_distance_break_over_9(self):
        state = _state()
        state.local_distances = {"cref": {"tref": 12.0}}
        removed = cd.break_compelled_duels_exceeding_distance(state, "cref")
        self.assertEqual(len(removed), 1)

    def test_distance_within_9_keeps(self):
        state = _state()
        state.local_distances = {"cref": {"tref": 6.0}}
        self.assertEqual(cd.break_compelled_duels_exceeding_distance(state, "cref"), [])

    def test_distance_unconfigured_keeps(self):
        state = _state()
        state.local_distances = {}
        self.assertEqual(cd.break_compelled_duels_exceeding_distance(state, "cref"), [])


class CompelledDuelCastTests(unittest.TestCase):
    def _run_cast(self, *, save_success):
        state = _state()
        state.participants[1]["active_effects"] = []  # fresh target
        attacker = state.participants[0]
        target = state.participants[1]
        db = MagicMock()
        spell_context = {
            "spell_name": "Duelo Compelido",
            "spell_canonical_key": "compelled_duel",
            "save_ability": "wisdom",
            "save_dc": 14,
            "context_origin": "initial_cast",
        }
        req = SimpleNamespace(variant_key=None)
        fake_roll = SimpleNamespace(success=save_success, total=13, check_modifier_sources=[], is_gm_roll=False)
        with patch(
            "app.services.combat_service.spells.automation._control_spells.resolve_saving_throw",
            return_value=fake_roll,
        ), patch(
            "app.services.combat_service.spells.automation._control_spells.get_game_time_seconds",
            return_value=0,
        ), patch.object(
            CombatService, "_build_roll_actor_stats_for_save", return_value=SimpleNamespace()
        ), patch.object(
            CombatService, "_clear_concentration_for_source",
            return_value={"removed_area_effects": [], "removed_effects": []},
        ), patch.object(
            CombatService, "_sync_area_effects_if_changed"
        ):
            result = asyncio.run(
                CombatService._cast_compelled_duel_automation(
                    db, "s1",
                    attacker=attacker, attacker_model=None, actor_user_id="cref",
                    is_gm=False, req=req, state=state, spell_context=spell_context,
                    target_participant=target,
                )
            )
        return result, target

    def test_success_no_effect(self):
        result, target = self._run_cast(save_success=True)
        self.assertTrue(result["is_saved"])
        self.assertFalse(result["effect_applied"])
        self.assertEqual(target["active_effects"], [])

    def test_failure_applies_effect(self):
        result, target = self._run_cast(save_success=False)
        self.assertFalse(result["is_saved"])
        self.assertTrue(result["effect_applied"])
        self.assertIsNotNone(cd.find_compelled_duel_effect_on_target(target))
        self.assertIsNotNone(result["concentration_group"])

    def test_self_target_rejected(self):
        state = _state()
        attacker = state.participants[0]
        db = MagicMock()
        req = SimpleNamespace(variant_key=None)
        with self.assertRaises(Exception):
            asyncio.run(
                CombatService._cast_compelled_duel_automation(
                    db, "s1", attacker=attacker, attacker_model=None, actor_user_id="cref",
                    is_gm=False, req=req, state=state,
                    spell_context={"spell_name": "Duelo Compelido", "spell_canonical_key": "compelled_duel", "save_dc": 14},
                    target_participant=attacker,
                )
            )


class CompelledDuelMovementSaveTests(unittest.TestCase):
    def _run(self, *, save_success=False, already_free=False):
        state = _state()
        actor = state.participants[1]
        if already_free:
            actor["turn_resources"] = {"compelled_duel_movement_free": True}
        db = MagicMock()
        fake_roll = SimpleNamespace(success=save_success, total=11, check_modifier_sources=[], is_gm_roll=False, dc=14)
        with patch(
            "app.services.combat_service.spells.automation._control_spells.resolve_saving_throw",
            return_value=fake_roll,
        ), patch.object(
            CombatService, "get_state", return_value=state
        ), patch.object(
            CombatService, "_require_active"
        ), patch.object(
            CombatService, "_resolve_actor_participant", return_value=actor
        ), patch.object(
            CombatService, "_build_roll_actor_stats_for_save", return_value=SimpleNamespace()
        ), patch.object(
            CombatService, "_apply_flat_save_effect_bonus_to_roll_result", return_value=0
        ), patch.object(
            CombatService, "_emit_state", new=AsyncMock()
        ), patch.object(
            CombatService, "_emit_log", new=AsyncMock()
        ):
            return asyncio.run(
                CombatService.resolve_compelled_duel_movement_save(
                    db, "s1", actor_participant_id="tpid", actor_user_id="tref", is_gm=True,
                )
            ), actor

    def test_already_free_allows_without_roll(self):
        result, _ = self._run(already_free=True)
        self.assertTrue(result["allowed"])
        self.assertFalse(result["rolled"])

    def test_success_sets_free_flag(self):
        result, actor = self._run(save_success=True)
        self.assertTrue(result["allowed"])
        self.assertTrue(result["rolled"])
        self.assertTrue(actor["turn_resources"]["compelled_duel_movement_free"])

    def test_failure_restricts(self):
        result, actor = self._run(save_success=False)
        self.assertFalse(result["allowed"])
        self.assertTrue(result["rolled"])
        self.assertFalse(actor.get("turn_resources", {}).get("compelled_duel_movement_free", False))

    def test_no_effect_rejected(self):
        state = _state()
        actor_no_effect = state.participants[0]  # caster, no duel effect on them
        db = MagicMock()
        with patch.object(CombatService, "get_state", return_value=state), patch.object(
            CombatService, "_require_active"
        ), patch.object(
            CombatService, "_resolve_actor_participant", return_value=actor_no_effect
        ):
            with self.assertRaises(Exception):
                asyncio.run(
                    CombatService.resolve_compelled_duel_movement_save(
                        db, "s1", actor_participant_id="cpid", actor_user_id="cref", is_gm=True,
                    )
                )


if __name__ == "__main__":
    unittest.main()
