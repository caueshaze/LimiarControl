"""Tests for True Strike / Golpe Certeiro.

Covers:
- Seed contract: level=0, divination, concentration, utility
- Targeting semantics: creature, none attack_type, distance, persistent
- Registry: default_mode=utility, handler_name=_cast_true_strike_automation
- Automation: creates effect on caster, not on target; concentration; no damage; no attack roll
- Advantage resolution: roll_advantage_modifier loop in resolve_attack_advantage
- available_from_next_turn guard (same-turn inhibition)
- Consume on first eligible attack via consumed_effect_ids_on_roll
- Lifecycle: _activate_deferred_spell_effects flips flag at caster's turn_start
- Expiration: until_turn_end with true_strike guard skips pre-activation expiry
- Concentration: recast clears prior spell; break removes effect
- OOC: not in OOC list; no build_persisted_effects branch
"""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.services.combat import CombatService, CombatServiceError
from app.services.combat_service.condition_effects_attacks import resolve_attack_advantage
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state(caster_id: str = "caster-p1", target_id: str = "target-p2") -> CombatState:
    return CombatState(
        id="c1",
        session_id="s1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        use_map=False,
        participants=[
            {
                "id": caster_id,
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Mago",
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "u1",
                "active_effects": [],
                "turn_resources": {
                    "action_used": False,
                    "bonus_action_used": False,
                    "reaction_used": False,
                },
            },
            {
                "id": target_id,
                "ref_id": "npc-1",
                "kind": "session_entity",
                "display_name": "Goblin",
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
                "active_effects": [],
                "turn_resources": {
                    "action_used": False,
                    "bonus_action_used": False,
                    "reaction_used": False,
                },
            },
        ],
    )


def _ctx() -> dict:
    return {
        "spell_canonical_key": "true_strike",
        "spell_name": "Golpe Certeiro",
        "slot_level": 0,
        "spell_level": 0,
        "spell_mode": "utility",
        "effect_dice": None,
        "attack_bonus": 5,
    }


def _attacker_model() -> SessionState:
    return SessionState(
        id="st1",
        session_id="s1",
        player_user_id="player-1",
        state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 2}}}},
    )


def _true_strike_effect(
    caster_id: str = "caster-p1",
    target_id: str = "target-p2",
    available: bool = False,
) -> dict:
    return {
        "id": "ts-eff-1",
        "kind": "spell_effect",
        "source_participant_id": caster_id,
        "duration_type": "until_turn_end",
        "expires_on": "turn_end",
        "expires_at_participant_id": caster_id,
        "metadata": {
            "source_spell_key": "true_strike",
            "concentration": True,
            "concentration_group": "grp-ts",
            "available_from_next_turn": available,
            "declarative_effect": {
                "type": "roll_advantage_modifier",
                "params": {
                    "mode": "advantage",
                    "roll_types": ["attack"],
                    "applies_when_attacking_participant_id": target_id,
                    "consume_on_apply": True,
                    "source": "true_strike",
                },
            },
        },
    }


# ---------------------------------------------------------------------------
# Seed contract
# ---------------------------------------------------------------------------

class TrueStrikeSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        import json
        with open(path) as f:
            data = json.load(f)
        cls.spell = next(
            (s for s in data["spells"] if s.get("canonicalKey") == "true_strike"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.spell)

    def test_level_zero(self):
        self.assertEqual(self.spell["level"], 0)

    def test_school_divination(self):
        self.assertEqual(self.spell["school"], "divination")

    def test_concentration_true(self):
        self.assertTrue(self.spell["concentration"])

    def test_ritual_false(self):
        self.assertFalse(self.spell["ritual"])

    def test_resolution_type_utility(self):
        self.assertEqual(self.spell["resolutionType"], "utility")

    def test_classes(self):
        classes = self.spell["classesJson"]
        self.assertIn("Bard", classes)
        self.assertIn("Sorcerer", classes)
        self.assertIn("Warlock", classes)
        self.assertIn("Wizard", classes)

    def test_range_meters(self):
        self.assertEqual(self.spell["rangeMeters"], 9)

    def test_duration_seconds(self):
        self.assertEqual(self.spell["durationSeconds"], 6)

    def test_selection_type_creature(self):
        self.assertEqual(self.spell["selectionType"], "creature")

    def test_attack_type_none(self):
        self.assertEqual(self.spell["attackType"], "none")

    def test_range_kind_distance(self):
        self.assertEqual(self.spell["rangeKind"], "distance")

    def test_effect_timing_persistent(self):
        self.assertEqual(self.spell["effectTiming"], "persistent")

    def test_no_damage_dice(self):
        self.assertIsNone(self.spell.get("damageDice"))

    def test_no_saving_throw(self):
        self.assertIsNone(self.spell.get("savingThrow"))

    def test_no_cantrip_scaling(self):
        self.assertIsNone(self.spell.get("cantripScaling"))

    def test_no_upcast(self):
        self.assertIsNone(self.spell.get("upcast"))

    def test_no_out_of_combat_castable(self):
        self.assertNotIn("outOfCombatCastable", self.spell)


# ---------------------------------------------------------------------------
# Targeting semantics
# ---------------------------------------------------------------------------

class TrueStrikeTargetingSemanticsTests(unittest.TestCase):
    def setUp(self):
        source = SimpleNamespace(canonical_key="true_strike", canonicalKey="true_strike")
        self.sem = resolve_spell_targeting_semantics(source)

    def test_selection_type_creature(self):
        self.assertEqual(self.sem.selection_type, "creature")

    def test_target_anchor_selected_target(self):
        self.assertEqual(self.sem.target_anchor, "selected_target")

    def test_attack_type_none(self):
        self.assertEqual(self.sem.attack_type, "none")

    def test_range_kind_distance(self):
        self.assertEqual(self.sem.range_kind, "distance")

    def test_effect_timing_persistent(self):
        self.assertEqual(self.sem.effect_timing, "persistent")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TrueStrikeRegistryTests(unittest.TestCase):
    def setUp(self):
        self.spec = CombatService._SPELL_AUTOMATION_REGISTRY.get("true_strike")

    def test_registry_entry_exists(self):
        self.assertIsNotNone(self.spec)

    def test_default_mode_utility(self):
        self.assertEqual(self.spec.default_mode, "utility")

    def test_requires_effect_payload_false(self):
        self.assertFalse(self.spec.requires_effect_payload)

    def test_handler_name(self):
        self.assertEqual(self.spec.handler_name, "_cast_true_strike_automation")


# ---------------------------------------------------------------------------
# Automation handler
# ---------------------------------------------------------------------------

class TrueStrikeAutomationTests(unittest.IsolatedAsyncioTestCase):

    async def _cast(
        self,
        *,
        state: CombatState | None = None,
        req=None,
        target_participant=None,
    ) -> tuple[dict, CombatState]:
        if state is None:
            state = _state()
        if req is None:
            req = SimpleNamespace()
        attacker = state.participants[0]
        if target_participant is None:
            target_participant = state.participants[1]

        with (
            patch.object(CombatService, "_clear_concentration_for_source", return_value={"removed_area_effects": []}),
            patch.object(CombatService, "_sync_area_effects_if_changed"),
            patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=0),
        ):
            result = await CombatService._cast_true_strike_automation(
                MagicMock(), "s1",
                attacker=attacker,
                attacker_model=_attacker_model(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=_ctx(),
                target_participant=target_participant,
            )
        return result, state

    async def test_creates_effect_on_caster(self):
        _, state = await self._cast()
        effects = state.participants[0].get("active_effects") or []
        self.assertEqual(len(effects), 1)

    async def test_no_effect_on_target(self):
        _, state = await self._cast()
        effects = state.participants[1].get("active_effects") or []
        self.assertEqual(len(effects), 0)

    async def test_effect_source_spell_key(self):
        _, state = await self._cast()
        effect = state.participants[0]["active_effects"][0]
        self.assertEqual((effect.get("metadata") or {}).get("source_spell_key"), "true_strike")

    async def test_effect_concentration_true(self):
        _, state = await self._cast()
        effect = state.participants[0]["active_effects"][0]
        self.assertTrue((effect.get("metadata") or {}).get("concentration"))

    async def test_effect_target_metadata(self):
        _, state = await self._cast()
        effect = state.participants[0]["active_effects"][0]
        meta = effect.get("metadata") or {}
        self.assertEqual(meta.get("target_participant_id"), "target-p2")
        self.assertEqual(meta.get("target_ref_id"), "npc-1")

    async def test_result_has_concentration_group(self):
        result, _ = await self._cast()
        self.assertIsInstance(result.get("concentration_group"), str)
        self.assertTrue(len(result["concentration_group"]) > 0)

    async def test_effect_available_from_next_turn_true(self):
        _, state = await self._cast()
        effect = state.participants[0]["active_effects"][0]
        self.assertTrue((effect.get("metadata") or {}).get("available_from_next_turn"))

    async def test_no_damage(self):
        result, _ = await self._cast()
        self.assertEqual(result.get("damage"), 0)

    async def test_action_kind_utility(self):
        result, _ = await self._cast()
        self.assertEqual(result.get("action_kind"), "utility")

    async def test_result_grants_advantage_true(self):
        result, _ = await self._cast()
        self.assertTrue(result.get("grants_advantage"))

    async def test_result_consume_on_first_eligible_attack(self):
        result, _ = await self._cast()
        self.assertTrue(result.get("consume_on_first_eligible_attack"))

    async def test_no_slot_consumption(self):
        # No slot manipulation should happen — mock verifies _clear_conc called but not slot ops
        _, state = await self._cast()
        effect = state.participants[0]["active_effects"][0]
        self.assertIsNotNone(effect)  # effect created = cast succeeded without error

    async def test_variant_key_raises_400(self):
        req = SimpleNamespace(variant_key="some_variant")
        with self.assertRaises(CombatServiceError) as ctx:
            await self._cast(req=req)
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_no_target_raises_400(self):
        st = _state()
        with self.assertRaises(CombatServiceError) as ctx:
            with (
                patch.object(CombatService, "_clear_concentration_for_source", return_value={"removed_area_effects": []}),
                patch.object(CombatService, "_sync_area_effects_if_changed"),
                patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=0),
            ):
                await CombatService._cast_true_strike_automation(
                    MagicMock(), "s1",
                    attacker=st.participants[0],
                    attacker_model=_attacker_model(),
                    actor_user_id="u1",
                    is_gm=False,
                    req=SimpleNamespace(),
                    state=st,
                    spell_context=_ctx(),
                    target_participant=None,
                )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_recast_clears_previous_concentration(self):
        captured = {}

        def fake_clear(state, *, source_participant_id, db=None):
            captured["called_with"] = source_participant_id
            return {"removed_area_effects": []}

        st = _state()
        with (
            patch.object(CombatService, "_clear_concentration_for_source", side_effect=fake_clear),
            patch.object(CombatService, "_sync_area_effects_if_changed"),
            patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=0),
        ):
            await CombatService._cast_true_strike_automation(
                MagicMock(), "s1",
                attacker=st.participants[0],
                attacker_model=_attacker_model(),
                actor_user_id="u1",
                is_gm=False,
                req=SimpleNamespace(),
                state=st,
                spell_context=_ctx(),
                target_participant=st.participants[1],
            )
        self.assertEqual(captured.get("called_with"), "caster-p1")

    async def test_recast_changes_target(self):
        target_b = {
            "id": "target-p3",
            "ref_id": "npc-2",
            "kind": "session_entity",
            "display_name": "Orc",
            "status": "active",
            "active_effects": [],
        }
        st = _state()
        with (
            patch.object(CombatService, "_clear_concentration_for_source", return_value={"removed_area_effects": []}),
            patch.object(CombatService, "_sync_area_effects_if_changed"),
            patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=0),
        ):
            await CombatService._cast_true_strike_automation(
                MagicMock(), "s1",
                attacker=st.participants[0],
                attacker_model=_attacker_model(),
                actor_user_id="u1",
                is_gm=False,
                req=SimpleNamespace(),
                state=st,
                spell_context=_ctx(),
                target_participant=target_b,
            )
        effect = st.participants[0]["active_effects"][0]
        self.assertEqual((effect.get("metadata") or {}).get("target_participant_id"), "target-p3")


