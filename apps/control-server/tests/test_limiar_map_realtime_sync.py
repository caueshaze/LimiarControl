from __future__ import annotations

import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.integrations.limiar_map_client import (
    LimiarMapClientError,
    LimiarMapStateResponse,
    LimiarMapTokenState,
)
import app.integrations.limiar_map_realtime_client as realtime_module
from app.integrations.limiar_map_realtime_client import (
    LimiarMapRealtimeSyncService,
)


class FakeClock:
    def __init__(self, now: float = 100.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class FakeHttpClient:
    def __init__(self, *responses_or_errors: object) -> None:
        self._responses_or_errors = list(responses_or_errors)
        self.calls: list[str] = []

    def get_session_state(self, session_id: str) -> LimiarMapStateResponse:
        self.calls.append(session_id)
        if not self._responses_or_errors:
            raise AssertionError("FakeHttpClient requires a queued response or error")
        next_result = self._responses_or_errors.pop(0)
        if isinstance(next_result, Exception):
            raise next_result
        if not isinstance(next_result, LimiarMapStateResponse):
            raise AssertionError("Unexpected fake response type")
        return next_result


class FakeRealtimeClient:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


def build_snapshot(version: int = 4) -> LimiarMapStateResponse:
    return LimiarMapStateResponse(
        session_id="session-123",
        version=version,
        active_combatant_id="player-123",
        tokens=(
            LimiarMapTokenState(
                token_id="tok-player",
                controller_type="player",
                controller_id="player-123",
                movement_speed_cells=6,
                combatant_id="player-123",
                position_x=4,
                position_y=5,
            ),
            LimiarMapTokenState(
                token_id="tok-enemy",
                controller_type="gm",
                controller_id="gm-1",
                movement_speed_cells=6,
                combatant_id="enemy-123",
                position_x=10,
                position_y=11,
            ),
        ),
    )


class LimiarMapRealtimeSyncServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.http_client = FakeHttpClient(build_snapshot())
        self.realtime_client = FakeRealtimeClient()
        self.service = LimiarMapRealtimeSyncService(
            http_client=self.http_client,
            realtime_client=self.realtime_client,
            now_provider=self.clock,
        )

    def tearDown(self) -> None:
        realtime_module.reset_limiar_map_realtime_sync_service()

    def test_start_and_stop_delegate_to_realtime_client(self) -> None:
        self.service.start()
        self.service.stop()

        self.assertTrue(self.realtime_client.started)
        self.assertTrue(self.realtime_client.stopped)

    def test_default_service_builds_centrifugo_stream(self) -> None:
        constructed: dict[str, object] = {}

        class FakeConstructedRealtimeClient:
            def __init__(self, *, ws_url, event_handler, channels):
                constructed["ws_url"] = ws_url
                constructed["event_handler"] = event_handler
                constructed["channels"] = channels

            def start(self) -> None:
                constructed["started"] = True

            def stop(self) -> None:
                constructed["stopped"] = True

        fake_centrifugo_module = SimpleNamespace(
            LimiarMapCentrifugoClient=FakeConstructedRealtimeClient,
            MAP_SYSTEM_EVENTS_CHANNEL="system:map_events",
        )

        with (
            patch.dict(
                sys.modules,
                {
                    "app.integrations.limiar_map_centrifugo_client": fake_centrifugo_module
                },
            ),
            patch.object(
                realtime_module.settings,
                "centrifugo_public_url",
                "ws://centrifugo.local/connection/websocket",
            ),
        ):
            service = LimiarMapRealtimeSyncService(
                http_client=self.http_client,
                now_provider=self.clock,
            )

        self.assertEqual(
            constructed["ws_url"],
            "ws://centrifugo.local/connection/websocket",
        )
        self.assertEqual(constructed["channels"], ("system:map_events",))
        self.assertTrue(callable(constructed["event_handler"]))

        service.start()
        service.stop()

        self.assertTrue(constructed["started"])
        self.assertTrue(constructed["stopped"])

    def test_manual_resync_updates_local_state_and_clears_drift(self) -> None:
        self.service.handle_event(
            "action.rejected",
            {
                "encounterId": "session-123",
                "version": 3,
                "actionId": "control-combat-start:combat-1",
                "payload": {"reason": "unknown", "message": "failed"},
            },
        )
        self.assertTrue(self.service.is_out_of_sync("session-123"))

        self.clock.now = 105.0
        state = self.service.resync_session("session-123", reason="manual")

        self.assertIsNotNone(state)
        self.assertEqual(self.http_client.calls, ["session-123"])
        self.assertEqual(state.last_known_map_version, 4)
        self.assertFalse(state.out_of_sync)
        self.assertEqual(state.last_active_combatant_id, "player-123")
        self.assertEqual(state.last_resync_at, 105.0)
        self.assertEqual(state.last_resync_reason, "manual")
        self.assertEqual(state.consecutive_resync_failures, 0)

    def test_tokens_synced_event_populates_known_positions(self) -> None:
        self.service.handle_event(
            "tokens.synced",
            {
                "encounterId": "session-123",
                "version": 2,
                "payload": {
                    "tokens": [
                        {
                            "id": "tok-player",
                            "combatantId": "player-123",
                            "position": {"x": 3, "y": 4},
                        }
                    ]
                },
            },
        )

        state = self.service.get_session_state("session-123")

        self.assertIsNotNone(state)
        self.assertEqual(state.last_known_map_version, 2)
        self.assertEqual(state.last_event_at, 100.0)
        self.assertEqual(state.token_positions["tok-player"].position_x, 3)
        self.assertEqual(state.token_positions["tok-player"].combatant_id, "player-123")

    def test_movement_event_updates_token_position_incrementally(self) -> None:
        self.service.resync_session("session-123", reason="bootstrap")

        self.clock.now = 101.0
        self.service.handle_event(
            "movement.applied",
            {
                "encounterId": "session-123",
                "version": 5,
                "actionId": "move-1",
                "payload": {
                    "tokenId": "tok-player",
                    "position": {"x": 6, "y": 7},
                    "pathCostUnits": 5,
                    "remainingBudget": 25,
                },
            },
        )

        state = self.service.get_session_state("session-123")

        self.assertIsNotNone(state)
        self.assertEqual(state.last_known_map_version, 5)
        self.assertEqual(state.token_positions["tok-player"].position_x, 6)
        self.assertEqual(state.token_positions["tok-player"].position_y, 7)

    def test_combat_advanced_event_updates_active_combatant(self) -> None:
        self.service.handle_event(
            "combat.advanced",
            {
                "encounterId": "session-123",
                "version": 2,
                "actionId": "control-combat-advance:combat-1:1:1",
                "payload": {
                    "roundNumber": 1,
                    "turnIndex": 1,
                    "activeCombatantId": "enemy-123",
                },
            },
        )

        state = self.service.get_session_state("session-123")

        self.assertIsNotNone(state)
        self.assertEqual(state.last_active_combatant_id, "enemy-123")

    def test_combat_ended_event_clears_active_combatant(self) -> None:
        self.service.resync_session("session-123", reason="bootstrap")

        self.clock.now = 101.0
        self.service.handle_event(
            "combat.ended",
            {
                "encounterId": "session-123",
                "version": 5,
                "actionId": "control-combat-end:combat-1",
                "payload": {"roundNumber": 2},
            },
        )

        state = self.service.get_session_state("session-123")

        self.assertIsNotNone(state)
        self.assertIsNone(state.last_active_combatant_id)

    def test_eligible_drift_triggers_auto_resync(self) -> None:
        self.service.handle_event(
            "tokens.synced",
            {
                "encounterId": "session-123",
                "version": 2,
                "payload": {"tokens": []},
            },
        )

        self.clock.now = 110.0
        self.service.handle_event(
            "combat.advanced",
            {
                "encounterId": "session-123",
                "version": 4,
                "payload": {
                    "roundNumber": 1,
                    "turnIndex": 1,
                    "activeCombatantId": "enemy-123",
                },
            },
        )

        state = self.service.get_session_state("session-123")

        self.assertIsNotNone(state)
        self.assertEqual(self.http_client.calls, ["session-123"])
        self.assertFalse(state.out_of_sync)
        self.assertEqual(state.last_resync_reason, "version_gap")
        self.assertEqual(state.last_known_map_version, 4)

    def test_non_eligible_drift_does_not_trigger_auto_resync(self) -> None:
        self.service.handle_event(
            "action.rejected",
            {
                "encounterId": "session-123",
                "version": 7,
                "actionId": "control-combat-advance:combat-1:2:0",
                "payload": {"reason": "combat_not_active", "message": "rejected"},
            },
        )

        state = self.service.get_session_state("session-123")

        self.assertIsNotNone(state)
        self.assertEqual(self.http_client.calls, [])
        self.assertTrue(state.out_of_sync)
        self.assertEqual(state.drift_reason, "control_action_rejected")

    def test_cooldown_prevents_resync_loop(self) -> None:
        self.http_client = FakeHttpClient(
            LimiarMapClientError("map unavailable", kind="network"),
            build_snapshot(version=6),
        )
        self.service = LimiarMapRealtimeSyncService(
            http_client=self.http_client,
            realtime_client=self.realtime_client,
            now_provider=self.clock,
        )

        self.service.handle_event(
            "tokens.synced",
            {
                "encounterId": "session-123",
                "version": 2,
                "payload": {"tokens": []},
            },
        )
        self.clock.now = 101.0
        self.service.handle_event(
            "combat.advanced",
            {
                "encounterId": "session-123",
                "version": 4,
                "payload": {
                    "roundNumber": 1,
                    "turnIndex": 1,
                    "activeCombatantId": "enemy-123",
                },
            },
        )
        self.clock.now = 102.0
        self.service.handle_event(
            "combat.advanced",
            {
                "encounterId": "session-123",
                "version": 3,
                "payload": {
                    "roundNumber": 1,
                    "turnIndex": 0,
                    "activeCombatantId": "player-123",
                },
            },
        )

        state = self.service.get_session_state("session-123")

        self.assertIsNotNone(state)
        self.assertEqual(self.http_client.calls, ["session-123"])
        self.assertTrue(state.out_of_sync)
        self.assertEqual(state.consecutive_resync_failures, 1)

    def test_resync_in_progress_prevents_reentry(self) -> None:
        session_state = self.service.get_session_state("session-123")
        self.assertIsNone(session_state)
        self.service.handle_event(
            "tokens.synced",
            {
                "encounterId": "session-123",
                "version": 2,
                "payload": {"tokens": []},
            },
        )
        internal_state = self.service._sessions["session-123"]
        internal_state.resync_in_progress = True

        state = self.service.trigger_resync_if_needed(
            "session-123",
            reason="version_gap",
            version=3,
        )

        self.assertIsNotNone(state)
        self.assertEqual(self.http_client.calls, [])
        self.assertTrue(state.resync_in_progress)

    def test_resync_failure_increments_counter_and_keeps_session_marked(self) -> None:
        self.http_client = FakeHttpClient(
            LimiarMapClientError("map unavailable", kind="timeout")
        )
        self.service = LimiarMapRealtimeSyncService(
            http_client=self.http_client,
            realtime_client=self.realtime_client,
            now_provider=self.clock,
        )

        self.service.handle_event(
            "tokens.synced",
            {
                "encounterId": "session-123",
                "version": 2,
                "payload": {"tokens": []},
            },
        )
        self.clock.now = 101.0
        self.service.handle_event(
            "combat.advanced",
            {
                "encounterId": "session-123",
                "version": 4,
                "payload": {
                    "roundNumber": 1,
                    "turnIndex": 1,
                    "activeCombatantId": "enemy-123",
                },
            },
        )

        state = self.service.get_session_state("session-123")

        self.assertIsNotNone(state)
        self.assertTrue(state.out_of_sync)
        self.assertEqual(state.drift_reason, "version_gap")
        self.assertEqual(state.consecutive_resync_failures, 1)
        self.assertFalse(state.resync_in_progress)
        self.assertEqual(state.last_resync_reason, "version_gap")

    def test_multiple_out_of_order_events_do_not_create_resync_avalanche(self) -> None:
        self.http_client = FakeHttpClient(
            LimiarMapClientError("map unavailable", kind="network")
        )
        self.service = LimiarMapRealtimeSyncService(
            http_client=self.http_client,
            realtime_client=self.realtime_client,
            now_provider=self.clock,
        )

        self.service.handle_event(
            "combat.advanced",
            {
                "encounterId": "session-123",
                "version": 5,
                "payload": {
                    "roundNumber": 2,
                    "turnIndex": 0,
                    "activeCombatantId": "player-123",
                },
            },
        )
        self.service.handle_event(
            "tokens.synced",
            {
                "encounterId": "session-123",
                "version": 6,
                "payload": {"tokens": []},
            },
        )
        for step in (101.0, 102.0, 103.0):
            self.clock.now = step
            self.service.handle_event(
                "combat.advanced",
                {
                    "encounterId": "session-123",
                    "version": 4,
                    "payload": {
                        "roundNumber": 1,
                        "turnIndex": 1,
                        "activeCombatantId": "enemy-123",
                    },
                },
            )

        state = self.service.get_session_state("session-123")

        self.assertIsNotNone(state)
        self.assertEqual(self.http_client.calls, ["session-123"])
        self.assertTrue(state.out_of_sync)
        self.assertEqual(state.consecutive_resync_failures, 1)

    def test_unknown_token_movement_triggers_auto_resync_for_known_session(
        self,
    ) -> None:
        self.http_client = FakeHttpClient(
            build_snapshot(),
            build_snapshot(version=5),
        )
        self.service = LimiarMapRealtimeSyncService(
            http_client=self.http_client,
            realtime_client=self.realtime_client,
            now_provider=self.clock,
        )
        self.service.resync_session("session-123", reason="bootstrap")
        self.http_client.calls.clear()

        self.clock.now = 110.0
        self.service.handle_event(
            "movement.applied",
            {
                "encounterId": "session-123",
                "version": 5,
                "actionId": "move-1",
                "payload": {
                    "tokenId": "tok-missing",
                    "position": {"x": 8, "y": 9},
                    "pathCostUnits": 5,
                    "remainingBudget": 10,
                },
            },
        )

        state = self.service.get_session_state("session-123")

        self.assertIsNotNone(state)
        self.assertEqual(self.http_client.calls, ["session-123"])
        self.assertFalse(state.out_of_sync)
        self.assertEqual(state.last_resync_reason, "unknown_token_movement")

    def test_map_disabled_wrapper_returns_none(self) -> None:
        with patch.object(realtime_module.settings, "limiar_map_enabled", False):
            state = realtime_module.resync_limiar_map_session("session-123")

        self.assertIsNone(state)

    def test_map_disabled_start_wrapper_does_not_bootstrap_service(self) -> None:
        with (
            patch.object(realtime_module.settings, "limiar_map_enabled", False),
            patch.object(
                realtime_module, "get_limiar_map_realtime_sync_service"
            ) as mock_get_service,
        ):
            realtime_module.start_limiar_map_realtime_sync()

        mock_get_service.assert_not_called()

    def test_map_unavailable_does_not_crash_auto_resync_path(self) -> None:
        self.http_client = FakeHttpClient(RuntimeError("unexpected"))
        self.service = LimiarMapRealtimeSyncService(
            http_client=self.http_client,
            realtime_client=self.realtime_client,
            now_provider=self.clock,
        )

        self.service.handle_event(
            "tokens.synced",
            {
                "encounterId": "session-123",
                "version": 2,
                "payload": {"tokens": []},
            },
        )
        self.clock.now = 101.0
        self.service.handle_event(
            "combat.advanced",
            {
                "encounterId": "session-123",
                "version": 4,
                "payload": {
                    "roundNumber": 1,
                    "turnIndex": 1,
                    "activeCombatantId": "enemy-123",
                },
            },
        )

        state = self.service.get_session_state("session-123")

        self.assertIsNotNone(state)
        self.assertTrue(state.out_of_sync)
        self.assertEqual(state.consecutive_resync_failures, 1)


if __name__ == "__main__":
    unittest.main()
