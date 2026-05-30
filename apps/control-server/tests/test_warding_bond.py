from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.combat_service.spell_automation import CombatSpellAutomationMixin
from app.services.combat_service.spells.spell_context_resolve import SpellContextResolveMixin
from app.services.combat_service.condition_effects_predicates import (
    get_saving_throw_effect_bonus_sources,
)
from app.services.out_of_combat_cast import (
    OOC_LINKED_EFFECT_SPELLS,
    _is_ooc_utility_spell,
    build_ooc_warding_bond_effects,
)
from app.services.session_state_finalize import sum_spell_effect_ac_bonus
from app.services.spell_effect_factories import (
    SpellEffectBuildContext,
    build_warding_bond_effects,
)
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics
from app.services.warding_bond import (
    break_warding_bonds_exceeding_distance,
    break_warding_bonds_for_caster,
    find_target_role_effect,
    remove_warding_bonds_involving_participants,
)


def _first(value):
    mock = MagicMock()
    mock.first.return_value = value
    return mock


def _build_effects(caster_ref="cref", target_ref="tref", bond_group="bg-1"):
    ctx = SpellEffectBuildContext(
        spell_key="warding_bond",
        spell_name="Vínculo de Proteção",
        game_time_seconds=0,
        duration_seconds=3600,
        concentration=False,
        concentration_group=None,
        source_participant_id="cpid",
        owner_participant_id="tpid",
        created_by_participant_id="cpid",
        context_origin="combat",
        extra_metadata={
            "bond_group": bond_group,
            "bond_caster_participant_id": caster_ref,
            "bond_target_participant_id": target_ref,
        },
    )
    return build_warding_bond_effects(ctx)


def _state_with_bond(caster_hp_effects=True):
    target_effect, caster_effect = _build_effects()
    return CombatState(
        id="c1",
        session_id="s1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=[
            {"id": "cpid", "ref_id": "cref", "kind": "player", "active_effects": [caster_effect]},
            {"id": "tpid", "ref_id": "tref", "kind": "player", "active_effects": [target_effect]},
        ],
    )


class WardingBondSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        cls.entry = next(
            (s for s in data.get("spells", []) if s.get("canonicalKey") == "warding_bond"), None
        )

    def test_seed_contract(self):
        self.assertIsNotNone(self.entry)
        self.assertEqual(self.entry["level"], 2)
        self.assertEqual(self.entry["school"], "abjuration")
        self.assertIn("Cleric", self.entry["classesJson"])
        self.assertEqual(self.entry["castingTimeType"], "action")
        self.assertEqual(self.entry["rangeKind"], "touch")
        self.assertEqual(self.entry["durationSeconds"], 3600)
        self.assertFalse(self.entry["concentration"])
        self.assertFalse(self.entry["materialComponentConsumed"])
        self.assertTrue(self.entry.get("outOfCombatCastable"))
        self.assertEqual(self.entry.get("outOfCombatTarget"), "self_or_ally")


class WardingBondSemanticsRegistryTests(unittest.TestCase):
    def test_targeting_override(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "warding_bond"})
        self.assertEqual(sem.selection_type, "single_target")
        self.assertEqual(sem.target_anchor, "target")
        self.assertEqual(sem.attack_type, "none")
        self.assertEqual(sem.range_kind, "touch")
        self.assertEqual(sem.effect_timing, "persistent")

    def test_registry_entry(self):
        spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY.get("warding_bond")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.default_mode, "utility")
        self.assertFalse(spec.requires_effect_payload)
        self.assertEqual(spec.handler_name, "_cast_warding_bond_automation")

    def test_context_meta(self):
        meta = SpellContextResolveMixin.UTILITY_SPELL_CONTEXT_META["warding_bond"]
        self.assertEqual(meta["type"], "defense_buff")
        self.assertTrue(meta["damageSharing"])
        self.assertTrue(meta["grantsACBonus"])
        self.assertEqual(meta["armorClassBonus"], 1)
        self.assertTrue(meta["grantsSavingThrowBonus"])
        self.assertTrue(meta["grantsResistance"])
        self.assertEqual(meta["maxDistanceMeters"], 18)

    def test_ooc_allowlist(self):
        self.assertTrue(_is_ooc_utility_spell("warding_bond"))
        self.assertIn("warding_bond", OOC_LINKED_EFFECT_SPELLS)