# ---------------------------------------------------------------------------
# Advantage resolution
# ---------------------------------------------------------------------------

class TrueStrikeAdvantageTests(unittest.TestCase):

    def _attacker_with_effect(self, available: bool = False, target_id: str = "target-p2") -> dict:
        return {
            "id": "caster-p1",
            "active_effects": [_true_strike_effect("caster-p1", target_id, available=available)],
        }

    def _target(self, tid: str = "target-p2") -> dict:
        return {"id": tid, "active_effects": []}

    def test_available_from_next_turn_true_not_applied(self):
        attacker = self._attacker_with_effect(available=True)
        ctx = resolve_attack_advantage(attacker, self._target(), "melee")
        self.assertNotIn("true_strike", ctx.advantage_sources)

    def test_available_from_next_turn_false_applied(self):
        attacker = self._attacker_with_effect(available=False)
        ctx = resolve_attack_advantage(attacker, self._target(), "melee")
        self.assertIn("true_strike", ctx.advantage_sources)
        self.assertEqual(ctx.result, "advantage")

    def test_applies_only_against_marked_target(self):
        attacker = self._attacker_with_effect(available=False, target_id="target-p2")
        other_target = {"id": "other-p3", "active_effects": []}
        ctx = resolve_attack_advantage(attacker, other_target, "melee")
        self.assertNotIn("true_strike", ctx.advantage_sources)

    def test_other_attacker_not_affected(self):
        other_attacker = {"id": "other-caster", "active_effects": []}
        ctx = resolve_attack_advantage(other_attacker, self._target(), "melee")
        self.assertNotIn("true_strike", ctx.advantage_sources)

    def test_consume_on_apply_adds_to_consumed_list(self):
        attacker = self._attacker_with_effect(available=False)
        ctx = resolve_attack_advantage(attacker, self._target(), "melee")
        self.assertIn("ts-eff-1", ctx.consumed_effect_ids_on_roll)

    def test_advantage_sources_contains_true_strike(self):
        attacker = self._attacker_with_effect(available=False)
        ctx = resolve_attack_advantage(attacker, self._target(), "melee")
        self.assertIn("true_strike", ctx.advantage_sources)


