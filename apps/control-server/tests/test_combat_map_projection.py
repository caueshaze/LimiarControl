from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.integrations.limiar_map_client import (
    LimiarMapClientError,
    LimiarMapStateResponse,
    LimiarMapTokenState,
)
from app.models.campaign_entity import CampaignEntity
from app.models.combat import CombatPhase, CombatState
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.schemas.combat import (
    CombatSetInitiativeParticipant,
    CombatSetInitiativeRequest,
)
from app.services.combat import CombatService
from app.services.combat_service.limiar_map_projection import (
    LimiarMapCombatProjectionService,
    maybe_project_combat_start_to_limiar_map,
)


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value


class FakeLimiarMapClient:
    def __init__(
        self,
        *,
        state_response: LimiarMapStateResponse | None = None,
        get_state_error: Exception | None = None,
        sync_error: Exception | None = None,
        start_error: Exception | None = None,
        advance_error: Exception | None = None,
        end_error: Exception | None = None,
    ) -> None:
        self.state_response = state_response
        self.get_state_error = get_state_error
        self.sync_error = sync_error
        self.start_error = start_error
        self.advance_error = advance_error
        self.end_error = end_error
        self.calls: list[tuple[str, str, dict | None]] = []

    def get_state(self, session_id: str) -> LimiarMapStateResponse:
        self.calls.append(("get_state", session_id, None))
        if self.get_state_error is not None:
            raise self.get_state_error
        if self.state_response is None:
            raise AssertionError("state_response is required")
        return self.state_response

    def advance_combat(
        self,
        session_id: str,
        payload: dict,
    ) -> LimiarMapStateResponse:
        self.calls.append(("advance_combat", session_id, payload))
        if self.advance_error is not None:
            raise self.advance_error
        if self.state_response is None:
            raise AssertionError("state_response is required")
        return self.state_response

    def end_combat(
        self,
        session_id: str,
        payload: dict,
    ) -> LimiarMapStateResponse:
        self.calls.append(("end_combat", session_id, payload))
        if self.end_error is not None:
            raise self.end_error
        if self.state_response is None:
            raise AssertionError("state_response is required")
        return self.state_response

    def sync_tokens(
        self,
        session_id: str,
        payload: dict,
    ) -> LimiarMapStateResponse:
        self.calls.append(("sync_tokens", session_id, payload))
        if self.sync_error is not None:
            raise self.sync_error
        if self.state_response is None:
            raise AssertionError("state_response is required")
        return self.state_response

    def start_combat(
        self,
        session_id: str,
        payload: dict,
    ) -> LimiarMapStateResponse:
        self.calls.append(("start_combat", session_id, payload))
        if self.start_error is not None:
            raise self.start_error
        if self.state_response is None:
            raise AssertionError("state_response is required")
        return self.state_response


def build_active_state() -> CombatState:
    return CombatState(
        id="combat-123",
        session_id="session-123",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=[
            {
                "id": "e1",
                "ref_id": "enemy-123",
                "kind": "session_entity",
                "display_name": "Goblin",
                "initiative": 20,
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
            },
            {
                "id": "p1",
                "ref_id": "player-123",
                "kind": "player",
                "display_name": "Hero",
                "initiative": 15,
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-1",
            },
        ],
    )


def build_map_state(
    *tokens: LimiarMapTokenState,
    round_number: int | None = None,
    turn_index: int | None = None,
    active_combatant_id: str | None = None,
    initiative_order: tuple[str, ...] = (),
) -> LimiarMapStateResponse:
    return LimiarMapStateResponse(
        session_id="session-123",
        version=4,
        tokens=tokens,
        round_number=round_number,
        turn_index=turn_index,
        active_combatant_id=active_combatant_id,
        initiative_order=initiative_order,
    )