class WardingBondFactoryTests(unittest.TestCase):
    def test_two_effects_share_bond_group(self):
        target_effect, caster_effect = _build_effects(bond_group="grp-x")
        self.assertEqual(target_effect["metadata"]["bond_group"], "grp-x")
        self.assertEqual(caster_effect["metadata"]["bond_group"], "grp-x")
        self.assertEqual(target_effect["metadata"]["warding_bond_role"], "target")
        self.assertEqual(caster_effect["metadata"]["warding_bond_role"], "caster")

    def test_target_effect_flags(self):
        target_effect, _ = _build_effects()
        md = target_effect["metadata"]
        self.assertTrue(md["grants_ac_bonus"])
        self.assertEqual(md["armor_class_bonus"], 1)
        self.assertTrue(md["grants_saving_throw_bonus"])
        self.assertEqual(md["saving_throw_bonus"], 1)
        self.assertTrue(md["grants_resistance_all"])
        self.assertTrue(md["shares_damage_with_caster"])
        self.assertFalse(md["concentration"])

    def test_caster_marker_has_no_bonuses(self):
        _, caster_effect = _build_effects()
        md = caster_effect["metadata"]
        self.assertFalse(md["grants_ac_bonus"])
        self.assertFalse(md["grants_saving_throw_bonus"])
        self.assertFalse(md["grants_resistance_all"])
        self.assertFalse(md["shares_damage_with_caster"])
        self.assertTrue(md["marker_only"])


class WardingBondAcTests(unittest.TestCase):
    def test_player_target_gets_plus_one(self):
        target_effect, _ = _build_effects()
        state_json = {"abilities": {"dexterity": 16}, "spellcasting": {}}  # base 13
        state_model = SimpleNamespace(state_json=state_json)
        db = MagicMock()
        db.exec.return_value = _first(state_model)
        combat_state = CombatState(
            id="c1", session_id="s1", phase=CombatPhase.active, round=1, current_turn_index=0,
            participants=[{"id": "p1", "ref_id": "u1", "kind": "player", "active_effects": [target_effect]}],
        )
        _, ac, *_ = CombatService._get_stats(db, "u1", "player", "s1", combat_state=combat_state)
        self.assertEqual(ac, 14)

    def test_npc_target_gets_plus_one(self):
        target_effect, _ = _build_effects()
        session_entity = SimpleNamespace(campaign_entity_id="npc-1", overrides={"armorClass": 13})
        campaign_entity = SimpleNamespace(abilities={}, spellcasting={}, armor_class=13)
        db = MagicMock()
        db.exec.side_effect = [_first(session_entity), _first(campaign_entity)]
        combat_state = CombatState(
            id="c1", session_id="s1", phase=CombatPhase.active, round=1, current_turn_index=0,
            participants=[{"id": "e1", "ref_id": "entity-1", "kind": "session_entity", "active_effects": [target_effect]}],
        )
        _, ac, *_ = CombatService._get_stats(db, "entity-1", "session_entity", "s1", combat_state=combat_state)
        self.assertEqual(ac, 14)

    def test_caster_marker_grants_no_ac(self):
        _, caster_effect = _build_effects()
        self.assertEqual(sum_spell_effect_ac_bonus([caster_effect]), 0)

    def test_sum_helper(self):
        target_effect, _ = _build_effects()
        self.assertEqual(sum_spell_effect_ac_bonus([target_effect]), 1)
        self.assertEqual(sum_spell_effect_ac_bonus(None), 0)