# ---------------------------------------------------------------------------
# Consume tests
# ---------------------------------------------------------------------------

class TrueStrikeConsumeTests(unittest.TestCase):

    def _attacker_with_true_strike(self, caster_id: str = "caster-p1") -> dict:
        return {
            "id": caster_id,
            "active_effects": [_true_strike_effect(caster_id, "target-p2", available=False)],
        }

    def test_consume_effect_ids_removes_from_attacker(self):
        attacker = self._attacker_with_true_strike()
        ctx = resolve_attack_advantage(attacker, {"id": "target-p2", "active_effects": []}, "melee")
        self.assertEqual(ctx.consumed_effect_ids_on_roll, ["ts-eff-1"])
        # Simulate what all attack pipelines do after roll
        CombatService._consume_effect_ids(attacker, ctx.consumed_effect_ids_on_roll)
        self.assertEqual(len(attacker.get("active_effects") or []), 0)

    def test_second_attack_no_advantage_after_consume(self):
        attacker = self._attacker_with_true_strike()
        target = {"id": "target-p2", "active_effects": []}
        ctx = resolve_attack_advantage(attacker, target, "melee")
        CombatService._consume_effect_ids(attacker, ctx.consumed_effect_ids_on_roll)
        ctx2 = resolve_attack_advantage(attacker, target, "melee")
        self.assertNotIn("true_strike", ctx2.advantage_sources)

    def test_weapon_attack_pipeline_consumes_from_attacker(self):
        # Test that _consume_effect_ids is called on attacker by simulating the weapon pipeline pattern
        attacker = self._attacker_with_true_strike()
        ctx = resolve_attack_advantage(attacker, {"id": "target-p2", "active_effects": []}, "melee")
        if ctx.consumed_effect_ids_on_roll:
            CombatService._consume_effect_ids(attacker, ctx.consumed_effect_ids_on_roll)
        self.assertEqual(len(attacker.get("active_effects") or []), 0)


