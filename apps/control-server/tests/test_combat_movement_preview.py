import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, patch

from app.integrations.limiar_map_client import (
    LimiarMapMovementCell,
    LimiarMapMovementResponse,
)
from app.schemas.combat import CombatMovementPreviewRequest
from app.services.combat import CombatService


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


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
        mock_get_state.return_value = SimpleNamespace(use_map=True, active_area_effects=[])
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

        result = _run(
            CombatService.preview_movement(
                db=MagicMock(),
                session_id="session-1",
                req=CombatMovementPreviewRequest(destination_cell={"x": 3, "y": 1}),
                actor_user_id="user-1",
                is_gm=False,
            )
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
        mock_get_state.return_value = SimpleNamespace(use_map=True, active_area_effects=[])
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

        result = _run(
            CombatService.preview_movement(
                db=MagicMock(),
                session_id="session-1",
                req=CombatMovementPreviewRequest(destination_cell={"x": 8, "y": 1}),
                actor_user_id="user-1",
                is_gm=False,
            )
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
        mock_get_state.return_value = SimpleNamespace(use_map=True, active_area_effects=[])
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

        _run(
            CombatService.confirm_movement(
                db=MagicMock(),
                session_id="session-1",
                req=CombatMovementPreviewRequest(destination_cell={"x": 2, "y": 1}),
                actor_user_id="user-1",
                is_gm=False,
            )
        )

        client.move_combatant.assert_called_once()


class TestConfirmMovementAppliesHazards(unittest.TestCase):
    @patch.object(CombatService, "_emit_log")
    @patch.object(CombatService, "_emit_state")
    @patch.object(CombatService, "_emit_player_state_update")
    @patch.object(CombatService, "_get_stats")
    @patch.object(CombatService, "_apply_damage_to_target")
    @patch.object(CombatService, "_require_movement_capable")
    @patch.object(CombatService, "_require_actor_status")
    @patch.object(CombatService, "_require_active")
    @patch.object(CombatService, "_resolve_actor_participant")
    @patch.object(CombatService, "get_state")
    @patch.object(CombatService, "_build_limiar_map_client")
    def test_confirmed_movement_through_spike_growth_applies_damage_and_logs(
        self,
        mock_build_client,
        mock_get_state,
        mock_resolve_actor,
        _mock_require_active,
        _mock_require_status,
        _mock_require_movement,
        mock_apply_damage,
        mock_get_stats,
        mock_emit_player,
        mock_emit_state,
        mock_emit_log,
    ) -> None:
        spike_growth = {
            "id": "effect-1",
            "source_spell_canonical_key": "spike_growth",
            "source_spell_name": "Spike Growth",
            "effect_kind": "hazard",
            "terrain_effect": "difficult_terrain",
            "movement_damage_dice": "2d4",
            "damage_type": "Piercing",
            "damage_per_meters": 1.5,
            "affected_cells": [{"x": 2, "y": 1}, {"x": 3, "y": 1}],
        }
        state = SimpleNamespace(
            use_map=True,
            active_area_effects=[spike_growth],
            session_id="session-1",
        )
        mock_get_state.return_value = state
        mock_resolve_actor.return_value = {
            "id": "participant-1",
            "ref_id": "combatant-1",
            "kind": "player",
            "status": "active",
            "display_name": "Hero",
        }

        mock_apply_damage.return_value = (5, "", 10, None)
        mock_get_stats.return_value = (SimpleNamespace(), 5, 10, 10, 2, 3)

        async def _emit_log(*args, **kwargs):
            return None

        async def _emit_state(*args, **kwargs):
            return None

        async def _emit_player(*args, **kwargs):
            return None

        mock_emit_log.side_effect = _emit_log
        mock_emit_state.side_effect = _emit_state
        mock_emit_player.side_effect = _emit_player

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
            destination_cell=LimiarMapMovementCell(x=3, y=1),
            path=(LimiarMapMovementCell(x=2, y=1), LimiarMapMovementCell(x=3, y=1)),
            path_cost_units=20,
            movement_budget=30,
            movement_speed_cells=6,
            remaining_budget=10,
        )
        mock_build_client.return_value = client

        _run(
            CombatService.confirm_movement(
                db=MagicMock(),
                session_id="session-1",
                req=CombatMovementPreviewRequest(destination_cell={"x": 3, "y": 1}),
                actor_user_id="user-1",
                is_gm=False,
            )
        )

        self.assertEqual(mock_apply_damage.call_count, 1)
        _, kwargs = mock_apply_damage.call_args_list[0][0], mock_apply_damage.call_args_list[0][1]
        self.assertEqual(kwargs.get("damage_type"), "Piercing")

        log_calls = [c for c in mock_emit_log.call_args_list]
        self.assertEqual(len(log_calls), 1)
        payload = log_calls[0][0][1]
        self.assertEqual(payload["source"], "movement_hazard")
        self.assertEqual(payload["spellCanonicalKey"], "spike_growth")
        self.assertEqual(payload["cellsTraversed"], 2)
        self.assertIn("Spike Growth", payload["message"])

    @patch.object(CombatService, "_apply_damage_to_target")
    @patch.object(CombatService, "_require_movement_capable")
    @patch.object(CombatService, "_require_actor_status")
    @patch.object(CombatService, "_require_active")
    @patch.object(CombatService, "_resolve_actor_participant")
    @patch.object(CombatService, "get_state")
    @patch.object(CombatService, "_build_limiar_map_client")
    def test_preview_does_not_apply_hazards(
        self,
        mock_build_client,
        mock_get_state,
        mock_resolve_actor,
        _mock_require_active,
        _mock_require_status,
        _mock_require_movement,
        mock_apply_damage,
    ) -> None:
        spike_growth = {
            "id": "effect-1",
            "source_spell_canonical_key": "spike_growth",
            "source_spell_name": "Spike Growth",
            "terrain_effect": "difficult_terrain",
            "movement_damage_dice": "2d4",
            "damage_type": "Piercing",
            "damage_per_meters": 1.5,
            "affected_cells": [{"x": 2, "y": 1}],
        }
        mock_get_state.return_value = SimpleNamespace(
            use_map=True,
            active_area_effects=[spike_growth],
            session_id="session-1",
        )
        mock_resolve_actor.return_value = {
            "id": "p1",
            "ref_id": "c1",
            "kind": "player",
            "status": "active",
        }
        client = MagicMock()
        client.preview_movement.return_value = LimiarMapMovementResponse(
            is_valid=True,
            reason=None,
            session_id="session-1",
            action_id="preview-1",
            version=14,
            token_id="t1",
            combatant_id="c1",
            source_cell=LimiarMapMovementCell(x=1, y=1),
            destination_cell=LimiarMapMovementCell(x=2, y=1),
            path=(LimiarMapMovementCell(x=2, y=1),),
            path_cost_units=10,
            movement_budget=30,
            movement_speed_cells=6,
            remaining_budget=20,
        )
        mock_build_client.return_value = client

        _run(
            CombatService.preview_movement(
                db=MagicMock(),
                session_id="session-1",
                req=CombatMovementPreviewRequest(destination_cell={"x": 2, "y": 1}),
                actor_user_id="user-1",
                is_gm=False,
            )
        )

        mock_apply_damage.assert_not_called()


def _movement_response_with_elevation(
    source_elevation: float | None = None,
    dest_elevation: float | None = None,
    is_valid: bool = True,
    source_cell: LimiarMapMovementCell | None = LimiarMapMovementCell(x=1, y=1),
) -> LimiarMapMovementResponse:
    return LimiarMapMovementResponse(
        is_valid=is_valid,
        reason=None if is_valid else "rejected",
        session_id="session-1",
        action_id="move-1",
        version=15,
        token_id="token-1",
        combatant_id="combatant-1",
        source_cell=source_cell,
        destination_cell=LimiarMapMovementCell(x=3, y=1),
        path=(LimiarMapMovementCell(x=3, y=1),),
        path_cost_units=5,
        movement_budget=30,
        movement_speed_cells=6,
        remaining_budget=25,
        source_elevation_meters=source_elevation,
        destination_elevation_meters=dest_elevation,
    )


class TestConfirmMovementFallDetection(unittest.TestCase):
    @patch.object(CombatService, "_apply_movement_hazards")
    @patch.object(CombatService, "resolve_fall")
    @patch.object(CombatService, "_require_movement_capable")
    @patch.object(CombatService, "_require_actor_status")
    @patch.object(CombatService, "_require_active")
    @patch.object(CombatService, "_resolve_actor_participant")
    @patch.object(CombatService, "get_state")
    @patch.object(CombatService, "_build_limiar_map_client")
    def test_same_elevation_no_fall(
        self, mock_build_client, mock_get_state, mock_resolve_actor,
        _mock_require_active, _mock_require_status, _mock_require_movement,
        mock_resolve_fall, mock_hazards,
    ):
        mock_get_state.return_value = SimpleNamespace(use_map=True, active_area_effects=[])
        mock_resolve_actor.return_value = {"id": "participant-1", "ref_id": "combatant-1", "status": "active"}
        client = MagicMock()
        client.move_combatant.return_value = _movement_response_with_elevation(
            source_elevation=6.0, dest_elevation=6.0,
        )
        mock_build_client.return_value = client

        _run(CombatService.confirm_movement(
            db=MagicMock(), session_id="session-1",
            req=CombatMovementPreviewRequest(destination_cell={"x": 3, "y": 1}),
            actor_user_id="user-1", is_gm=True,
        ))

        mock_resolve_fall.assert_not_called()

    @patch.object(CombatService, "_apply_movement_hazards")
    @patch.object(CombatService, "resolve_fall")
    @patch.object(CombatService, "_require_movement_capable")
    @patch.object(CombatService, "_require_actor_status")
    @patch.object(CombatService, "_require_active")
    @patch.object(CombatService, "_resolve_actor_participant")
    @patch.object(CombatService, "get_state")
    @patch.object(CombatService, "_build_limiar_map_client")
    def test_upward_movement_no_fall(
        self, mock_build_client, mock_get_state, mock_resolve_actor,
        _mock_require_active, _mock_require_status, _mock_require_movement,
        mock_resolve_fall, mock_hazards,
    ):
        mock_get_state.return_value = SimpleNamespace(use_map=True, active_area_effects=[])
        mock_resolve_actor.return_value = {"id": "participant-1", "ref_id": "combatant-1", "status": "active"}
        client = MagicMock()
        client.move_combatant.return_value = _movement_response_with_elevation(
            source_elevation=0.0, dest_elevation=6.0,
        )
        mock_build_client.return_value = client

        _run(CombatService.confirm_movement(
            db=MagicMock(), session_id="session-1",
            req=CombatMovementPreviewRequest(destination_cell={"x": 3, "y": 1}),
            actor_user_id="user-1", is_gm=True,
        ))

        mock_resolve_fall.assert_not_called()

    @patch.object(CombatService, "_apply_movement_hazards")
    @patch.object(CombatService, "resolve_fall")
    @patch.object(CombatService, "_require_movement_capable")
    @patch.object(CombatService, "_require_actor_status")
    @patch.object(CombatService, "_require_active")
    @patch.object(CombatService, "_resolve_actor_participant")
    @patch.object(CombatService, "get_state")
    @patch.object(CombatService, "_build_limiar_map_client")
    def test_small_drop_below_threshold_no_fall(
        self, mock_build_client, mock_get_state, mock_resolve_actor,
        _mock_require_active, _mock_require_status, _mock_require_movement,
        mock_resolve_fall, mock_hazards,
    ):
        mock_get_state.return_value = SimpleNamespace(use_map=True, active_area_effects=[])
        mock_resolve_actor.return_value = {"id": "participant-1", "ref_id": "combatant-1", "status": "active"}
        client = MagicMock()
        client.move_combatant.return_value = _movement_response_with_elevation(
            source_elevation=3.0, dest_elevation=1.0,
        )
        mock_build_client.return_value = client

        _run(CombatService.confirm_movement(
            db=MagicMock(), session_id="session-1",
            req=CombatMovementPreviewRequest(destination_cell={"x": 3, "y": 1}),
            actor_user_id="user-1", is_gm=True,
        ))

        mock_resolve_fall.assert_not_called()

    @patch.object(CombatService, "_apply_movement_hazards")
    @patch.object(CombatService, "resolve_fall")
    @patch.object(CombatService, "_require_movement_capable")
    @patch.object(CombatService, "_require_actor_status")
    @patch.object(CombatService, "_require_active")
    @patch.object(CombatService, "_resolve_actor_participant")
    @patch.object(CombatService, "get_state")
    @patch.object(CombatService, "_build_limiar_map_client")
    def test_threshold_drop_3m_calls_resolve_fall(
        self, mock_build_client, mock_get_state, mock_resolve_actor,
        _mock_require_active, _mock_require_status, _mock_require_movement,
        mock_resolve_fall, mock_hazards,
    ):
        mock_get_state.return_value = SimpleNamespace(use_map=True, active_area_effects=[])
        mock_resolve_actor.return_value = {"id": "participant-1", "ref_id": "combatant-1", "status": "active"}
        client = MagicMock()
        client.move_combatant.return_value = _movement_response_with_elevation(
            source_elevation=6.0, dest_elevation=3.0,
        )
        mock_build_client.return_value = client

        _run(CombatService.confirm_movement(
            db=MagicMock(), session_id="session-1",
            req=CombatMovementPreviewRequest(destination_cell={"x": 3, "y": 1}),
            actor_user_id="user-1", is_gm=True,
        ))

        mock_resolve_fall.assert_called_once_with(
            ANY, "session-1", "participant-1", 3.0, "user-1", True,
        )

    @patch.object(CombatService, "_apply_movement_hazards")
    @patch.object(CombatService, "resolve_fall")
    @patch.object(CombatService, "_require_movement_capable")
    @patch.object(CombatService, "_require_actor_status")
    @patch.object(CombatService, "_require_active")
    @patch.object(CombatService, "_resolve_actor_participant")
    @patch.object(CombatService, "get_state")
    @patch.object(CombatService, "_build_limiar_map_client")
    def test_larger_drop_6m_calls_resolve_fall(
        self, mock_build_client, mock_get_state, mock_resolve_actor,
        _mock_require_active, _mock_require_status, _mock_require_movement,
        mock_resolve_fall, mock_hazards,
    ):
        mock_get_state.return_value = SimpleNamespace(use_map=True, active_area_effects=[])
        mock_resolve_actor.return_value = {"id": "participant-1", "ref_id": "combatant-1", "status": "active"}
        client = MagicMock()
        client.move_combatant.return_value = _movement_response_with_elevation(
            source_elevation=6.0, dest_elevation=0.0,
        )
        mock_build_client.return_value = client

        _run(CombatService.confirm_movement(
            db=MagicMock(), session_id="session-1",
            req=CombatMovementPreviewRequest(destination_cell={"x": 3, "y": 1}),
            actor_user_id="user-1", is_gm=True,
        ))

        mock_resolve_fall.assert_called_once_with(
            ANY, "session-1", "participant-1", 6.0, "user-1", True,
        )

    @patch.object(CombatService, "_apply_movement_hazards")
    @patch.object(CombatService, "resolve_fall")
    @patch.object(CombatService, "_require_movement_capable")
    @patch.object(CombatService, "_require_actor_status")
    @patch.object(CombatService, "_require_active")
    @patch.object(CombatService, "_resolve_actor_participant")
    @patch.object(CombatService, "get_state")
    @patch.object(CombatService, "_build_limiar_map_client")
    def test_missing_elevation_defaults_to_zero_no_fall(
        self, mock_build_client, mock_get_state, mock_resolve_actor,
        _mock_require_active, _mock_require_status, _mock_require_movement,
        mock_resolve_fall, mock_hazards,
    ):
        mock_get_state.return_value = SimpleNamespace(use_map=True, active_area_effects=[])
        mock_resolve_actor.return_value = {"id": "participant-1", "ref_id": "combatant-1", "status": "active"}
        client = MagicMock()
        client.move_combatant.return_value = _movement_response_with_elevation(
            source_elevation=None, dest_elevation=None,
        )
        mock_build_client.return_value = client

        _run(CombatService.confirm_movement(
            db=MagicMock(), session_id="session-1",
            req=CombatMovementPreviewRequest(destination_cell={"x": 3, "y": 1}),
            actor_user_id="user-1", is_gm=True,
        ))

        mock_resolve_fall.assert_not_called()

    @patch.object(CombatService, "_apply_movement_hazards")
    @patch.object(CombatService, "resolve_fall")
    @patch.object(CombatService, "_require_movement_capable")
    @patch.object(CombatService, "_require_actor_status")
    @patch.object(CombatService, "_require_active")
    @patch.object(CombatService, "_resolve_actor_participant")
    @patch.object(CombatService, "get_state")
    @patch.object(CombatService, "_build_limiar_map_client")
    def test_failed_movement_no_fall(
        self, mock_build_client, mock_get_state, mock_resolve_actor,
        _mock_require_active, _mock_require_status, _mock_require_movement,
        mock_resolve_fall, mock_hazards,
    ):
        mock_get_state.return_value = SimpleNamespace(use_map=True, active_area_effects=[])
        mock_resolve_actor.return_value = {"id": "participant-1", "ref_id": "combatant-1", "status": "active"}
        client = MagicMock()
        client.move_combatant.return_value = _movement_response_with_elevation(
            source_elevation=6.0, dest_elevation=0.0, is_valid=False,
        )
        mock_build_client.return_value = client

        _run(CombatService.confirm_movement(
            db=MagicMock(), session_id="session-1",
            req=CombatMovementPreviewRequest(destination_cell={"x": 3, "y": 1}),
            actor_user_id="user-1", is_gm=True,
        ))

        mock_resolve_fall.assert_not_called()

    @patch.object(CombatService, "_apply_movement_hazards")
    @patch.object(CombatService, "resolve_fall")
    @patch.object(CombatService, "_require_movement_capable")
    @patch.object(CombatService, "_require_actor_status")
    @patch.object(CombatService, "_require_active")
    @patch.object(CombatService, "_resolve_actor_participant")
    @patch.object(CombatService, "get_state")
    @patch.object(CombatService, "_build_limiar_map_client")
    def test_preview_does_not_trigger_fall(
        self, mock_build_client, mock_get_state, mock_resolve_actor,
        _mock_require_active, _mock_require_status, _mock_require_movement,
        mock_resolve_fall, mock_hazards,
    ):
        mock_get_state.return_value = SimpleNamespace(use_map=True, active_area_effects=[])
        mock_resolve_actor.return_value = {"id": "participant-1", "ref_id": "combatant-1", "status": "active"}
        client = MagicMock()
        client.preview_movement.return_value = _movement_response_with_elevation(
            source_elevation=6.0, dest_elevation=0.0,
        )
        mock_build_client.return_value = client

        _run(CombatService.preview_movement(
            db=MagicMock(), session_id="session-1",
            req=CombatMovementPreviewRequest(destination_cell={"x": 3, "y": 1}),
            actor_user_id="user-1", is_gm=True,
        ))

        mock_resolve_fall.assert_not_called()


if __name__ == "__main__":
    unittest.main()
