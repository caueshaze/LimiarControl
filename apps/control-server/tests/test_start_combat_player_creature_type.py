from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.session_state import SessionState
from app.schemas.combat import CombatParticipant, CombatStartRequest
from app.services.combat import CombatService


def _first(value):
    result = MagicMock()
    result.first.return_value = value
    return result


class StartCombatPlayerCreatureTypeTests(unittest.IsolatedAsyncioTestCase):
    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._sync_all_participant_statuses")
    @patch("app.services.combat.CombatService._resolve_map_selection", return_value=None)
    @patch("app.services.combat.CombatService.get_state", return_value=None)
    @patch("app.services.combat_service.lifecycle_initiative._encumbrance_tier_for_player", return_value="normal")
    @patch("app.services.combat_service.persistent_effects.restore_persisted_effects")
    async def test_player_without_wild_shape_starts_as_humanoid(
        self,
        _mock_restore,
        _mock_enc,
        _mock_get_state,
        _mock_resolve_map_selection,
        _mock_sync_status,
        _mock_emit_log,
        _mock_emit_state,
    ):
        db = MagicMock()
        db.exec.side_effect = [
            _first(None),  # User
            _first(SessionState(state_json={"wildShape": {"active": False}})),  # SessionState
        ]
        req = CombatStartRequest(
            participants=[
                CombatParticipant(
                    id="p1",
                    kind="player",
                    ref_id="user-1",
                    display_name="Hero",
                    team="players",
                )
            ],
            useMap=False,
        )

        state = await CombatService.start_combat(db, "session-1", req)
        p = state.participants[0]
        self.assertEqual(p.get("creature_type"), "humanoid")
        self.assertEqual(p.get("creatureType"), "humanoid")

    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._sync_all_participant_statuses")
    @patch("app.services.combat.CombatService._resolve_map_selection", return_value=None)
    @patch("app.services.combat.CombatService.get_state", return_value=None)
    @patch("app.services.combat_service.lifecycle_initiative._encumbrance_tier_for_player", return_value="normal")
    @patch("app.services.combat_service.persistent_effects.restore_persisted_effects")
    async def test_player_with_active_beast_wild_shape_starts_as_beast(
        self,
        _mock_restore,
        _mock_enc,
        _mock_get_state,
        _mock_resolve_map_selection,
        _mock_sync_status,
        _mock_emit_log,
        _mock_emit_state,
    ):
        db = MagicMock()
        db.exec.side_effect = [
            _first(None),  # User
            _first(SessionState(state_json={"wildShape": {"active": True, "formKey": "wolf"}})),
        ]
        req = CombatStartRequest(
            participants=[
                CombatParticipant(
                    id="p1",
                    kind="player",
                    ref_id="user-1",
                    display_name="Hero",
                    team="players",
                )
            ],
            useMap=False,
        )

        state = await CombatService.start_combat(db, "session-1", req)
        p = state.participants[0]
        self.assertEqual(p.get("creature_type"), "beast")
        self.assertEqual(p.get("creatureType"), "beast")

    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._sync_all_participant_statuses")
    @patch("app.services.combat.CombatService._resolve_map_selection", return_value=None)
    @patch("app.services.combat.CombatService.get_state", return_value=None)
    @patch("app.services.combat_service.lifecycle_initiative._encumbrance_tier_for_player", return_value="normal")
    @patch("app.services.combat_service.persistent_effects.restore_persisted_effects")
    async def test_inactive_or_invalid_wild_shape_falls_back_to_humanoid(
        self,
        _mock_restore,
        _mock_enc,
        _mock_get_state,
        _mock_resolve_map_selection,
        _mock_sync_status,
        _mock_emit_log,
        _mock_emit_state,
    ):
        req = CombatStartRequest(
            participants=[
                CombatParticipant(
                    id="p1",
                    kind="player",
                    ref_id="user-1",
                    display_name="Hero",
                    team="players",
                )
            ],
            useMap=False,
        )

        db_inactive = MagicMock()
        db_inactive.exec.side_effect = [
            _first(None),
            _first(SessionState(state_json={"wildShape": {"active": False, "formKey": "wolf"}})),
        ]
        state_inactive = await CombatService.start_combat(db_inactive, "session-1", req)
        self.assertEqual(state_inactive.participants[0].get("creature_type"), "humanoid")
        self.assertEqual(state_inactive.participants[0].get("creatureType"), "humanoid")

        db_invalid = MagicMock()
        db_invalid.exec.side_effect = [
            _first(None),
            _first(SessionState(state_json={"wildShape": {"active": True, "formKey": "invalid_form"}})),
        ]
        state_invalid = await CombatService.start_combat(db_invalid, "session-1", req)
        self.assertEqual(state_invalid.participants[0].get("creature_type"), "humanoid")
        self.assertEqual(state_invalid.participants[0].get("creatureType"), "humanoid")


if __name__ == "__main__":
    unittest.main()