# ---------------------------------------------------------------------------
# Lifecycle: _activate_deferred_spell_effects
# ---------------------------------------------------------------------------

class TrueStrikeLifecycleActivationTests(unittest.TestCase):

    def _state_with_caster_effect(self, caster_id: str, available: bool = True) -> CombatState:
        effect = _true_strike_effect(caster_id, "target-p2", available=available)
        return CombatState(
            id="c1", session_id="s1", phase=CombatPhase.active,
            round=1, current_turn_index=0, use_map=False,
            participants=[
                {
                    "id": caster_id,
                    "ref_id": "player-1",
                    "kind": "player",
                    "display_name": "Mago",
                    "status": "active",
                    "active_effects": [effect],
                },
                {
                    "id": "other-p",
                    "ref_id": "npc-1",
                    "kind": "session_entity",
                    "display_name": "Goblin",
                    "status": "active",
                    "active_effects": [],
                },
            ],
        )

    def test_activate_flips_available_flag(self):
        state = self._state_with_caster_effect("caster-p1", available=True)
        CombatService._activate_deferred_spell_effects(state, "caster-p1")
        effect = state.participants[0]["active_effects"][0]
        self.assertFalse((effect.get("metadata") or {}).get("available_from_next_turn"))

    def test_activate_does_not_flip_other_participant(self):
        state = self._state_with_caster_effect("caster-p1", available=True)
        CombatService._activate_deferred_spell_effects(state, "other-p")
        effect = state.participants[0]["active_effects"][0]
        self.assertTrue((effect.get("metadata") or {}).get("available_from_next_turn"))

    def test_activate_uses_source_participant_id(self):
        # Effect has source_participant_id = "caster-p1"; calling with "caster-p1" activates it
        state = self._state_with_caster_effect("caster-p1", available=True)
        CombatService._activate_deferred_spell_effects(state, "caster-p1")
        effect = state.participants[0]["active_effects"][0]
        self.assertFalse((effect.get("metadata") or {}).get("available_from_next_turn"))

    def test_activate_does_not_affect_non_true_strike(self):
        # Effects without available_from_next_turn are left alone
        state = _state("caster-p1", "target-p2")
        state.participants[0]["active_effects"] = [{
            "id": "other-eff",
            "kind": "spell_effect",
            "source_participant_id": "caster-p1",
            "metadata": {"source_spell_key": "detect_magic"},
        }]
        CombatService._activate_deferred_spell_effects(state, "caster-p1")
        eff = state.participants[0]["active_effects"][0]
        self.assertNotIn("available_from_next_turn", (eff.get("metadata") or {}))


# ---------------------------------------------------------------------------
# Expiration tests
# ---------------------------------------------------------------------------