class WardingBondSaveTests(unittest.TestCase):
    def test_target_save_bonus_source(self):
        target_effect, _ = _build_effects()
        sources = get_saving_throw_effect_bonus_sources({"active_effects": [target_effect]})
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["signed_total"], 1)
        self.assertEqual(sources[0]["roll_type"], "save")

    def test_caster_marker_no_save_bonus(self):
        _, caster_effect = _build_effects()
        self.assertEqual(get_saving_throw_effect_bonus_sources({"active_effects": [caster_effect]}), [])

    def test_flat_helper_applies_and_rechecks_dc(self):
        target_effect, _ = _build_effects()
        roll_result = SimpleNamespace(total=14, dc=15, success=False, check_modifier_sources=None)
        applied = CombatService._apply_flat_save_effect_bonus_to_roll_result(
            participant={"active_effects": [target_effect]}, roll_result=roll_result
        )
        self.assertEqual(applied, 1)
        self.assertEqual(roll_result.total, 15)
        self.assertTrue(roll_result.success)


class WardingBondResistanceTests(unittest.TestCase):
    def test_target_halves_damage(self):
        target_effect, _ = _build_effects()
        participant = {"active_effects": [target_effect]}
        reduced, msg = CombatService._apply_warding_bond_resistance(participant, 20)
        self.assertEqual(reduced, 10)
        self.assertTrue(msg)

    def test_caster_marker_no_resistance(self):
        _, caster_effect = _build_effects()
        reduced, msg = CombatService._apply_warding_bond_resistance({"active_effects": [caster_effect]}, 20)
        self.assertEqual(reduced, 20)
        self.assertEqual(msg, "")

    def test_find_target_role_effect(self):
        target_effect, caster_effect = _build_effects()
        self.assertIsNotNone(find_target_role_effect({"active_effects": [target_effect]}))
        self.assertIsNone(find_target_role_effect({"active_effects": [caster_effect]}))


class WardingBondDamageShareTests(unittest.TestCase):
    def test_share_mirrors_final_damage_to_caster(self):
        state = _state_with_bond()
        target_participant = state.participants[1]
        db = MagicMock()
        calls = []

        def fake_apply(_db, ref_id, kind, amount, **kwargs):
            calls.append((ref_id, kind, amount, kwargs.get("warding_bond_share")))
            return 30, "", 40, None

        with patch.object(CombatService, "_apply_damage_to_target", side_effect=fake_apply):
            CombatService._apply_warding_bond_effects_after_damage(
                db, state, target_participant,
                target_new_hp=30, final_amount=10, is_crit=False, warding_bond_share=False,
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "cref")  # caster ref_id
        self.assertEqual(calls[0][2], 10)      # mirrored final amount
        self.assertTrue(calls[0][3])           # warding_bond_share=True

    def test_share_does_not_recurse_when_flag_set(self):
        state = _state_with_bond()
        target_participant = state.participants[1]
        db = MagicMock()
        with patch.object(CombatService, "_apply_damage_to_target") as mocked:
            CombatService._apply_warding_bond_effects_after_damage(
                db, state, target_participant,
                target_new_hp=30, final_amount=10, is_crit=False, warding_bond_share=True,
            )
        mocked.assert_not_called()

    def test_missing_caster_fails_safe_removes_bond(self):
        state = _state_with_bond()
        # Drop the caster participant.
        state.participants = [state.participants[1]]
        target_participant = state.participants[0]
        db = MagicMock()
        with patch.object(CombatService, "_apply_damage_to_target") as mocked:
            CombatService._apply_warding_bond_effects_after_damage(
                db, state, target_participant,
                target_new_hp=30, final_amount=10, is_crit=False, warding_bond_share=False,
            )
        mocked.assert_not_called()
        self.assertIsNone(find_target_role_effect(target_participant))

    def test_caster_at_zero_breaks_bond(self):
        state = _state_with_bond()
        caster_participant = state.participants[0]
        db = MagicMock()
        # Caster takes (reflected) damage to 0 -> their bonds end.
        CombatService._apply_warding_bond_effects_after_damage(
            db, state, caster_participant,
            target_new_hp=0, final_amount=10, is_crit=False, warding_bond_share=True,
        )
        # Both effects removed across participants.
        for p in state.participants:
            self.assertEqual(p.get("active_effects"), [])


