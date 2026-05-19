from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import ValidationError

from _combat_test_shared import TestCombatServiceBase
from app.api.routes.combat import update_distances as update_distances_route
from app.models.combat import CombatState
from app.schemas.combat import (
    CombatLocalDistanceEntry,
    CombatParticipant,
    CombatStartRequest,
    CombatUpdateDistancesRequest,
)
from app.services.combat import CombatService, CombatServiceError


def _distance_entry(
    from_ref_id: str,
    to_ref_id: str,
    distance_meters: float,
) -> CombatLocalDistanceEntry:
    return CombatLocalDistanceEntry(
        from_ref_id=from_ref_id,
        to_ref_id=to_ref_id,
        distance_meters=distance_meters,
    )


class CombatLocalDistanceSchemaTests(unittest.TestCase):
    def test_negative_distance_is_rejected(self):
        with self.assertRaises(ValidationError):
            CombatLocalDistanceEntry(
                from_ref_id="player-123",
                to_ref_id="enemy-123",
                distance_meters=-1,
            )


class CombatLocalDistanceLifecycleTests(TestCombatServiceBase):
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    @patch("app.services.combat.CombatService._sync_all_participant_statuses")
    @patch("app.services.combat.CombatService.get_state", return_value=None)
    async def test_start_combat_persists_initial_distances_when_use_map_false(
        self,
        _mock_get_state,
        _mock_sync_all_participant_statuses,
        _mock_emit_log,
        _mock_emit_state,
    ) -> None:
        req = CombatStartRequest(
            participants=[
                CombatParticipant(
                    id="p1",
                    ref_id="player-123",
                    kind="player",
                    display_name="Hero",
                    team="players",
                    visible=True,
                ),
                CombatParticipant(
                    id="e1",
                    ref_id="enemy-123",
                    kind="session_entity",
                    display_name="Goblin",
                    team="enemies",
                    visible=True,
                ),
            ],
            useMap=False,
            initialDistances=[
                _distance_entry("player-123", "enemy-123", 4.5),
            ],
        )

        state = await CombatService.start_combat(self.db, "session-123", req)

        self.assertEqual(
            state.local_distances,
            {
                "player-123": {"enemy-123": 4.5},
                "enemy-123": {"player-123": 4.5},
            },
        )

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    @patch("app.services.combat.CombatService._sync_all_participant_statuses")
    @patch("app.services.combat.CombatService.get_state", return_value=None)
    async def test_start_combat_rejects_unknown_initial_distance_refs(
        self,
        _mock_get_state,
        _mock_sync_all_participant_statuses,
        _mock_emit_log,
        _mock_emit_state,
    ) -> None:
        req = CombatStartRequest(
            participants=[
                CombatParticipant(
                    id="p1",
                    ref_id="player-123",
                    kind="player",
                    display_name="Hero",
                    team="players",
                    visible=True,
                ),
            ],
            useMap=False,
            initialDistances=[
                _distance_entry("player-123", "enemy-404", 4.5),
            ],
        )

        with self.assertRaises(CombatServiceError) as context:
            await CombatService.start_combat(self.db, "session-123", req)

        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("enemy-404", str(context.exception.detail))

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    @patch("app.services.combat.CombatService._sync_all_participant_statuses")
    @patch("app.services.combat.CombatService.get_state", return_value=None)
    async def test_start_combat_ignores_initial_distances_when_map_is_enabled(
        self,
        _mock_get_state,
        _mock_sync_all_participant_statuses,
        _mock_emit_log,
        _mock_emit_state,
    ) -> None:
        req = CombatStartRequest(
            participants=[
                CombatParticipant(
                    id="p1",
                    ref_id="player-123",
                    kind="player",
                    display_name="Hero",
                    team="players",
                    visible=True,
                ),
                CombatParticipant(
                    id="e1",
                    ref_id="enemy-123",
                    kind="session_entity",
                    display_name="Goblin",
                    team="enemies",
                    visible=True,
                ),
            ],
            useMap=True,
            initialDistances=[
                _distance_entry("player-123", "enemy-123", 4.5),
            ],
        )

        state = await CombatService.start_combat(self.db, "session-123", req)

        self.assertEqual(state.local_distances, {})

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService.get_state")
    async def test_update_distances_persists_symmetrically(
        self,
        mock_get_state,
        mock_emit_state,
    ) -> None:
        mock_get_state.return_value = self.state
        req = CombatUpdateDistancesRequest(
            distances=[
                _distance_entry("player-123", "enemy-123", 6.0),
            ]
        )

        state = await CombatService.update_distances(self.db, "session-123", req)

        self.assertEqual(
            state.local_distances,
            {
                "player-123": {"enemy-123": 6.0},
                "enemy-123": {"player-123": 6.0},
            },
        )
        mock_emit_state.assert_called_once()

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService.get_state")
    async def test_update_distances_rejects_unknown_participant_refs(
        self,
        mock_get_state,
        _mock_emit_state,
    ) -> None:
        mock_get_state.return_value = self.state
        req = CombatUpdateDistancesRequest(
            distances=[
                _distance_entry("player-123", "enemy-404", 6.0),
            ]
        )

        with self.assertRaises(CombatServiceError) as context:
            await CombatService.update_distances(self.db, "session-123", req)

        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("enemy-404", str(context.exception.detail))


class CombatLocalDistanceRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_gm_can_update_local_distances(self) -> None:
        user = MagicMock()
        db = MagicMock()
        req = CombatUpdateDistancesRequest(
            distances=[
                _distance_entry("player-123", "enemy-123", 3.0),
            ]
        )
        expected_state = MagicMock(spec=CombatState)

        with (
            patch("app.api.routes.combat._is_session_gm", return_value=True),
            patch(
                "app.api.routes.combat.CombatService.update_distances",
                new=AsyncMock(return_value=expected_state),
            ) as mock_update_distances,
        ):
            result = await update_distances_route("session-123", req, db, user)

        self.assertIs(result, expected_state)
        mock_update_distances.assert_awaited_once_with(db, "session-123", req)

    async def test_non_gm_cannot_update_local_distances(self) -> None:
        user = MagicMock()
        db = MagicMock()
        req = CombatUpdateDistancesRequest(
            distances=[
                _distance_entry("player-123", "enemy-123", 3.0),
            ]
        )

        with (
            patch("app.api.routes.combat._is_session_gm", return_value=False),
            patch(
                "app.api.routes.combat.CombatService.update_distances",
                new=AsyncMock(),
            ) as mock_update_distances,
        ):
            with self.assertRaises(CombatServiceError) as context:
                await update_distances_route("session-123", req, db, user)

        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(context.exception.detail, "Only GM can update combat distances")
        mock_update_distances.assert_not_awaited()