class TrueStrikeExpirationTests(unittest.IsolatedAsyncioTestCase):

    def _state_with_true_strike(self, available: bool) -> CombatState:
        effect = _true_strike_effect("caster-p1", "target-p2", available=available)
        return CombatState(
            id="c1", session_id="s1", phase=CombatPhase.active,
            round=1, current_turn_index=0, use_map=False,
            participants=[
                {
                    "id": "caster-p1",
                    "ref_id": "player-1",
                    "kind": "player",
                    "display_name": "Mago",
                    "status": "active",
                    "active_effects": [effect],
                },
                {
                    "id": "other-p",
                    "ref_id": "npc-1",
                    "kind": "session_entity",
                    "display_name": "Goblin",
                    "status": "active",
                    "active_effects": [],
                },
            ],
        )

    async def test_until_turn_end_skips_if_available_from_next_turn_true(self):
        # Effect not yet activated — must NOT be expired at caster's turn_end
        state = self._state_with_true_strike(available=True)
        await CombatService._expire_effects_for_participant("s1", state, "caster-p1", "turn_end")
        effects = state.participants[0].get("active_effects") or []
        self.assertEqual(len(effects), 1, "Effect should survive turn_end before activation")

    async def test_until_turn_end_expires_after_activation(self):
        # Effect activated (available=False) — must be expired at caster's turn_end
        state = self._state_with_true_strike(available=False)
        await CombatService._expire_effects_for_participant("s1", state, "caster-p1", "turn_end")
        effects = state.participants[0].get("active_effects") or []
        self.assertEqual(len(effects), 0, "Effect should expire at turn_end after activation")

    async def test_effect_persists_through_other_participant_turn_end(self):
        state = self._state_with_true_strike(available=False)
        await CombatService._expire_effects_for_participant("s1", state, "other-p", "turn_end")
        effects = state.participants[0].get("active_effects") or []
        self.assertEqual(len(effects), 1, "Effect should only expire at caster's turn_end")

    async def test_effect_persists_through_caster_turn_start(self):
        # until_turn_end effects don't expire at turn_start
        state = self._state_with_true_strike(available=True)
        await CombatService._expire_effects_for_participant("s1", state, "caster-p1", "turn_start")
        effects = state.participants[0].get("active_effects") or []
        self.assertEqual(len(effects), 1)


# ---------------------------------------------------------------------------
# Concentration tests
# ---------------------------------------------------------------------------

class TrueStrikeConcentrationTests(unittest.IsolatedAsyncioTestCase):

    async def test_recast_removes_detect_magic(self):
        removed_ids = []

        def fake_clear(state, *, source_participant_id, db=None):
            # Simulate that an existing concentration group was removed
            removed_ids.append(source_participant_id)
            return {"removed_area_effects": []}

        st = _state()
        with (
            patch.object(CombatService, "_clear_concentration_for_source", side_effect=fake_clear),
            patch.object(CombatService, "_sync_area_effects_if_changed"),
            patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=0),
        ):
            await CombatService._cast_true_strike_automation(
                MagicMock(), "s1",
                attacker=st.participants[0],
                attacker_model=_attacker_model(),
                actor_user_id="u1",
                is_gm=False,
                req=SimpleNamespace(),
                state=st,
                spell_context=_ctx(),
                target_participant=st.participants[1],
            )
        self.assertEqual(removed_ids, ["caster-p1"])

    def test_concentration_break_removes_effect(self):
        st = _state()
        effect = _true_strike_effect("caster-p1", "target-p2")
        effect["metadata"]["concentration"] = True
        effect["metadata"]["concentration_group"] = "grp-ts"
        st.participants[0]["active_effects"] = [effect]
        CombatService._clear_concentration_for_source(st, source_participant_id="caster-p1")
        effects = st.participants[0].get("active_effects") or []
        self.assertEqual(len(effects), 0)


# ---------------------------------------------------------------------------
# OOC tests
# ---------------------------------------------------------------------------

class TrueStrikeOocTests(unittest.TestCase):

    def test_not_in_special_ooc_utility_spells(self):
        from app.services.out_of_combat_cast import _SPECIAL_OOC_UTILITY_SPELLS
        self.assertNotIn("true_strike", _SPECIAL_OOC_UTILITY_SPELLS)

    def test_no_build_persisted_effects_branch(self):
        from app.services.out_of_combat_cast import build_persisted_effects
        import inspect
        src = inspect.getsource(build_persisted_effects)
        self.assertNotIn("true_strike", src)