class WardingBondBreakTests(unittest.TestCase):
    def test_remove_involving_participant(self):
        state = _state_with_bond()
        removed = remove_warding_bonds_involving_participants(state, ["cref"])
        self.assertEqual(len(removed), 2)
        for p in state.participants:
            self.assertEqual(p["active_effects"], [])

    def test_break_for_caster(self):
        state = _state_with_bond()
        break_warding_bonds_for_caster(state, "cref")
        for p in state.participants:
            self.assertEqual(p["active_effects"], [])

    def test_distance_break_over_18(self):
        state = _state_with_bond()
        state.local_distances = {"cref": {"tref": 25.0}}
        broken = break_warding_bonds_exceeding_distance(state)
        self.assertEqual(len(broken), 2)
        for p in state.participants:
            self.assertEqual(p["active_effects"], [])

    def test_distance_within_18_keeps_bond(self):
        state = _state_with_bond()
        state.local_distances = {"cref": {"tref": 9.0}}
        broken = break_warding_bonds_exceeding_distance(state)
        self.assertEqual(broken, [])
        self.assertIsNotNone(find_target_role_effect(state.participants[1]))

    def test_distance_unconfigured_keeps_bond(self):
        state = _state_with_bond()
        state.local_distances = {}
        self.assertEqual(break_warding_bonds_exceeding_distance(state), [])


class WardingBondOocTests(unittest.TestCase):
    def _spell(self):
        return SimpleNamespace(
            canonical_key="warding_bond",
            name_pt="Vínculo de Proteção",
            name_en="Warding Bond",
            duration_seconds=3600,
        )

    def test_build_ooc_effects_shape(self):
        target_effect, caster_effect = build_ooc_warding_bond_effects(
            spell=self._spell(), caster_user_id="u1", target_user_id="u2", game_time_seconds=5
        )
        # bond keyed by user ids (== player ref_ids in combat)
        self.assertEqual(target_effect["metadata"]["bond_caster_participant_id"], "u1")
        self.assertEqual(target_effect["metadata"]["bond_target_participant_id"], "u2")
        self.assertEqual(target_effect["metadata"]["bond_group"], caster_effect["metadata"]["bond_group"])
        # routing keys: target effect -> target, caster marker -> caster
        self.assertEqual(target_effect["metadata"]["target_player_user_id"], "u2")
        self.assertEqual(caster_effect["metadata"]["target_player_user_id"], "u1")
        self.assertTrue(target_effect["metadata"]["created_out_of_combat"])

    def test_clear_warding_bonds_across_session(self):
        from app.services.combat_service.persistent_effects import clear_warding_bonds_across_session

        target_effect, caster_effect = build_ooc_warding_bond_effects(
            spell=self._spell(), caster_user_id="u1", target_user_id="u2", game_time_seconds=5
        )
        caster_state = SimpleNamespace(
            player_user_id="u1", state_json={"active_spell_effects": [caster_effect]}
        )
        target_state = SimpleNamespace(
            player_user_id="u2", state_json={"active_spell_effects": [target_effect]}
        )
        db = MagicMock()
        db.exec.return_value = SimpleNamespace(all=lambda: [caster_state, target_state])
        with patch(
            "app.services.combat_service.persistent_effects.get_game_time_seconds",
            return_value=10,
        ), patch(
            "app.services.combat_service.persistent_effects.finalize_session_state_data",
            side_effect=lambda d, **k: d,
        ), patch(
            "app.services.combat_service.persistent_effects.flag_modified",
        ):
            modified = clear_warding_bonds_across_session(db, "s1", ["u1"])
        self.assertEqual(len(modified), 2)
        self.assertNotIn("active_spell_effects", caster_state.state_json)
        self.assertNotIn("active_spell_effects", target_state.state_json)


if __name__ == "__main__":
    unittest.main()