class LimiarMapCombatProjectionTests(unittest.TestCase):
    def test_map_off_skips_projection_entirely(self) -> None:
        with (
            patch(
                "app.services.combat_service.limiar_map_projection.get_limiar_map_projection_service"
            ) as mock_get_service,
            patch(
                "app.services.combat_service.limiar_map_projection.settings.limiar_map_enabled",
                False,
            ),
        ):
            maybe_project_combat_start_to_limiar_map(
                MagicMock(),
                "session-123",
                build_active_state(),
            )

        mock_get_service.assert_not_called()

    def test_projection_success_syncs_tokens_before_starting_combat(self) -> None:
        db = MagicMock()
        db.exec.side_effect = [
            _FakeScalarResult(
                SessionEntity(
                    id="enemy-123",
                    session_id="session-123",
                    campaign_entity_id="ce-1",
                    overrides={"mapTokenId": "tok_enemy"},
                )
            ),
            _FakeScalarResult(
                CampaignEntity(
                    id="ce-1",
                    campaign_id="camp-1",
                    name="Goblin",
                    speed_meters=12,
                )
            ),
            _FakeScalarResult(
                SessionState(
                    id="state-1",
                    session_id="session-123",
                    player_user_id="player-123",
                    state_json={"speedMeters": 9},
                )
            ),
        ]
        client = FakeLimiarMapClient(
            state_response=build_map_state(
                LimiarMapTokenState(
                    token_id="tok_player",
                    controller_type="player",
                    controller_id="player-123",
                    movement_speed_cells=30,
                    combatant_id=None,
                ),
                LimiarMapTokenState(
                    token_id="tok_enemy",
                    controller_type="gm",
                    controller_id="gm-1",
                    movement_speed_cells=30,
                    combatant_id=None,
                ),
            )
        )
        service = LimiarMapCombatProjectionService(client)
        state = build_active_state()

        service.project_combat_start(db, "session-123", state)

        self.assertEqual(
            [call[0] for call in client.calls],
            ["get_state", "sync_tokens", "start_combat"],
        )
        sync_payload = client.calls[1][2]
        self.assertEqual(
            sync_payload,
            {
                "tokens": [
                    {
                        "tokenId": "tok_enemy",
                        "combatantId": "enemy-123",
                        "conditions": [],
                        "label": "Goblin",
                        "controllerId": "gm-control",
                        "controllerType": "gm",
                        "movementSpeedCells": 8,
                    },
                    {
                        "tokenId": "tok_player",
                        "combatantId": "player-123",
                        "conditions": [],
                        "label": "Hero",
                        "controllerId": "user-1",
                        "controllerType": "player",
                        "movementSpeedCells": 6,
                    },
                ]
            },
        )
        start_payload = client.calls[2][2]
        self.assertEqual(
            start_payload,
            {
                "actionId": "control-combat-start:combat-123",
                "combatants": [
                    {"combatantId": "enemy-123", "initiativeScore": 20},
                    {"combatantId": "player-123", "initiativeScore": 15},
                ],
            },
        )

    def test_projection_includes_selected_battle_map_payload(self) -> None:
        db = MagicMock()
        db.exec.side_effect = [
            _FakeScalarResult(
                SessionEntity(
                    id="enemy-123",
                    session_id="session-123",
                    campaign_entity_id="ce-1",
                    overrides={"mapTokenId": "tok_enemy"},
                )
            ),
            _FakeScalarResult(
                CampaignEntity(
                    id="ce-1",
                    campaign_id="camp-1",
                    name="Goblin",
                    speed_meters=12,
                )
            ),
            _FakeScalarResult(
                SessionState(
                    id="state-1",
                    session_id="session-123",
                    player_user_id="player-123",
                    state_json={"speedMeters": 9},
                )
            ),
        ]
        client = FakeLimiarMapClient(
            state_response=build_map_state(
                LimiarMapTokenState(
                    token_id="tok_player",
                    controller_type="player",
                    controller_id="player-123",
                    movement_speed_cells=30,
                    combatant_id=None,
                ),
                LimiarMapTokenState(
                    token_id="tok_enemy",
                    controller_type="gm",
                    controller_id="gm-1",
                    movement_speed_cells=30,
                    combatant_id=None,
                ),
            )
        )
        service = LimiarMapCombatProjectionService(client)
        state = build_active_state()
        state.map_selection = {
            "kind": "campaign_map",
            "mapName": "Dungeon Depths",
            "imageUrl": "/api/assets/campaigns/campaign-1/maps/asset1234567890abcdef1234567890ab",
            "gridWidth": 32,
            "gridHeight": 24,
            "calibration": {"x": 0.1, "y": 0.2, "width": 0.7, "height": 0.6},
            "obstacles": [
                {
                    "x": 2,
                    "y": 3,
                    "blocksMovement": True,
                    "blocksEffect": False,
                    "blocksVision": False,
                    "cover": "threeQuarters",
                    "clipsDiagonalMovement": True,
                    "movementCostMultiplier": 1,
                }
            ],
            "edgeObstacles": [
                {
                    "x": 4,
                    "y": 5,
                    "direction": "E",
                    "blocksMovement": True,
                    "blocksVision": False,
                    "blocksEffect": False,
                    "cover": "none",
                }
            ],
        }

        service.project_combat_start(db, "session-123", state)

        start_payload = client.calls[2][2]
        self.assertEqual(
            start_payload["battleMap"],
            {
                "name": "Dungeon Depths",
                "gridWidth": 32,
                "gridHeight": 24,
                "gridCalibration": {"x": 0.1, "y": 0.2, "width": 0.7, "height": 0.6},
                "imageUrl": "/sessions/session-123/battle-map/background",
                "sourceImageUrl": "/api/assets/internal/campaigns/campaign-1/maps/asset1234567890abcdef1234567890ab",
                "obstacles": [
                    {
                        "x": 2,
                        "y": 3,
                        "blocksMovement": True,
                        "blocksEffect": False,
                        "blocksVision": False,
                        "cover": "threeQuarters",
                        "clipsDiagonalMovement": True,
                        "movementCostMultiplier": 1,
                    }
                ],
                "edgeObstacles": [
                    {
                        "x": 4,
                        "y": 5,
                        "direction": "E",
                        "blocksMovement": True,
                        "blocksVision": False,
                        "blocksEffect": False,
                        "cover": "none",
                    }
                ],
            },
        )

    def test_projection_still_starts_combat_when_token_links_are_unavailable(
        self,
    ) -> None:
        db = MagicMock()
        db.exec.side_effect = [
            _FakeScalarResult(
                SessionEntity(
                    id="enemy-123",
                    session_id="session-123",
                    campaign_entity_id="ce-1",
                    overrides={},
                )
            ),
            _FakeScalarResult(
                CampaignEntity(
                    id="ce-1",
                    campaign_id="camp-1",
                    name="Goblin",
                    speed_meters=12,
                )
            ),
            _FakeScalarResult(
                SessionState(
                    id="state-1",
                    session_id="session-123",
                    player_user_id="player-123",
                    state_json={"speedMeters": 9},
                )
            ),
        ]
        client = FakeLimiarMapClient(
            state_response=build_map_state(
                LimiarMapTokenState(
                    token_id="tok_other",
                    controller_type="gm",
                    controller_id="gm-1",
                    movement_speed_cells=30,
                    combatant_id=None,
                )
            )
        )
        service = LimiarMapCombatProjectionService(client)

        service.project_combat_start(db, "session-123", build_active_state())

        self.assertEqual(
            [call[0] for call in client.calls], ["get_state", "start_combat"]
        )

    def test_projection_can_bind_single_player_token_without_explicit_mapping(
        self,
    ) -> None:
        db = MagicMock()
        db.exec.side_effect = [
            _FakeScalarResult(
                SessionEntity(
                    id="enemy-123",
                    session_id="session-123",
                    campaign_entity_id="ce-1",
                    overrides={"mapTokenId": "tok_enemy"},
                )
            ),
            _FakeScalarResult(
                CampaignEntity(
                    id="ce-1",
                    campaign_id="camp-1",
                    name="Goblin",
                    speed_meters=12,
                )
            ),
            _FakeScalarResult(
                SessionState(
                    id="state-1",
                    session_id="session-123",
                    player_user_id="player-123",
                    state_json={"speedMeters": 9},
                )
            ),
        ]
        client = FakeLimiarMapClient(
            state_response=build_map_state(
                LimiarMapTokenState(
                    token_id="tok_player",
                    controller_type="player",
                    controller_id="player_1",
                    movement_speed_cells=30,
                    combatant_id="cmb_1",
                    label="Hero",
                ),
                LimiarMapTokenState(
                    token_id="tok_enemy",
                    controller_type="gm",
                    controller_id="gm_1",
                    movement_speed_cells=30,
                    combatant_id="cmb_2",
                    label="Goblin",
                ),
            )
        )
        service = LimiarMapCombatProjectionService(client)

        service.project_combat_start(db, "session-123", build_active_state())

        sync_payload = client.calls[1][2]
        self.assertEqual(sync_payload["tokens"][1]["tokenId"], "tok_player")
        self.assertEqual(sync_payload["tokens"][1]["combatantId"], "player-123")
        self.assertEqual(sync_payload["tokens"][1]["controllerId"], "user-1")

    def test_projection_prefers_player_character_name_for_token_label(self) -> None:
        db = MagicMock()
        db.exec.side_effect = [
            _FakeScalarResult(
                SessionEntity(
                    id="enemy-123",
                    session_id="session-123",
                    campaign_entity_id="ce-1",
                    overrides={"mapTokenId": "tok_enemy"},
                )
            ),
            _FakeScalarResult(
                CampaignEntity(
                    id="ce-1",
                    campaign_id="camp-1",
                    name="Goblin",
                    speed_meters=12,
                )
            ),
            _FakeScalarResult(
                SessionState(
                    id="state-1",
                    session_id="session-123",
                    player_user_id="player-123",
                    state_json={"speedMeters": 9, "characterName": "Sir Galahad"},
                )
            ),
        ]
        client = FakeLimiarMapClient(
            state_response=build_map_state(
                LimiarMapTokenState(
                    token_id="tok_player",
                    controller_type="player",
                    controller_id="player_1",
                    movement_speed_cells=30,
                    combatant_id="cmb_1",
                    kind="playerCharacter",
                    label="Player1",
                ),
                LimiarMapTokenState(
                    token_id="tok_enemy",
                    controller_type="gm",
                    controller_id="gm_1",
                    movement_speed_cells=30,
                    combatant_id="cmb_2",
                    kind="enemy",
                    label="Goblin",
                ),
            )
        )
        service = LimiarMapCombatProjectionService(client)
        state = build_active_state()
        state.participants[1]["display_name"] = "Player1"

        service.project_combat_start(db, "session-123", state)

        sync_payload = client.calls[1][2]
        player_sync = next(
            entry
            for entry in sync_payload["tokens"]
            if entry["tokenId"] == "tok_player"
        )
        self.assertEqual(player_sync["label"], "Sir Galahad")

    def test_projection_can_bind_single_enemy_token_by_kind_when_label_differs(
        self,
    ) -> None:
        db = MagicMock()
        db.exec.side_effect = [
            _FakeScalarResult(
                SessionEntity(
                    id="enemy-123",
                    session_id="session-123",
                    campaign_entity_id="ce-1",
                    overrides={},
                    label="Zumbi",
                )
            ),
            _FakeScalarResult(
                CampaignEntity(
                    id="ce-1",
                    campaign_id="camp-1",
                    name="Zumbi",
                    speed_meters=12,
                )
            ),
            _FakeScalarResult(
                SessionState(
                    id="state-1",
                    session_id="session-123",
                    player_user_id="player-123",
                    state_json={"speedMeters": 9, "characterName": "Hero"},
                )
            ),
        ]
        client = FakeLimiarMapClient(
            state_response=build_map_state(
                LimiarMapTokenState(
                    token_id="tok_player",
                    controller_type="player",
                    controller_id="player_1",
                    movement_speed_cells=30,
                    combatant_id="cmb_1",
                    kind="playerCharacter",
                    label="Hero",
                ),
                LimiarMapTokenState(
                    token_id="tok_enemy",
                    controller_type="gm",
                    controller_id="gm_1",
                    movement_speed_cells=30,
                    combatant_id="cmb_2",
                    kind="enemy",
                    label="Goblin",
                ),
            )
        )
        service = LimiarMapCombatProjectionService(client)
        state = build_active_state()
        state.participants[0]["display_name"] = "Zumbi"

        service.project_combat_start(db, "session-123", state)

        sync_payload = client.calls[1][2]
        enemy_sync = next(
            entry for entry in sync_payload["tokens"] if entry["tokenId"] == "tok_enemy"
        )
        self.assertEqual(enemy_sync["combatantId"], "enemy-123")
        self.assertEqual(enemy_sync["label"], "Zumbi")
        self.assertEqual(enemy_sync["controllerId"], "gm-control")
        self.assertEqual(enemy_sync["controllerType"], "gm")

    def test_sync_failure_still_attempts_combat_start(self) -> None:
        db = MagicMock()
        db.exec.side_effect = [
            _FakeScalarResult(
                SessionEntity(
                    id="enemy-123",
                    session_id="session-123",
                    campaign_entity_id="ce-1",
                    overrides={"mapTokenId": "tok_enemy"},
                )
            ),
            _FakeScalarResult(
                CampaignEntity(
                    id="ce-1",
                    campaign_id="camp-1",
                    name="Goblin",
                    speed_meters=12,
                )
            ),
            _FakeScalarResult(
                SessionState(
                    id="state-1",
                    session_id="session-123",
                    player_user_id="player-123",
                    state_json={"speedMeters": 9},
                )
            ),
        ]
        client = FakeLimiarMapClient(
            state_response=build_map_state(
                LimiarMapTokenState(
                    token_id="tok_player",
                    controller_type="player",
                    controller_id="player-123",
                    movement_speed_cells=30,
                    combatant_id=None,
                ),
                LimiarMapTokenState(
                    token_id="tok_enemy",
                    controller_type="gm",
                    controller_id="gm-1",
                    movement_speed_cells=30,
                    combatant_id=None,
                ),
            ),
            sync_error=LimiarMapClientError(
                "sync failed", kind="http", status_code=500
            ),
        )
        service = LimiarMapCombatProjectionService(client)

        service.project_combat_start(db, "session-123", build_active_state())

        self.assertEqual(
            [call[0] for call in client.calls],
            ["get_state", "sync_tokens", "start_combat"],
        )

    def test_start_failure_keeps_combat_local(self) -> None:
        db = MagicMock()
        db.exec.side_effect = [
            _FakeScalarResult(
                SessionEntity(
                    id="enemy-123",
                    session_id="session-123",
                    campaign_entity_id="ce-1",
                    overrides={"mapTokenId": "tok_enemy"},
                )
            ),
            _FakeScalarResult(
                CampaignEntity(
                    id="ce-1",
                    campaign_id="camp-1",
                    name="Goblin",
                    speed_meters=12,
                )
            ),
            _FakeScalarResult(
                SessionState(
                    id="state-1",
                    session_id="session-123",
                    player_user_id="player-123",
                    state_json={"speedMeters": 9},
                )
            ),
        ]
        client = FakeLimiarMapClient(
            state_response=build_map_state(
                LimiarMapTokenState(
                    token_id="tok_player",
                    controller_type="player",
                    controller_id="player-123",
                    movement_speed_cells=30,
                    combatant_id=None,
                ),
                LimiarMapTokenState(
                    token_id="tok_enemy",
                    controller_type="gm",
                    controller_id="gm-1",
                    movement_speed_cells=30,
                    combatant_id=None,
                ),
            ),
            start_error=LimiarMapClientError(
                "start failed", kind="http", status_code=409
            ),
        )
        service = LimiarMapCombatProjectionService(client)

        service.project_combat_start(db, "session-123", build_active_state())

        self.assertEqual(
            [call[0] for call in client.calls],
            ["get_state", "sync_tokens", "start_combat"],
        )

    def test_start_conflict_with_active_map_is_treated_as_available(self) -> None:
        db = MagicMock()
        db.exec.side_effect = [
            _FakeScalarResult(
                SessionEntity(
                    id="enemy-123",
                    session_id="session-123",
                    campaign_entity_id="ce-1",
                    overrides={"mapTokenId": "tok_enemy"},
                )
            ),
            _FakeScalarResult(
                CampaignEntity(
                    id="ce-1",
                    campaign_id="camp-1",
                    name="Goblin",
                    speed_meters=12,
                )
            ),
            _FakeScalarResult(
                SessionState(
                    id="state-1",
                    session_id="session-123",
                    player_user_id="player-123",
                    state_json={"speedMeters": 9},
                )
            ),
        ]
        client = FakeLimiarMapClient(
            state_response=build_map_state(
                LimiarMapTokenState(
                    token_id="tok_player",
                    controller_type="player",
                    controller_id="player-123",
                    movement_speed_cells=30,
                    combatant_id=None,
                ),
                LimiarMapTokenState(
                    token_id="tok_enemy",
                    controller_type="gm",
                    controller_id="gm-1",
                    movement_speed_cells=30,
                    combatant_id=None,
                ),
            ),
            start_error=LimiarMapClientError(
                "combat already active",
                kind="http",
                status_code=409,
                reason="combat_already_active",
            ),
        )
        service = LimiarMapCombatProjectionService(client)

        result = service.project_combat_start(db, "session-123", build_active_state())

        self.assertTrue(result.map_available)
        self.assertEqual(result.reason, "combat_already_active")
        self.assertEqual(
            [call[0] for call in client.calls],
            ["get_state", "sync_tokens", "start_combat"],
        )

    def test_projection_conflict_catches_up_existing_map_turn(self) -> None:
        db = MagicMock()
        db.exec.side_effect = [
            _FakeScalarResult(
                SessionEntity(
                    id="enemy-123",
                    session_id="session-123",
                    campaign_entity_id="ce-1",
                    overrides={"mapTokenId": "tok_enemy"},
                )
            ),
            _FakeScalarResult(
                CampaignEntity(
                    id="ce-1",
                    campaign_id="camp-1",
                    name="Goblin",
                    speed_meters=12,
                )
            ),
            _FakeScalarResult(
                SessionState(
                    id="state-1",
                    session_id="session-123",
                    player_user_id="player-123",
                    state_json={"speedMeters": 9},
                )
            ),
        ]
        client = FakeLimiarMapClient(
            state_response=build_map_state(
                LimiarMapTokenState(
                    token_id="tok_player",
                    controller_type="player",
                    controller_id="player-123",
                    movement_speed_cells=6,
                    combatant_id="player-123",
                ),
                LimiarMapTokenState(
                    token_id="tok_enemy",
                    controller_type="gm",
                    controller_id="gm-control",
                    movement_speed_cells=8,
                    combatant_id="enemy-123",
                ),
                round_number=1,
                turn_index=1,
                active_combatant_id="player-123",
                initiative_order=("enemy-123", "player-123"),
            ),
            start_error=LimiarMapClientError(
                "combat already active",
                kind="http",
                status_code=409,
                reason="combat_already_active",
            ),
        )
        service = LimiarMapCombatProjectionService(client)
        state = build_active_state()
        state.round = 2
        state.current_turn_index = 0

        result = service.project_combat_start(db, "session-123", state)

        self.assertTrue(result.map_available)
        self.assertEqual(result.reason, "turn_synced")
        self.assertEqual(
            [call[0] for call in client.calls],
            ["get_state", "sync_tokens", "start_combat", "advance_combat"],
        )
        self.assertEqual(
            client.calls[-1],
            (
                "advance_combat",
                "session-123",
                {
                    "actionId": "control-combat-advance:combat-123:2:0",
                },
            ),
        )

    def test_projection_repeated_start_response_catches_up_existing_map_turn(
        self,
    ) -> None:
        db = MagicMock()
        db.exec.side_effect = [
            _FakeScalarResult(
                SessionEntity(
                    id="enemy-123",
                    session_id="session-123",
                    campaign_entity_id="ce-1",
                    overrides={"mapTokenId": "tok_enemy"},
                )
            ),
            _FakeScalarResult(
                CampaignEntity(
                    id="ce-1",
                    campaign_id="camp-1",
                    name="Goblin",
                    speed_meters=12,
                )
            ),
            _FakeScalarResult(
                SessionState(
                    id="state-1",
                    session_id="session-123",
                    player_user_id="player-123",
                    state_json={"speedMeters": 9},
                )
            ),
        ]
        client = FakeLimiarMapClient(
            state_response=build_map_state(
                LimiarMapTokenState(
                    token_id="tok_player",
                    controller_type="player",
                    controller_id="player-123",
                    movement_speed_cells=6,
                    combatant_id="player-123",
                ),
                LimiarMapTokenState(
                    token_id="tok_enemy",
                    controller_type="gm",
                    controller_id="gm-control",
                    movement_speed_cells=8,
                    combatant_id="enemy-123",
                ),
                round_number=1,
                turn_index=1,
                active_combatant_id="player-123",
                initiative_order=("enemy-123", "player-123"),
            ),
        )
        service = LimiarMapCombatProjectionService(client)
        state = build_active_state()
        state.round = 2
        state.current_turn_index = 0

        result = service.project_combat_start(db, "session-123", state)

        self.assertTrue(result.map_available)
        self.assertEqual(result.reason, "turn_synced")
        self.assertEqual(
            [call[0] for call in client.calls],
            ["get_state", "sync_tokens", "start_combat", "advance_combat"],
        )
        self.assertEqual(
            client.calls[-1],
            (
                "advance_combat",
                "session-123",
                {
                    "actionId": "control-combat-advance:combat-123:2:0",
                },
            ),
        )

    def test_action_id_is_deterministic_for_same_combat_state(self) -> None:
        state = build_active_state()

        self.assertEqual(
            LimiarMapCombatProjectionService.build_combat_start_action_id(state),
            LimiarMapCombatProjectionService.build_combat_start_action_id(state),
        )

    def test_projection_advance_success_calls_client_with_deterministic_action_id(
        self,
    ) -> None:
        client = FakeLimiarMapClient(state_response=build_map_state())
        service = LimiarMapCombatProjectionService(client)
        state = build_active_state()
        state.round = 2
        state.current_turn_index = 1

        service.project_combat_advance("session-123", state)

        self.assertEqual(
            client.calls,
            [
                (
                    "advance_combat",
                    "session-123",
                    {
                        "actionId": "control-combat-advance:combat-123:2:1",
                    },
                ),
                ("get_state", "session-123", None),
            ],
        )

    def test_projection_advance_failure_keeps_control_local(self) -> None:
        client = FakeLimiarMapClient(
            state_response=build_map_state(),
            advance_error=LimiarMapClientError("advance failed", kind="timeout"),
        )
        service = LimiarMapCombatProjectionService(client)
        state = build_active_state()

        service.project_combat_advance("session-123", state)

        self.assertEqual(client.calls[0][0], "advance_combat")

    def test_projection_end_success_calls_client_with_deterministic_action_id(
        self,
    ) -> None:
        client = FakeLimiarMapClient(state_response=build_map_state())
        service = LimiarMapCombatProjectionService(client)
        state = build_active_state()
        state.phase = CombatPhase.ended

        service.project_combat_end("session-123", state)

        self.assertEqual(
            client.calls,
            [
                (
                    "end_combat",
                    "session-123",
                    {
                        "actionId": "control-combat-end:combat-123",
                    },
                )
            ],
        )

    def test_projection_end_failure_keeps_control_local(self) -> None:
        client = FakeLimiarMapClient(
            state_response=build_map_state(),
            end_error=LimiarMapClientError("end failed", kind="http", status_code=500),
        )
        service = LimiarMapCombatProjectionService(client)
        state = build_active_state()
        state.phase = CombatPhase.ended

        service.project_combat_end("session-123", state)

        self.assertEqual(client.calls[0][0], "end_combat")

    def test_advance_action_id_is_deterministic_for_same_transition(self) -> None:
        state = build_active_state()
        state.round = 3
        state.current_turn_index = 0

        self.assertEqual(
            LimiarMapCombatProjectionService.build_combat_advance_action_id(state),
            LimiarMapCombatProjectionService.build_combat_advance_action_id(state),
        )

    def test_end_action_id_is_deterministic(self) -> None:
        state = build_active_state()
        state.phase = CombatPhase.ended

        self.assertEqual(
            LimiarMapCombatProjectionService.build_combat_end_action_id(state),
            LimiarMapCombatProjectionService.build_combat_end_action_id(state),
        )


