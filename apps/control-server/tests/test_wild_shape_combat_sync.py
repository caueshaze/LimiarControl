import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.api.routes.wild_shape import _sync_combat_participant_wild_shape_state


class TestWildShapeCombatParticipantSync(unittest.IsolatedAsyncioTestCase):
    async def test_sync_updates_wild_shape_flag_and_emits_state_without_reload(self):
        combat_state = CombatState(
            id="combat-1",
            session_id="session-123",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "player-123",
                    "kind": "player",
                    "display_name": "Hero",
                    "initiative": 10,
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "user-1",
                }
            ],
        )
        db = MagicMock()
        exec_result = MagicMock()
        exec_result.first.return_value = combat_state
        db.exec.return_value = exec_result

        with patch("app.api.routes.wild_shape.CombatService._emit_state", new=AsyncMock()) as mock_emit_state:
            await _sync_combat_participant_wild_shape_state(
                db,
                "session-123",
                "player-123",
                {"wildShape": {"active": True, "formKey": "wolf"}},
            )
            self.assertTrue(combat_state.participants[0]["wild_shape_active"])
            self.assertEqual(combat_state.participants[0]["creatureType"], "beast")

            await _sync_combat_participant_wild_shape_state(
                db,
                "session-123",
                "player-123",
                {"wildShape": {"active": False, "formKey": None}},
            )
            self.assertFalse(combat_state.participants[0]["wild_shape_active"])
            self.assertEqual(combat_state.participants[0]["creatureType"], "humanoid")

        self.assertEqual(mock_emit_state.await_count, 2)
        mock_emit_state.assert_any_await("session-123", combat_state)
        self.assertGreaterEqual(db.commit.call_count, 2)

