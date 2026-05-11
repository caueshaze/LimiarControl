from __future__ import annotations

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
        payload = json.loads(open("Base/base_spells.seed.json", encoding="utf-8").read())
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


if __name__ == "__main__":
    unittest.main()