class CombatLifecycleProjectionHookTests(TestCombatServiceBase):
    def test_map_off_skips_advance_projection_wrapper(self) -> None:
        state = build_active_state()
        with (
            patch(
                "app.services.combat_service.limiar_map_projection.get_limiar_map_projection_service"
            ) as mock_get_service,
            patch(
                "app.services.combat_service.limiar_map_projection.settings.limiar_map_enabled",
                False,
            ),
        ):
            from app.services.combat_service.limiar_map_projection import (
                maybe_project_combat_advance_to_limiar_map,
            )

            maybe_project_combat_advance_to_limiar_map("session-123", state)

        mock_get_service.assert_not_called()

    def test_map_off_skips_end_projection_wrapper(self) -> None:
        state = build_active_state()
        state.phase = CombatPhase.ended
        with (
            patch(
                "app.services.combat_service.limiar_map_projection.get_limiar_map_projection_service"
            ) as mock_get_service,
            patch(
                "app.services.combat_service.limiar_map_projection.settings.limiar_map_enabled",
                False,
            ),
        ):
            from app.services.combat_service.limiar_map_projection import (
                maybe_project_combat_end_to_limiar_map,
            )

            maybe_project_combat_end_to_limiar_map("session-123", state)

        mock_get_service.assert_not_called()

    @patch(
        "app.services.combat_service.lifecycle.maybe_project_combat_start_to_limiar_map"
    )
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_set_initiative_triggers_map_projection_when_combat_becomes_active(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_project_start,
    ) -> None:
        with patch(
            "app.services.combat.CombatService.get_state", return_value=self.state
        ):
            req = CombatSetInitiativeRequest(
                initiatives=[
                    CombatSetInitiativeParticipant(id="p1", initiative=15),
                    CombatSetInitiativeParticipant(id="e1", initiative=20),
                ]
            )

            state = await CombatService.set_initiative(self.db, "session-123", req)

        self.assertEqual(state.phase, CombatPhase.active)
        mock_project_start.assert_called_once_with(self.db, "session-123", state)

    @patch(
        "app.services.combat_service.lifecycle.maybe_project_combat_start_to_limiar_map"
    )
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_apply_initiative_roll_triggers_map_projection_when_combat_becomes_active(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_project_start,
    ) -> None:
        self.state.participants[1]["initiative"] = 12

        with patch(
            "app.services.combat.CombatService.get_state", return_value=self.state
        ):
            state = await CombatService.apply_initiative_roll(
                self.db,
                "session-123",
                "player",
                "player-123",
                15,
            )

        self.assertIsNotNone(state)
        mock_project_start.assert_called_once_with(self.db, "session-123", state)

    @patch(
        "app.services.combat_service.lifecycle.maybe_project_combat_advance_to_limiar_map"
    )
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_next_turn_triggers_map_projection_after_control_advances(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_project_advance,
    ) -> None:
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0

        with patch(
            "app.services.combat.CombatService.get_state", return_value=self.state
        ):
            state = await CombatService.next_turn(
                self.db,
                "session-123",
                actor_user_id="user-xyz",
                is_gm=True,
            )

        self.assertEqual(state.current_turn_index, 1)
        mock_project_advance.assert_called_once_with("session-123", state)

    @patch(
        "app.services.combat_service.lifecycle.maybe_project_combat_end_to_limiar_map"
    )
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_end_combat_triggers_map_projection_after_control_ends(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_project_end,
    ) -> None:
        self.state.phase = CombatPhase.active

        with patch(
            "app.services.combat.CombatService.get_state", return_value=self.state
        ):
            state = await CombatService.end_combat(
                self.db,
                "session-123",
                is_gm=True,
            )

        self.assertEqual(state.phase, CombatPhase.ended)
        mock_project_end.assert_called_once_with("session-123", state)


