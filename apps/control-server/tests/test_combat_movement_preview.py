import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.integrations.limiar_map_client import (
    LimiarMapMovementCell,
    LimiarMapMovementResponse,
)
from app.schemas.combat import CombatMovementPreviewRequest
from app.services.combat import CombatService


class TestCombatMovementPreview(unittest.TestCase):
    @patch.object(CombatService, "_require_movement_capable")
    @patch.object(CombatService, "_require_actor_status")
    @patch.object(CombatService, "_require_active")
    @patch.object(CombatService, "_resolve_actor_participant")
    @patch.object(CombatService, "get_state")
    @patch.object(CombatService, "_build_limiar_map_client")
    def test_valid_preview_derives_cost_and_remaining_budget(
        self,
        mock_build_client,
        mock_get_state,
        mock_resolve_actor,
        _mock_require_active,
        _mock_require_status,
        _mock_require_movement,
    ) -> None:
        mock_get_state.return_value = SimpleNamespace(use_map=True)
        mock_resolve_actor.return_value = {"id": "participant-1", "ref_id": "combatant-1", "status": "active"}
        client = MagicMock()
        client.preview_movement.return_value = LimiarMapMovementResponse(
            is_valid=True,
            reason=None,
            session_id="session-1",
            action_id="preview-1",
            version=14,
            token_id="token-1",
            combatant_id="combatant-1",
            source_cell=LimiarMapMovementCell(x=1, y=1),
            destination_cell=LimiarMapMovementCell(x=3, y=1),
            path=(LimiarMapMovementCell(x=2, y=1), LimiarMapMovementCell(x=3, y=1)),
            path_cost_units=10,
            movement_budget=30,
            movement_speed_cells=6,
            remaining_budget=20,
        )
        mock_build_client.return_value = client

        result = CombatService.preview_movement(
            db=MagicMock(),
            session_id="session-1",
            req=CombatMovementPreviewRequest(destination_cell={"x": 3, "y": 1}),
            actor_user_id="user-1",
            is_gm=False,
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.path_cost_units, 10)
        self.assertEqual(result.remaining_budget, 20)
        self.assertEqual(
            [(cell.x, cell.y) for cell in result.path],
            [(2, 1), (3, 1)],
        )

    @patch.object(CombatService, "_require_movement_capable")
    @patch.object(CombatService, "_require_actor_status")
    @patch.object(CombatService, "_require_active")
    @patch.object(CombatService, "_resolve_actor_participant")
    @patch.object(CombatService, "get_state")
    @patch.object(CombatService, "_build_limiar_map_client")
    def test_invalid_preview_keeps_clear_reason(
        self,
        mock_build_client,
        mock_get_state,
        mock_resolve_actor,
        _mock_require_active,
        _mock_require_status,
        _mock_require_movement,
    ) -> None:
        mock_get_state.return_value = SimpleNamespace(use_map=True)
        mock_resolve_actor.return_value = {"id": "participant-1", "ref_id": "combatant-1", "status": "active"}
        client = MagicMock()
        client.preview_movement.return_value = LimiarMapMovementResponse(
            is_valid=False,
            reason="movement_budget_exceeded",
            session_id="session-1",
            action_id="preview-2",
            version=14,
            token_id="token-1",
            combatant_id="combatant-1",
            source_cell=LimiarMapMovementCell(x=1, y=1),
            destination_cell=LimiarMapMovementCell(x=8, y=1),
            path=tuple(LimiarMapMovementCell(x=x, y=1) for x in range(2, 9)),
            path_cost_units=35,
            movement_budget=30,
            movement_speed_cells=6,
            remaining_budget=0,
        )
        mock_build_client.return_value = client

        result = CombatService.preview_movement(
            db=MagicMock(),
            session_id="session-1",
            req=CombatMovementPreviewRequest(destination_cell={"x": 8, "y": 1}),
            actor_user_id="user-1",
            is_gm=False,
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.reason, "movement_budget_exceeded")
        self.assertEqual(result.path_cost_units, 35)

    @patch.object(CombatService, "_require_movement_capable")
    @patch.object(CombatService, "_require_actor_status")
    @patch.object(CombatService, "_require_active")
    @patch.object(CombatService, "_resolve_actor_participant")
    @patch.object(CombatService, "get_state")
    @patch.object(CombatService, "_build_limiar_map_client")
    def test_confirmed_movement_calls_map_move_endpoint(
        self,
        mock_build_client,
        mock_get_state,
        mock_resolve_actor,
        _mock_require_active,
        _mock_require_status,
        _mock_require_movement,
    ) -> None:
        mock_get_state.return_value = SimpleNamespace(use_map=True)
        mock_resolve_actor.return_value = {"id": "participant-1", "ref_id": "combatant-1", "status": "active"}
        client = MagicMock()
        client.move_combatant.return_value = LimiarMapMovementResponse(
            is_valid=True,
            reason=None,
            session_id="session-1",
            action_id="move-1",
            version=15,
            token_id="token-1",
            combatant_id="combatant-1",
            source_cell=LimiarMapMovementCell(x=1, y=1),
            destination_cell=LimiarMapMovementCell(x=2, y=1),
            path=(LimiarMapMovementCell(x=2, y=1),),
            path_cost_units=5,
            movement_budget=30,
            movement_speed_cells=6,
            remaining_budget=25,
        )
        mock_build_client.return_value = client

        CombatService.confirm_movement(
            db=MagicMock(),
            session_id="session-1",
            req=CombatMovementPreviewRequest(destination_cell={"x": 2, "y": 1}),
            actor_user_id="user-1",
            is_gm=False,
        )

        client.move_combatant.assert_called_once()


if __name__ == "__main__":
    unittest.main()
