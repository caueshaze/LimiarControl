from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.schemas.combat import CombatResolveSaveRequest
from app.schemas.roll import RollResult
from app.services.combat import CombatService


def _build_state_with_participant_effects(effects: list[dict]) -> CombatState:
    return CombatState(
        id="combat-save-resolve",
        session_id="session-save-resolve",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=[
            {
                "id": "p1",
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Mage",
                "initiative": 15,
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-1",
                "active_effects": [],
            },
            {
                "id": "e1",
                "ref_id": "enemy-1",
                "kind": "session_entity",
                "display_name": "Target",
                "initiative": 10,
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
                "active_effects": effects,
            },
        ],
    )


class TestPendingSaveModifierSources(unittest.IsolatedAsyncioTestCase):
    async def test_pending_save_includes_declared_disadvantage_sources(self):
        state = _build_state_with_participant_effects(
            [
                {
                    "kind": "spell_effect",
                    "metadata": {
                        "source_spell_name": "Reduzir",
                        "declarative_effect": {
                            "type": "disadvantage_on_saves",
                            "params": {"abilities": ["strength"]},
                        },
                    },
                }
            ]
        )
        target = state.participants[1]
        target["pending_save"] = {
            "id": "pending-save-1",
            "status": "pending",
            "spell_name": "Test Spell",
            "spell_canonical_key": "test_spell",
            "action_kind": "saving_throw",
            "save_ability": "strength",
            "save_dc": 15,
            "effect_kind": "damage",
            "effect_bonus": 0,
            "effect_dice": None,
            "effect_roll_required": False,
            "save_success_outcome": "none",
            "damage_type": None,
            "attacker_ref_id": "player-1",
            "attacker_participant_id": "p1",
            "attacker_display_name": "Mage",
        }

        db = MagicMock()
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()

        save_roll = RollResult(
            event_id="save-roll-1",
            roll_type="save",
            actor_kind="session_entity",
            actor_ref_id="enemy-1",
            actor_display_name="Target",
            rolls=[5],
            selected_roll=5,
            advantage_mode="disadvantage",
            modifier_used=0,
            override_used=False,
            formula="1d20 + 0",
            total=5,
            ability="strength",
            dc=15,
            success=False,
            timestamp=datetime.now(timezone.utc),
        )

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch(
                "app.services.combat.CombatService._build_roll_actor_stats_for_save",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.combat_service.save_resolve.resolve_saving_throw",
                return_value=save_roll,
            ),
            patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock),
            patch("app.services.combat.CombatService._emit_and_persist_log", new_callable=AsyncMock),
            patch("app.services.combat.CombatService._apply_spell_effect", return_value=(None, "", None, None)),
        ):
            result = await CombatService.resolve_pending_save(
                db,
                "session-save-resolve",
                CombatResolveSaveRequest(
                    target_participant_id="e1",
                    pending_save_id="pending-save-1",
                ),
                "user-1",
                True,
            )

        self.assertIn("roll_result", result)
        roll_result = result["roll_result"]
        self.assertIsNotNone(roll_result.check_modifier_sources)
        self.assertEqual(len(roll_result.check_modifier_sources), 1)
        self.assertEqual(roll_result.check_modifier_sources[0]["source_label"], "Reduzir")
        self.assertEqual(roll_result.check_modifier_sources[0]["modifier_type"], "disadvantage")
        self.assertTrue(roll_result.check_modifier_sources[0]["applied"])

    async def test_pending_save_preserves_restrained_behavior(self):
        state = _build_state_with_participant_effects(
            [
                {
                    "kind": "condition",
                    "condition_type": "restrained",
                }
            ]
        )
        target = state.participants[1]
        target["pending_save"] = {
            "id": "pending-save-1",
            "status": "pending",
            "spell_name": "Test Spell",
            "spell_canonical_key": "test_spell",
            "action_kind": "saving_throw",
            "save_ability": "dexterity",
            "save_dc": 15,
            "effect_kind": "damage",
            "effect_bonus": 0,
            "effect_dice": None,
            "effect_roll_required": False,
            "save_success_outcome": "none",
            "damage_type": None,
            "attacker_ref_id": "player-1",
            "attacker_participant_id": "p1",
            "attacker_display_name": "Mage",
        }

        db = MagicMock()
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()

        save_roll = RollResult(
            event_id="save-roll-1",
            roll_type="save",
            actor_kind="session_entity",
            actor_ref_id="enemy-1",
            actor_display_name="Target",
            rolls=[5],
            selected_roll=5,
            advantage_mode="disadvantage",
            modifier_used=0,
            override_used=False,
            formula="1d20 + 0",
            total=5,
            ability="dexterity",
            dc=15,
            success=False,
            timestamp=datetime.now(timezone.utc),
        )

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch(
                "app.services.combat.CombatService._build_roll_actor_stats_for_save",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.combat_service.save_resolve.resolve_saving_throw",
                return_value=save_roll,
            ),
            patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock),
            patch("app.services.combat.CombatService._emit_and_persist_log", new_callable=AsyncMock),
            patch("app.services.combat.CombatService._apply_spell_effect", return_value=(None, "", None, None)),
        ):
            result = await CombatService.resolve_pending_save(
                db,
                "session-save-resolve",
                CombatResolveSaveRequest(
                    target_participant_id="e1",
                    pending_save_id="pending-save-1",
                ),
                "user-1",
                True,
            )

        self.assertIn("roll_result", result)
        roll_result = result["roll_result"]
        self.assertIsNotNone(roll_result.check_modifier_sources)
        # restrained does not produce source_details today; verify it doesn't break
        self.assertEqual(roll_result.advantage_mode, "disadvantage")


if __name__ == "__main__":
    unittest.main()