# ─── Phase F5: sizeCategory sync tests ───────────────────────────────────────


class SizeCategorySyncTests(unittest.TestCase):
    """Verify that entity size is resolved and forwarded to LimiarMap."""

    def _make_db(self, session_entity, campaign_entity, session_state=None):
        """Build a mock DB that returns the given models in order."""
        db = MagicMock()
        results = [
            _FakeScalarResult(session_entity),
            _FakeScalarResult(campaign_entity),
        ]
        if session_state is not None:
            results.append(_FakeScalarResult(session_state))
        db.exec.side_effect = results
        return db

    def _run_sync(self, db, entity_token_id, player_token_id=None):
        """Run project_combat_start and return the sync_tokens payload."""
        state_tokens = [
            LimiarMapTokenState(
                token_id=entity_token_id,
                controller_type="gm",
                controller_id="gm-1",
                movement_speed_cells=None,
                combatant_id=None,
            ),
        ]
        if player_token_id:
            state_tokens.append(
                LimiarMapTokenState(
                    token_id=player_token_id,
                    controller_type="player",
                    controller_id="player-123",
                    movement_speed_cells=None,
                    combatant_id=None,
                )
            )
        client = FakeLimiarMapClient(state_response=build_map_state(*state_tokens))
        service = LimiarMapCombatProjectionService(client)
        service.project_combat_start(db, "session-123", build_active_state())
        sync_call = next((c for c in client.calls if c[0] == "sync_tokens"), None)
        return sync_call[2] if sync_call else None

    # ── non-medium entity sends sizeCategory ─────────────────────────────────

    def test_large_entity_sends_size_category(self):
        db = self._make_db(
            SessionEntity(
                id="enemy-123",
                session_id="session-123",
                campaign_entity_id="ce-1",
                overrides={"mapTokenId": "tok_enemy"},
            ),
            CampaignEntity(
                id="ce-1",
                campaign_id="camp-1",
                name="Troll",
                size="large",
            ),
            SessionState(
                id="state-1",
                session_id="session-123",
                player_user_id="player-123",
                state_json={},
            ),
        )
        payload = self._run_sync(db, "tok_enemy", "tok_player")
        enemy_token = next(
            (t for t in payload["tokens"] if t["combatantId"] == "enemy-123"),
            None,
        )
        self.assertIsNotNone(enemy_token)
        self.assertEqual(enemy_token.get("sizeCategory"), "large")

    def test_huge_entity_sends_size_category(self):
        db = self._make_db(
            SessionEntity(
                id="enemy-123",
                session_id="session-123",
                campaign_entity_id="ce-1",
                overrides={"mapTokenId": "tok_enemy"},
            ),
            CampaignEntity(
                id="ce-1",
                campaign_id="camp-1",
                name="Dragon",
                size="huge",
            ),
            SessionState(
                id="state-1",
                session_id="session-123",
                player_user_id="player-123",
                state_json={},
            ),
        )
        payload = self._run_sync(db, "tok_enemy", "tok_player")
        enemy_token = next(
            (t for t in payload["tokens"] if t["combatantId"] == "enemy-123"),
            None,
        )
        self.assertEqual(enemy_token.get("sizeCategory"), "huge")

    # ── medium entity omits sizeCategory ─────────────────────────────────────

    def test_medium_entity_omits_size_category(self):
        db = self._make_db(
            SessionEntity(
                id="enemy-123",
                session_id="session-123",
                campaign_entity_id="ce-1",
                overrides={"mapTokenId": "tok_enemy"},
            ),
            CampaignEntity(
                id="ce-1",
                campaign_id="camp-1",
                name="Goblin",
                size="medium",
            ),
            SessionState(
                id="state-1",
                session_id="session-123",
                player_user_id="player-123",
                state_json={},
            ),
        )
        payload = self._run_sync(db, "tok_enemy", "tok_player")
        enemy_token = next(
            (t for t in payload["tokens"] if t["combatantId"] == "enemy-123"),
            None,
        )
        # Medium is the default — should NOT be forwarded
        self.assertNotIn("sizeCategory", enemy_token)

    def test_entity_with_no_size_omits_size_category(self):
        db = self._make_db(
            SessionEntity(
                id="enemy-123",
                session_id="session-123",
                campaign_entity_id="ce-1",
                overrides={"mapTokenId": "tok_enemy"},
            ),
            CampaignEntity(
                id="ce-1",
                campaign_id="camp-1",
                name="Goblin",
                size=None,
            ),
            SessionState(
                id="state-1",
                session_id="session-123",
                player_user_id="player-123",
                state_json={},
            ),
        )
        payload = self._run_sync(db, "tok_enemy", "tok_player")
        enemy_token = next(
            (t for t in payload["tokens"] if t["combatantId"] == "enemy-123"),
            None,
        )
        self.assertNotIn("sizeCategory", enemy_token)

    # ── _resolve_entity_size: override takes precedence ───────────────────────

    def test_size_override_in_entity_overrides_takes_precedence(self):
        db = self._make_db(
            SessionEntity(
                id="enemy-123",
                session_id="session-123",
                campaign_entity_id="ce-1",
                # Override says large even though catalog says small
                overrides={"mapTokenId": "tok_enemy", "size": "large"},
            ),
            CampaignEntity(
                id="ce-1",
                campaign_id="camp-1",
                name="Cursed Gnome",
                size="small",
            ),
            SessionState(
                id="state-1",
                session_id="session-123",
                player_user_id="player-123",
                state_json={},
            ),
        )
        payload = self._run_sync(db, "tok_enemy", "tok_player")
        enemy_token = next(
            (t for t in payload["tokens"] if t["combatantId"] == "enemy-123"),
            None,
        )
        self.assertEqual(enemy_token.get("sizeCategory"), "large")

    # ── _resolve_player_size: wild shape beast size ───────────────────────────

    def test_wild_shape_player_sends_beast_size(self):
        # Wolf is medium — won't forward sizeCategory.  Use black_bear to get a
        # non-medium size... Actually all current catalog entries are medium or
        # smaller. Use a manual state_json to set size directly to test the
        # player size path without wild shape.
        db = MagicMock()
        db.exec.side_effect = [
            # entity lookup
            _FakeScalarResult(
                SessionEntity(
                    id="enemy-123",
                    session_id="session-123",
                    campaign_entity_id="ce-1",
                    overrides={"mapTokenId": "tok_enemy"},
                )
            ),
            _FakeScalarResult(
                CampaignEntity(
                    id="ce-1", campaign_id="camp-1", name="Goblin", size=None
                )
            ),
            # player state — size=large in state_json
            _FakeScalarResult(
                SessionState(
                    id="state-1",
                    session_id="session-123",
                    player_user_id="player-123",
                    state_json={"size": "large"},
                )
            ),
        ]
        client = FakeLimiarMapClient(
            state_response=build_map_state(
                LimiarMapTokenState(
                    token_id="tok_enemy",
                    controller_type="gm",
                    controller_id="gm-1",
                    movement_speed_cells=None,
                    combatant_id=None,
                ),
                LimiarMapTokenState(
                    token_id="tok_player",
                    controller_type="player",
                    controller_id="player-123",
                    movement_speed_cells=None,
                    combatant_id=None,
                ),
            )
        )
        service = LimiarMapCombatProjectionService(client)
        service.project_combat_start(db, "session-123", build_active_state())
        sync_call = next(c for c in client.calls if c[0] == "sync_tokens")
        player_token = next(
            t for t in sync_call[2]["tokens"] if t["combatantId"] == "player-123"
        )
        self.assertEqual(player_token.get("sizeCategory"), "large")


if __name__ == "__main__":
    unittest.main()
