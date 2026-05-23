from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.schemas.base_spell import BaseSpellCreate
from app.schemas.combat import CombatCastSpellRequest
from app.schemas.roll import RollResult
from app.services.combat import CombatService


class HoldPersonSeedTests(unittest.TestCase):
    def test_hold_person_has_apply_condition_and_repeat_save(self):
        import json
        payload = json.loads(open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"), encoding="utf-8").read())
        raw_spell = next(entry for entry in payload["spells"] if entry["canonicalKey"] == "hold_person")
        spell = BaseSpellCreate.model_validate(raw_spell)
        self.assertEqual(spell.savingThrow, "WIS")
        self.assertEqual(spell.resolutionType, "control")
        self.assertTrue(spell.concentration)
        effects = raw_spell.get("effects") or []
        self.assertTrue(effects)
        effect = effects[0]
        self.assertEqual(effect.get("type"), "apply_condition")
        self.assertEqual((effect.get("params") or {}).get("condition"), "paralyzed")
        self.assertEqual((effect.get("repeat_save") or {}).get("timing"), "target_turn_end")


class HoldPersonRepeatSaveTests(unittest.IsolatedAsyncioTestCase):
    def _state(self):
        return CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {"id": "p1", "ref_id": "caster", "kind": "player", "display_name": "Lia", "status": "active", "team": "players", "actor_user_id": "u1", "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False}},
                {"id": "e1", "ref_id": "enemy", "kind": "session_entity", "display_name": "Bandido", "status": "active", "team": "enemies", "turn_resources": {}, "active_effects": []},
            ],
        )

    async def test_repeat_save_success_removes_only_matching_effect_id(self):
        state = self._state()
        state.current_turn_index = 1  # outgoing is the affected target
        state.participants[1]["active_effects"] = [
            {"id": "hold-1", "kind": "condition", "condition_type": "paralyzed", "source_participant_id": "p1", "metadata": {"source_spell_key": "hold_person", "concentration": True, "concentration_group": "grp-1", "repeat_save": {"timing": "target_turn_end", "ability": "wisdom", "dc": 14, "ends_on_success": True}}},
            {"id": "other-1", "kind": "condition", "condition_type": "paralyzed", "source_participant_id": "x", "metadata": {"source_spell_key": "other_spell"}},
        ]
        roll = RollResult(event_id="r1", roll_type="save", actor_kind="session_entity", actor_ref_id="enemy", actor_display_name="Bandido", rolls=[15], selected_roll=15, advantage_mode="normal", modifier_used=0, override_used=False, formula="1d20", total=15, ability="wisdom", dc=14, success=True, timestamp=datetime.now(timezone.utc))

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat_service.lifecycle_turns.resolve_saving_throw", return_value=roll),
            patch("app.services.combat.CombatService._build_roll_actor_stats_for_save", return_value=MagicMock()),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_log", new_callable=AsyncMock),
        ):
            await CombatService.next_turn(MagicMock(), "s1", "u1", True)

        remaining = state.participants[1]["active_effects"]
        ids = {e["id"] for e in remaining}
        self.assertNotIn("hold-1", ids)
        self.assertIn("other-1", ids)

    async def test_turn_end_of_other_participant_does_not_trigger(self):
        state = self._state()
        state.current_turn_index = 0  # outgoing is caster, not enemy
        state.participants[1]["active_effects"] = [
            {"id": "hold-1", "kind": "condition", "condition_type": "paralyzed", "source_participant_id": "p1", "metadata": {"source_spell_key": "hold_person", "repeat_save": {"timing": "target_turn_end", "ability": "wisdom", "dc": 14, "ends_on_success": True}}},
        ]

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat_service.lifecycle_turns.resolve_saving_throw") as save_roll,
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_log", new_callable=AsyncMock),
        ):
            await CombatService.next_turn(MagicMock(), "s1", "u1", False)
        save_roll.assert_not_called()


class HoldPersonCastFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_initial_save_success_consumes_slot_without_orphan_concentration(self):
        state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {"id": "p1", "ref_id": "caster", "kind": "player", "display_name": "Lia", "status": "active", "team": "players", "actor_user_id": "u1", "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False}, "active_effects": []},
                {"id": "e1", "ref_id": "enemy", "kind": "session_entity", "display_name": "Bandido", "status": "active", "team": "enemies", "active_effects": []},
            ],
        )
        attacker_state = MagicMock()
        attacker_state.state_json = {
            "spellcasting": {
                "slots": {"2": {"used": 0, "max": 2}},
                "spells": [{"canonicalKey": "hold_person", "name": "Hold Person", "prepared": True, "level": 2}],
            }
        }
        req = CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="hold_person",
            target_ref_id="enemy",
        )
        spell_context = {
            "spell_name": "Hold Person",
            "spell_canonical_key": "hold_person",
            "spell_mode": "saving_throw",
            "selection_type": "creature",
            "slot_level": 2,
            "action_cost": "action",
            "source_kind": "spell",
            "effect_kind": "damage",
            "effect_dice": None,
            "effect_bonus": 0,
            "save_ability": "wisdom",
            "save_dc": 14,
            "save_success_outcome": "none",
            "target_type": "ranged",
            "range_kind": "distance",
            "attack_type": "none",
            "requires_target_sight": True,
            "requires_target_effect": True,
            "effects": [{"type": "apply_condition", "target": "selected_target", "params": {"condition": "paralyzed"}, "repeat_save": {"timing": "target_turn_end", "ability": "wisdom", "ends_on_success": True}}],
            "concentration": True,
            "concentration_group": None,
        }
        roll = RollResult(event_id="r1", roll_type="save", actor_kind="session_entity", actor_ref_id="enemy", actor_display_name="Bandido", rolls=[18], selected_roll=18, advantage_mode="normal", modifier_used=0, override_used=False, formula="1d20", total=18, ability="wisdom", dc=14, success=True, timestamp=datetime.now(timezone.utc))
        targeting_result = MagicMock(is_valid=True, validated_primary_target_ref_id="enemy", spatial_metadata=MagicMock(cover=None))

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service", return_value=MagicMock(validate=MagicMock(return_value=targeting_result))),
            patch("app.services.combat_service.spells.cast_target.resolve_saving_throw", return_value=roll),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock),
        ):
            result = await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)

        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["2"]["used"], 1)
        self.assertTrue(result["is_saved"])
        self.assertEqual(state.participants[1].get("active_effects"), [])
        self.assertIsNone(result.get("concentration_group"))
        self.assertEqual(state.participants[0].get("active_effects"), [])

    async def test_breaking_concentration_removes_effect_and_prevents_future_repeat_save(self):
        state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=1,
            participants=[
                {"id": "p1", "ref_id": "caster", "kind": "player", "display_name": "Lia", "status": "active", "team": "players", "actor_user_id": "u1", "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False}, "active_effects": []},
                {"id": "e1", "ref_id": "enemy", "kind": "session_entity", "display_name": "Bandido", "status": "active", "team": "enemies", "active_effects": [
                    {"id": "hold-1", "kind": "condition", "condition_type": "paralyzed", "source_participant_id": "p1", "metadata": {"source_spell_key": "hold_person", "concentration": True, "concentration_group": "grp-1", "repeat_save": {"timing": "target_turn_end", "ability": "wisdom", "dc": 14, "ends_on_success": True}}}
                ]},
            ],
        )
        CombatService._clear_concentration_for_source(state, source_participant_id="p1")
        self.assertEqual(state.participants[1].get("active_effects"), [])

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat_service.lifecycle_turns.resolve_saving_throw") as save_roll,
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_log", new_callable=AsyncMock) as emit_log,
        ):
            await CombatService.next_turn(MagicMock(), "s1", "u1", True)
        save_roll.assert_not_called()
        repeat_logs = [
            c.args[1]
            for c in emit_log.await_args_list
            if isinstance(c.args, tuple)
            and len(c.args) > 1
            and isinstance(c.args[1], dict)
            and c.args[1].get("source") == "repeat_save_resolve"
        ]
        self.assertEqual(repeat_logs, [])

    async def test_multi_target_one_fails_one_saves_applies_only_one_effect(self):
        state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {"id": "p1", "ref_id": "caster", "kind": "player", "display_name": "Lia", "status": "active", "team": "players", "actor_user_id": "u1", "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False}, "active_effects": []},
                {"id": "e1", "ref_id": "enemy-a", "kind": "session_entity", "display_name": "Bandido A", "status": "active", "team": "enemies", "active_effects": []},
                {"id": "e2", "ref_id": "enemy-b", "kind": "session_entity", "display_name": "Bandido B", "status": "active", "team": "enemies", "active_effects": []},
            ],
        )
        attacker_state = MagicMock()
        attacker_state.state_json = {"spellcasting": {"slots": {"3": {"used": 0, "max": 2}}, "spells": [{"canonicalKey": "hold_person", "name": "Hold Person", "prepared": True, "level": 2}]}}
        req = CombatCastSpellRequest(actor_participant_id="p1", spell_canonical_key="hold_person", target_ref_ids=["enemy-a", "enemy-b"], slot_level=3)
        spell_context = {"spell_name": "Hold Person", "spell_canonical_key": "hold_person", "spell_mode": "saving_throw", "selection_type": "creature", "slot_level": 3, "action_cost": "action", "source_kind": "spell", "effect_kind": "damage", "effect_dice": None, "effect_bonus": 0, "save_ability": "wisdom", "save_dc": 14, "save_success_outcome": "none", "target_type": "ranged", "range_kind": "distance", "attack_type": "none", "requires_target_sight": True, "requires_target_effect": True, "effects": [{"type": "apply_condition", "target": "selected_target", "params": {"condition": "paralyzed"}, "repeat_save": {"timing": "target_turn_end", "ability": "wisdom", "ends_on_success": True}}], "concentration": True, "max_targets": 2}
        roll_fail = RollResult(event_id="r1", roll_type="save", actor_kind="session_entity", actor_ref_id="enemy-a", actor_display_name="Bandido A", rolls=[5], selected_roll=5, advantage_mode="normal", modifier_used=0, override_used=False, formula="1d20", total=5, ability="wisdom", dc=14, success=False, timestamp=datetime.now(timezone.utc))
        roll_pass = RollResult(event_id="r2", roll_type="save", actor_kind="session_entity", actor_ref_id="enemy-b", actor_display_name="Bandido B", rolls=[18], selected_roll=18, advantage_mode="normal", modifier_used=0, override_used=False, formula="1d20", total=18, ability="wisdom", dc=14, success=True, timestamp=datetime.now(timezone.utc))
        targeting_result = MagicMock(is_valid=True, validated_primary_target_ref_id="enemy-a", spatial_metadata=MagicMock(cover=None))

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service", return_value=MagicMock(validate=MagicMock(return_value=targeting_result))),
            patch("app.services.combat_service.spells.cast_target.resolve_saving_throw", side_effect=[roll_fail, roll_pass]),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock),
        ):
            result = await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)
        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["3"]["used"], 1)
        self.assertEqual(len(state.participants[1].get("active_effects") or []), 1)
        self.assertEqual(state.participants[2].get("active_effects") or [], [])
        self.assertIsNotNone(result.get("concentration_group"))

    async def test_multi_target_two_fails_share_concentration_group_and_distinct_effect_ids(self):
        state = CombatState(
            id="c1", session_id="s1", phase=CombatPhase.active, round=1, current_turn_index=0,
            participants=[
                {"id": "p1", "ref_id": "caster", "kind": "player", "display_name": "Lia", "status": "active", "team": "players", "actor_user_id": "u1", "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False}, "active_effects": []},
                {"id": "e1", "ref_id": "enemy-a", "kind": "session_entity", "display_name": "Bandido A", "status": "active", "team": "enemies", "active_effects": []},
                {"id": "e2", "ref_id": "enemy-b", "kind": "session_entity", "display_name": "Bandido B", "status": "active", "team": "enemies", "active_effects": []},
            ],
        )
        attacker_state = MagicMock()
        attacker_state.state_json = {"spellcasting": {"slots": {"3": {"used": 0, "max": 2}}, "spells": [{"canonicalKey": "hold_person", "name": "Hold Person", "prepared": True, "level": 2}]}}
        req = CombatCastSpellRequest(actor_participant_id="p1", spell_canonical_key="hold_person", target_ref_ids=["enemy-a", "enemy-b"], slot_level=3)
        spell_context = {"spell_name": "Hold Person", "spell_canonical_key": "hold_person", "spell_mode": "saving_throw", "selection_type": "creature", "slot_level": 3, "action_cost": "action", "source_kind": "spell", "effect_kind": "damage", "effect_dice": None, "effect_bonus": 0, "save_ability": "wisdom", "save_dc": 14, "save_success_outcome": "none", "target_type": "ranged", "range_kind": "distance", "attack_type": "none", "requires_target_sight": True, "requires_target_effect": True, "effects": [{"type": "apply_condition", "target": "selected_target", "params": {"condition": "paralyzed"}, "repeat_save": {"timing": "target_turn_end", "ability": "wisdom", "ends_on_success": True}}], "concentration": True, "max_targets": 2}
        roll_fail_a = RollResult(event_id="r1", roll_type="save", actor_kind="session_entity", actor_ref_id="enemy-a", actor_display_name="Bandido A", rolls=[4], selected_roll=4, advantage_mode="normal", modifier_used=0, override_used=False, formula="1d20", total=4, ability="wisdom", dc=14, success=False, timestamp=datetime.now(timezone.utc))
        roll_fail_b = RollResult(event_id="r2", roll_type="save", actor_kind="session_entity", actor_ref_id="enemy-b", actor_display_name="Bandido B", rolls=[6], selected_roll=6, advantage_mode="normal", modifier_used=0, override_used=False, formula="1d20", total=6, ability="wisdom", dc=14, success=False, timestamp=datetime.now(timezone.utc))
        targeting_result = MagicMock(is_valid=True, validated_primary_target_ref_id="enemy-a", spatial_metadata=MagicMock(cover=None))
        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service", return_value=MagicMock(validate=MagicMock(return_value=targeting_result))),
            patch("app.services.combat_service.spells.cast_target.resolve_saving_throw", side_effect=[roll_fail_a, roll_fail_b]),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock),
        ):
            result = await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)
        eff_a = state.participants[1].get("active_effects") or []
        eff_b = state.participants[2].get("active_effects") or []
        self.assertEqual(len(eff_a), 1)
        self.assertEqual(len(eff_b), 1)
        self.assertNotEqual(eff_a[0].get("id"), eff_b[0].get("id"))
        group_a = (eff_a[0].get("metadata") or {}).get("concentration_group")
        group_b = (eff_b[0].get("metadata") or {}).get("concentration_group")
        self.assertEqual(group_a, group_b)
        self.assertEqual(result.get("concentration_group"), group_a)

    async def test_multi_target_repeat_save_removes_one_then_other_and_clears_concentration(self):
        state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=1,
            participants=[
                {"id": "p1", "ref_id": "caster", "kind": "player", "display_name": "Lia", "status": "active", "team": "players", "actor_user_id": "u1", "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False}},
                {"id": "e1", "ref_id": "enemy", "kind": "session_entity", "display_name": "Bandido", "status": "active", "team": "enemies", "turn_resources": {}, "active_effects": []},
                {"id": "e2", "ref_id": "enemy-b", "kind": "session_entity", "display_name": "Bandido B", "status": "active", "team": "enemies", "turn_resources": {}, "active_effects": []},
            ],
        )
        state.participants[1]["active_effects"] = [{"id": "hold-a", "kind": "condition", "condition_type": "paralyzed", "source_participant_id": "p1", "metadata": {"source_spell_key": "hold_person", "concentration": True, "concentration_group": "grp-shared", "repeat_save": {"timing": "target_turn_end", "ability": "wisdom", "dc": 14, "ends_on_success": True}}}]
        state.participants[2]["active_effects"] = [{"id": "hold-b", "kind": "condition", "condition_type": "paralyzed", "source_participant_id": "p1", "metadata": {"source_spell_key": "hold_person", "concentration": True, "concentration_group": "grp-shared", "repeat_save": {"timing": "target_turn_end", "ability": "wisdom", "dc": 14, "ends_on_success": True}}}]
        roll_ok_a = RollResult(event_id="ra", roll_type="save", actor_kind="session_entity", actor_ref_id="enemy", actor_display_name="Bandido", rolls=[15], selected_roll=15, advantage_mode="normal", modifier_used=0, override_used=False, formula="1d20", total=15, ability="wisdom", dc=14, success=True, timestamp=datetime.now(timezone.utc))
        roll_ok_b = RollResult(event_id="rb", roll_type="save", actor_kind="session_entity", actor_ref_id="enemy-b", actor_display_name="Bandido B", rolls=[16], selected_roll=16, advantage_mode="normal", modifier_used=0, override_used=False, formula="1d20", total=16, ability="wisdom", dc=14, success=True, timestamp=datetime.now(timezone.utc))
        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat_service.lifecycle_turns.resolve_saving_throw", side_effect=[roll_ok_a, roll_ok_b]),
            patch("app.services.combat.CombatService._build_roll_actor_stats_for_save", return_value=MagicMock()),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_log", new_callable=AsyncMock),
        ):
            state.current_turn_index = 1
            await CombatService.next_turn(MagicMock(), "s1", "u1", True)
            self.assertEqual(state.participants[1].get("active_effects"), [])
            self.assertEqual(len(state.participants[2].get("active_effects") or []), 1)
            state.current_turn_index = 2
            await CombatService.next_turn(MagicMock(), "s1", "u1", True)
            self.assertEqual(state.participants[2].get("active_effects"), [])

    async def test_multi_target_spatial_invalid_is_atomic_without_slot_consumption(self):
        state = CombatState(
            id="c1", session_id="s1", phase=CombatPhase.active, round=1, current_turn_index=0,
            participants=[
                {"id": "p1", "ref_id": "caster", "kind": "player", "display_name": "Lia", "status": "active", "team": "players", "actor_user_id": "u1", "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False}, "active_effects": []},
                {"id": "e1", "ref_id": "enemy-a", "kind": "session_entity", "display_name": "Bandido A", "status": "active", "team": "enemies", "active_effects": []},
                {"id": "e2", "ref_id": "enemy-b", "kind": "session_entity", "display_name": "Bandido B", "status": "active", "team": "enemies", "active_effects": []},
            ],
        )
        attacker_state = MagicMock()
        attacker_state.state_json = {"spellcasting": {"slots": {"3": {"used": 0, "max": 2}}, "spells": [{"canonicalKey": "hold_person", "name": "Hold Person", "prepared": True, "level": 2}]}}
        req = CombatCastSpellRequest(actor_participant_id="p1", spell_canonical_key="hold_person", target_ref_ids=["enemy-a", "enemy-b"], slot_level=3)
        spell_context = {"spell_name": "Hold Person", "spell_canonical_key": "hold_person", "spell_mode": "saving_throw", "selection_type": "creature", "slot_level": 3, "action_cost": "action", "source_kind": "spell", "effect_kind": "damage", "effect_dice": None, "effect_bonus": 0, "save_ability": "wisdom", "save_dc": 14, "save_success_outcome": "none", "target_type": "ranged", "range_kind": "distance", "attack_type": "none", "requires_target_sight": True, "requires_target_effect": True, "effects": [{"type": "apply_condition", "target": "selected_target", "params": {"condition": "paralyzed"}, "repeat_save": {"timing": "target_turn_end", "ability": "wisdom", "ends_on_success": True}}], "concentration": True, "max_targets": 2}
        valid_targeting = MagicMock(is_valid=True, validated_primary_target_ref_id="enemy-a", spatial_metadata=MagicMock(cover=None))
        invalid_targeting = MagicMock(is_valid=False, diagnostics=MagicMock(primary_failure=MagicMock(return_value="target_out_of_reach")), failure_reason="Target out of range")
        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service", return_value=MagicMock(validate=MagicMock(side_effect=[valid_targeting, invalid_targeting]))),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock) as emit_log,
        ):
            with self.assertRaises(Exception):
                await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)
        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["3"]["used"], 0)
        self.assertEqual(state.participants[1].get("active_effects") or [], [])
        self.assertEqual(state.participants[2].get("active_effects") or [], [])
        success_logs = [c for c in emit_log.await_args_list if "conjurou Hold Person" in ((c.args[4] or {}).get("message", "") if len(c.args) > 4 else "")]
        self.assertEqual(success_logs, [])

    async def test_hold_person_single_target_non_humanoid_known_fails_without_consuming_slot(self):
        state = CombatState(
            id="c1", session_id="s1", phase=CombatPhase.active, round=1, current_turn_index=0,
            participants=[
                {"id": "p1", "ref_id": "caster", "kind": "player", "display_name": "Lia", "status": "active", "team": "players", "actor_user_id": "u1", "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False}, "active_effects": []},
                {"id": "e1", "ref_id": "enemy-a", "kind": "session_entity", "display_name": "Bandido A", "status": "active", "team": "enemies", "active_effects": []},
            ],
        )
        attacker_state = MagicMock()
        attacker_state.state_json = {"spellcasting": {"slots": {"2": {"used": 0, "max": 2}}, "spells": [{"canonicalKey": "hold_person", "name": "Hold Person", "prepared": True, "level": 2}]}}
        req = CombatCastSpellRequest(actor_participant_id="p1", spell_canonical_key="hold_person", target_ref_id="enemy-a")
        spell_context = {"spell_name": "Hold Person", "spell_canonical_key": "hold_person", "spell_mode": "saving_throw", "selection_type": "creature", "slot_level": 2, "action_cost": "action", "source_kind": "spell", "effect_kind": "damage", "effect_dice": None, "effect_bonus": 0, "save_ability": "wisdom", "save_dc": 14, "save_success_outcome": "none", "target_type": "ranged", "range_kind": "distance", "attack_type": "none", "requires_target_sight": True, "requires_target_effect": True, "effects": [{"type": "apply_condition", "target": "selected_target", "params": {"condition": "paralyzed"}, "repeat_save": {"timing": "target_turn_end", "ability": "wisdom", "ends_on_success": True}}], "concentration": True}
        targeting_result = MagicMock(is_valid=True, validated_primary_target_ref_id="enemy-a", spatial_metadata=MagicMock(cover=None))
        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat.CombatService.resolve_effective_creature_type", return_value="dragon"),
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service", return_value=MagicMock(validate=MagicMock(return_value=targeting_result))),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock) as emit_log,
        ):
            with self.assertRaises(Exception):
                await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)
        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["2"]["used"], 0)
        self.assertEqual(state.participants[1].get("active_effects") or [], [])
        success_logs = [c for c in emit_log.await_args_list if "conjurou Hold Person" in ((c.args[4] or {}).get("message", "") if len(c.args) > 4 else "")]
        self.assertEqual(success_logs, [])

    async def test_hold_person_multi_target_known_non_humanoid_fails_atomically(self):
        state = CombatState(
            id="c1", session_id="s1", phase=CombatPhase.active, round=1, current_turn_index=0,
            participants=[
                {"id": "p1", "ref_id": "caster", "kind": "player", "display_name": "Lia", "status": "active", "team": "players", "actor_user_id": "u1", "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False}, "active_effects": []},
                {"id": "e1", "ref_id": "enemy-a", "kind": "session_entity", "display_name": "Bandido A", "status": "active", "team": "enemies", "active_effects": []},
                {"id": "e2", "ref_id": "enemy-b", "kind": "session_entity", "display_name": "Bandido B", "status": "active", "team": "enemies", "active_effects": []},
            ],
        )
        attacker_state = MagicMock()
        attacker_state.state_json = {"spellcasting": {"slots": {"3": {"used": 0, "max": 2}}, "spells": [{"canonicalKey": "hold_person", "name": "Hold Person", "prepared": True, "level": 2}]}}
        req = CombatCastSpellRequest(actor_participant_id="p1", spell_canonical_key="hold_person", target_ref_ids=["enemy-a", "enemy-b"], slot_level=3)
        spell_context = {"spell_name": "Hold Person", "spell_canonical_key": "hold_person", "spell_mode": "saving_throw", "selection_type": "creature", "slot_level": 3, "action_cost": "action", "source_kind": "spell", "effect_kind": "damage", "effect_dice": None, "effect_bonus": 0, "save_ability": "wisdom", "save_dc": 14, "save_success_outcome": "none", "target_type": "ranged", "range_kind": "distance", "attack_type": "none", "requires_target_sight": True, "requires_target_effect": True, "effects": [{"type": "apply_condition", "target": "selected_target", "params": {"condition": "paralyzed"}, "repeat_save": {"timing": "target_turn_end", "ability": "wisdom", "ends_on_success": True}}], "concentration": True, "max_targets": 2}
        targeting_result = MagicMock(is_valid=True, validated_primary_target_ref_id="enemy-a", spatial_metadata=MagicMock(cover=None))
        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat.CombatService.resolve_effective_creature_type", return_value="undead"),
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service", return_value=MagicMock(validate=MagicMock(return_value=targeting_result))),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock) as emit_log,
        ):
            with self.assertRaises(Exception):
                await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)
        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["3"]["used"], 0)
        self.assertEqual(state.participants[1].get("active_effects") or [], [])
        self.assertEqual(state.participants[2].get("active_effects") or [], [])
        success_logs = [c for c in emit_log.await_args_list if "conjurou Hold Person" in ((c.args[4] or {}).get("message", "") if len(c.args) > 4 else "")]
        self.assertEqual(success_logs, [])


if __name__ == "__main__":
    unittest.main()
