from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.integrations.limiar_map_client import (
    LimiarMapAreaCell,
    LimiarMapAreaTargetingResponse,
    LimiarMapClientError,
    LimiarMapTargetingResponse,
)
from app.models.combat import CombatPhase, CombatState
from app.schemas.combat import CombatAttackRequest
from app.services.combat import CombatService, CombatServiceError
import app.services.combat_service.combat_targeting as combat_targeting
from app.services.combat_service.combat_targeting import (
    LimiarMapTargetingService,
    LocalCombatTargetingService,
)
from app.services.combat_service.targeting_intent import (
    AreaTargetingIntent,
    SpellCastIntent,
    WeaponAttackIntent,
)


class StubLimiarMapClient:
    def __init__(
        self,
        *,
        response: LimiarMapTargetingResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict] = []
        self.area_calls: list[dict] = []

    def validate_single_target(
        self,
        *,
        session_id: str,
        action_id: str,
        combatant_id: str,
        target_combatant_id: str,
        range_cells: int | None,
        requires_sight: bool = False,
        requires_effect: bool = False,
    ) -> LimiarMapTargetingResponse:
        self.calls.append(
            {
                "session_id": session_id,
                "action_id": action_id,
                "combatant_id": combatant_id,
                "target_combatant_id": target_combatant_id,
                "range_cells": range_cells,
                "requires_sight": requires_sight,
                "requires_effect": requires_effect,
            }
        )
        if self.error is not None:
            raise self.error
        if self.response is None:
            raise AssertionError("StubLimiarMapClient requires a response or error")
        return self.response

    def get_session_state(self, session_id: str):
        return type(
            "StubState",
            (),
            {
                "session_id": session_id,
                "version": 5,
                "tokens": (
                    type(
                        "StubToken",
                        (),
                        {
                            "token_id": "token-source",
                            "combatant_id": "player-123",
                            "position_x": 4,
                            "position_y": 4,
                        },
                    )(),
                    type(
                        "StubToken",
                        (),
                        {
                            "token_id": "token-target",
                            "combatant_id": "enemy-123",
                            "position_x": 10,
                            "position_y": 10,
                        },
                    )(),
                ),
            },
        )()

    def resolve_area_targeting(
        self,
        *,
        session_id: str,
        action_id: str,
        combatant_id: str,
        shape: str,
        origin_cell: dict[str, int],
        anchor_cell: dict[str, int],
        range_cells: int | None,
        size_cells: int,
        requires_sight: bool = False,
        requires_effect: bool = False,
    ) -> LimiarMapAreaTargetingResponse:
        self.area_calls.append(
            {
                "session_id": session_id,
                "action_id": action_id,
                "combatant_id": combatant_id,
                "shape": shape,
                "origin_cell": origin_cell,
                "anchor_cell": anchor_cell,
                "range_cells": range_cells,
                "size_cells": size_cells,
                "requires_sight": requires_sight,
                "requires_effect": requires_effect,
            }
        )
        if self.error is not None:
            raise self.error
        if not isinstance(self.response, LimiarMapAreaTargetingResponse):
            raise AssertionError(
                "StubLimiarMapClient requires an area response for area targeting"
            )
        return self.response


def build_combat_state() -> CombatState:
    return CombatState(
        id="combat-123",
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
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-1",
            },
            {
                "id": "e1",
                "ref_id": "enemy-123",
                "kind": "session_entity",
                "display_name": "Goblin",
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
            },
        ],
        local_distances={
            "player-123": {"enemy-123": 1.5},
            "enemy-123": {"player-123": 1.5},
        },
    )


class CombatTargetingFactoryTests(unittest.TestCase):
    def tearDown(self) -> None:
        combat_targeting.reset_combat_targeting_service()

    def test_map_disabled_uses_local_targeting_service(self) -> None:
        with patch.object(combat_targeting.settings, "limiar_map_enabled", False):
            combat_targeting.reset_combat_targeting_service()
            service = combat_targeting.get_combat_targeting_service()

        self.assertIsInstance(service, LocalCombatTargetingService)

    def test_map_enabled_uses_limiar_map_targeting_service(self) -> None:
        with (
            patch.object(combat_targeting.settings, "limiar_map_enabled", True),
            patch.object(
                combat_targeting.settings,
                "limiar_map_base_url",
                "http://localhost:3000",
            ),
            patch.object(combat_targeting.settings, "limiar_map_timeout_seconds", 2.0),
        ):
            combat_targeting.reset_combat_targeting_service()
            service = combat_targeting.get_combat_targeting_service()

        self.assertIsInstance(service, LimiarMapTargetingService)


class CombatTargetingIntegrationServiceTests(unittest.TestCase):
    def test_map_enabled_and_valid_targeting_returns_map_metadata(self) -> None:
        state = build_combat_state()
        client = StubLimiarMapClient(
            response=LimiarMapTargetingResponse(
                is_valid=True,
                reason=None,
                session_id="session-123",
                action_id="action-1",
                version=7,
                source_token_id="token-source",
                target_token_id="token-target",
                distance_cells=4,
            )
        )
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )

        result = service.validate(
            WeaponAttackIntent(
                session_id="session-123",
                action_id="action-1",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                range_meters=6,
                weapon_range_type="ranged",
            ),
            state,
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.validated_primary_target_ref_id, "enemy-123")
        self.assertEqual(result.spatial_metadata.source_token_id, "token-source")
        self.assertEqual(result.spatial_metadata.target_token_id, "token-target")
        self.assertEqual(result.spatial_metadata.map_version, 7)
        self.assertEqual(result.spatial_metadata.targeting_authority, "limiar_map")
        self.assertEqual(result.spatial_metadata.distance_meters, 6.0)
        self.assertTrue(result.spatial_metadata.is_in_normal_range)
        self.assertFalse(result.spatial_metadata.is_in_long_range)
        # 6 m / 1.5 m/cell = 4 cells (round)
        self.assertEqual(client.calls[0]["range_cells"], 4)
        self.assertTrue(client.calls[0]["requires_sight"])
        self.assertTrue(client.calls[0]["requires_effect"])

    def test_map_enabled_and_invalid_targeting_returns_rejection(self) -> None:
        state = build_combat_state()
        client = StubLimiarMapClient(
            response=LimiarMapTargetingResponse(
                is_valid=False,
                reason="out_of_range",
                session_id="session-123",
                action_id="action-1",
                version=7,
                source_token_id="token-source",
                target_token_id="token-target",
            )
        )
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )

        result = service.validate(
            WeaponAttackIntent(
                session_id="session-123",
                action_id="action-1",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                range_meters=1,
                weapon_range_type="melee",
            ),
            state,
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.failure_reason, "Target is out of range.")

    def test_map_enabled_but_unavailable_falls_back_to_local_targeting(self) -> None:
        state = build_combat_state()
        client = StubLimiarMapClient(
            error=LimiarMapClientError("timeout", kind="timeout")
        )
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )

        result = service.validate(
            WeaponAttackIntent(
                session_id="session-123",
                action_id="action-1",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                weapon_range_type="melee",
            ),
            state,
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.validated_primary_target_ref_id, "enemy-123")
        self.assertEqual(result.spatial_metadata.targeting_authority, "local")

    def test_area_targeting_returns_affected_targets_and_cells(self) -> None:
        state = build_combat_state()
        client = StubLimiarMapClient(
            response=LimiarMapAreaTargetingResponse(
                is_valid=True,
                reason=None,
                session_id="session-123",
                action_id="action-area",
                version=11,
                shape="sphere",
                source_token_id="token-source",
                affected_cells=(
                    LimiarMapAreaCell(x=10, y=10),
                    LimiarMapAreaCell(x=10, y=9),
                ),
                affected_token_ids=("token-target",),
                affected_combatant_ids=("enemy-123",),
            )
        )
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )

        result = service.validate(
            AreaTargetingIntent(
                session_id="session-123",
                action_id="action-area",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                spell_canonical_key="fireball",
                spell_mode="saving_throw",
                shape="sphere",
                size_meters=6,  # 20 ft radius ≈ 6 m
                range_meters=45,  # 150 ft range ≈ 45 m
            ),
            state,
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.affected_target_ref_ids, ["enemy-123"])
        self.assertEqual(result.spatial_metadata.area_shape, "sphere")
        self.assertEqual(result.spatial_metadata.affected_token_ids, ["token-target"])
        self.assertEqual(
            result.spatial_metadata.affected_cells,
            [{"x": 10, "y": 10}, {"x": 10, "y": 9}],
        )
        self.assertEqual(client.area_calls[0]["origin_cell"], {"x": 4, "y": 4})
        self.assertEqual(client.area_calls[0]["anchor_cell"], {"x": 10, "y": 10})
        # Verify conversions: 45 m → 30 cells, 6 m → 4 cells
        self.assertEqual(client.area_calls[0]["range_cells"], 30)
        self.assertEqual(client.area_calls[0]["size_cells"], 4)
        self.assertFalse(client.area_calls[0]["requires_sight"])
        self.assertTrue(client.area_calls[0]["requires_effect"])

    def test_area_targeting_requires_map_when_unavailable(self) -> None:
        state = build_combat_state()
        client = StubLimiarMapClient(
            error=LimiarMapClientError("timeout", kind="timeout")
        )
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )

        result = service.validate(
            AreaTargetingIntent(
                session_id="session-123",
                action_id="action-area",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                spell_canonical_key="fireball",
                spell_mode="saving_throw",
                shape="sphere",
                size_meters=6,
                range_meters=45,
            ),
            state,
        )

        self.assertFalse(result.is_valid)
        self.assertIn("temporarily unavailable", result.failure_reason)

    def test_weapon_attack_range_is_derived_from_weapon_data_when_present(self) -> None:
        state = build_combat_state()
        client = StubLimiarMapClient(
            response=LimiarMapTargetingResponse(
                is_valid=True,
                reason=None,
                session_id="session-123",
                action_id="action-1",
                version=3,
                source_token_id="token-source",
                target_token_id="token-target",
            )
        )
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )

        service.validate(
            WeaponAttackIntent(
                session_id="session-123",
                action_id="action-1",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                range_meters=9,
                weapon_range_type="ranged",
            ),
            state,
        )

        # 9 m / 1.5 m/cell = 6 cells
        self.assertEqual(client.calls[0]["range_cells"], 6)

    def test_weapon_attack_long_range_uses_long_range_cells(self) -> None:
        state = build_combat_state()
        client = StubLimiarMapClient(
            response=LimiarMapTargetingResponse(
                is_valid=True,
                reason=None,
                session_id="session-123",
                action_id="action-long",
                version=3,
                source_token_id="token-source",
                target_token_id="token-target",
                distance_cells=10,
            )
        )
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )

        result = service.validate(
            WeaponAttackIntent(
                session_id="session-123",
                action_id="action-long",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                range_meters=9,
                range_long_meters=18,
                weapon_range_type="ranged",
            ),
            state,
        )

        self.assertEqual(client.calls[0]["range_cells"], 12)
        self.assertTrue(result.spatial_metadata.is_in_long_range)
        self.assertFalse(result.spatial_metadata.is_in_normal_range)

    def test_spell_range_is_derived_from_range_meters(self) -> None:
        state = build_combat_state()
        client = StubLimiarMapClient(
            response=LimiarMapTargetingResponse(
                is_valid=True,
                reason=None,
                session_id="session-123",
                action_id="action-2",
                version=4,
                source_token_id="token-source",
                target_token_id="token-target",
            )
        )
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )

        service.validate(
            SpellCastIntent(
                session_id="session-123",
                action_id="action-2",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                spell_canonical_key="magic_missile",
                spell_mode="spell_attack",
                range_meters=18,
            ),
            state,
        )

        # 18 m / 1.5 m/cell = 12 cells
        self.assertEqual(client.calls[0]["range_cells"], 12)
        self.assertTrue(client.calls[0]["requires_sight"])
        self.assertTrue(client.calls[0]["requires_effect"])

    def test_spell_targeting_prefers_explicit_requirements_over_legacy_fallback(
        self,
    ) -> None:
        state = build_combat_state()
        client = StubLimiarMapClient(
            response=LimiarMapTargetingResponse(
                is_valid=True,
                reason=None,
                session_id="session-123",
                action_id="action-explicit",
                version=4,
                source_token_id="token-source",
                target_token_id="token-target",
            )
        )
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )

        service.validate(
            SpellCastIntent(
                session_id="session-123",
                action_id="action-explicit",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                spell_canonical_key="magic_missile",
                spell_mode="spell_attack",
                target_mode="ranged",
                requires_sight=False,
                requires_effect=True,
            ),
            state,
        )

        self.assertFalse(client.calls[0]["requires_sight"])
        self.assertTrue(client.calls[0]["requires_effect"])

    def test_area_targeting_prefers_explicit_point_requirements_over_legacy_fallback(
        self,
    ) -> None:
        state = build_combat_state()
        client = StubLimiarMapClient(
            response=LimiarMapAreaTargetingResponse(
                is_valid=True,
                reason=None,
                session_id="session-123",
                action_id="action-area-explicit",
                version=11,
                shape="sphere",
                source_token_id="token-source",
                affected_cells=(LimiarMapAreaCell(x=10, y=10),),
                affected_token_ids=("token-target",),
                affected_combatant_ids=("enemy-123",),
            )
        )
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )

        service.validate(
            AreaTargetingIntent(
                session_id="session-123",
                action_id="action-area-explicit",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                spell_canonical_key="fireball",
                spell_mode="saving_throw",
                shape="sphere",
                size_meters=6,
                range_meters=45,
                target_mode="sphere",
                requires_sight=True,
                requires_effect=False,
            ),
            state,
        )

        self.assertTrue(client.area_calls[0]["requires_sight"])
        self.assertFalse(client.area_calls[0]["requires_effect"])

    def test_area_targeting_uses_legacy_fallback_when_point_requirements_are_missing(
        self,
    ) -> None:
        state = build_combat_state()
        client = StubLimiarMapClient(
            response=LimiarMapAreaTargetingResponse(
                is_valid=True,
                reason=None,
                session_id="session-123",
                action_id="action-area-fallback",
                version=11,
                shape="sphere",
                source_token_id="token-source",
                affected_cells=(LimiarMapAreaCell(x=10, y=10),),
                affected_token_ids=("token-target",),
                affected_combatant_ids=("enemy-123",),
            )
        )
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )

        service.validate(
            AreaTargetingIntent(
                session_id="session-123",
                action_id="action-area-fallback",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                spell_canonical_key="fireball",
                spell_mode="saving_throw",
                shape="sphere",
                size_meters=6,
                range_meters=45,
                target_mode="sphere",
            ),
            state,
        )

        self.assertFalse(client.area_calls[0]["requires_sight"])
        self.assertTrue(client.area_calls[0]["requires_effect"])

    def test_wild_shape_attack_sends_default_melee_reach(self) -> None:
        # Phase F4: wild shape attacks are always melee and always send
        # range_cells = 1 (default reach, no reach property on natural attacks).
        state = build_combat_state()
        client = StubLimiarMapClient(
            response=LimiarMapTargetingResponse(
                is_valid=True,
                reason=None,
                session_id="session-123",
                action_id="action-3",
                version=5,
                source_token_id="token-source",
                target_token_id="token-target",
            )
        )
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )

        service.validate(
            WeaponAttackIntent(
                session_id="session-123",
                action_id="action-3",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                is_wild_shape=True,
                weapon_range_type="melee",
                has_reach=False,
            ),
            state,
        )

        self.assertEqual(client.calls[0]["range_cells"], 1)
        self.assertTrue(client.calls[0]["requires_sight"])
        self.assertTrue(client.calls[0]["requires_effect"])

    def test_map_rejections_for_line_of_sight_and_effect_get_human_messages(
        self,
    ) -> None:
        state = build_combat_state()
        service = LimiarMapTargetingService(
            StubLimiarMapClient(
                response=LimiarMapTargetingResponse(
                    is_valid=False,
                    reason="no_line_of_sight",
                    session_id="session-123",
                    action_id="action-los",
                    version=3,
                    source_token_id="token-source",
                    target_token_id="token-target",
                )
            ),
            fallback_service=LocalCombatTargetingService(),
        )

        los_result = service.validate(
            WeaponAttackIntent(
                session_id="session-123",
                action_id="action-los",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                weapon_range_type="ranged",
            ),
            state,
        )
        self.assertFalse(los_result.is_valid)
        self.assertEqual(
            los_result.failure_reason, "Target is blocked by line of sight."
        )

        service = LimiarMapTargetingService(
            StubLimiarMapClient(
                response=LimiarMapTargetingResponse(
                    is_valid=False,
                    reason="no_line_of_effect",
                    session_id="session-123",
                    action_id="action-loe",
                    version=3,
                    source_token_id="token-source",
                    target_token_id="token-target",
                )
            ),
            fallback_service=LocalCombatTargetingService(),
        )
        loe_result = service.validate(
            SpellCastIntent(
                session_id="session-123",
                action_id="action-loe",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                spell_canonical_key="magic_missile",
                spell_mode="spell_attack",
                range_meters=18,
            ),
            state,
        )
        self.assertFalse(loe_result.is_valid)
        self.assertEqual(
            loe_result.failure_reason, "Target is blocked by line of effect."
        )


class CombatTargetingActionFlowTests(TestCombatServiceBase):
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_attack_is_rejected_when_map_targeting_is_invalid(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
    ) -> None:
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        attacker_state = MagicMock()
        attacker_state.state_json = {}
        targeting_service = LimiarMapTargetingService(
            StubLimiarMapClient(
                response=LimiarMapTargetingResponse(
                    is_valid=False,
                    reason="out_of_range",
                    session_id="session-123",
                    action_id="action-1",
                    version=3,
                    source_token_id="token-source",
                    target_token_id="token-target",
                )
            ),
            fallback_service=LocalCombatTargetingService(),
        )

        with (
            patch(
                "app.services.combat.CombatService.get_state", return_value=self.state
            ),
            patch(
                "app.services.combat.CombatService._get_stats",
                return_value=(attacker_state, 10, 16, 14, 2, 0),
            ),
            patch(
                "app.services.combat.CombatService._build_player_attack_context",
                return_value={
                    "name": "Longsword",
                    "damage_dice": "1d8",
                    "attack_bonus": 5,
                    "damage_bonus": 3,
                    "damage_type": "slashing",
                    "range_meters": 1,
                    "weapon_range_type": "melee",
                    "has_reach": False,
                    "weapon_canonical_key": "longsword",
                },
            ),
            patch(
                "app.services.combat_service.actions.weapon_attacks.get_combat_targeting_service",
                return_value=targeting_service,
            ),
        ):
            with self.assertRaises(CombatServiceError) as context:
                await CombatService.attack(
                    self.db,
                    "session-123",
                    CombatAttackRequest(target_ref_id="enemy-123"),
                    "user-1",
                    False,
                )

        self.assertIn("out of range", str(context.exception).lower())


class LocalTargetingVisibilityTests(unittest.TestCase):
    """Phase F3 — visibility-aware targeting via LocalCombatTargetingService."""

    def _make_state(self, attacker_conditions=None, target_conditions=None):
        attacker_effects = [
            {"kind": "condition", "condition_type": c}
            for c in (attacker_conditions or [])
        ]
        target_effects = [
            {"kind": "condition", "condition_type": c}
            for c in (target_conditions or [])
        ]
        return CombatState(
            id="combat-vis",
            session_id="session-vis",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "player-vis",
                    "kind": "player",
                    "display_name": "Hero",
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "user-1",
                    "active_effects": attacker_effects,
                },
                {
                    "id": "e1",
                    "ref_id": "enemy-vis",
                    "kind": "session_entity",
                    "display_name": "Goblin",
                    "status": "active",
                    "team": "enemies",
                    "visible": True,
                    "actor_user_id": None,
                    "active_effects": target_effects,
                },
            ],
        )

    def test_no_conditions_sight_required_passes(self):
        service = LocalCombatTargetingService()
        state = self._make_state()
        result = service.validate(
            WeaponAttackIntent(
                session_id="session-vis",
                action_id="a1",
                actor_ref_id="player-vis",
                actor_kind="player",
                requested_target_ref_id="enemy-vis",
                requires_sight=True,
                requires_effect=True,
            ),
            state,
        )
        self.assertTrue(result.is_valid)

    def test_invisible_target_rejected_when_sight_required(self):
        service = LocalCombatTargetingService()
        state = self._make_state(target_conditions=["invisible"])
        result = service.validate(
            WeaponAttackIntent(
                session_id="session-vis",
                action_id="a1",
                actor_ref_id="player-vis",
                actor_kind="player",
                requested_target_ref_id="enemy-vis",
                requires_sight=True,
                requires_effect=True,
            ),
            state,
        )
        self.assertFalse(result.is_valid)
        self.assertIn("not visible", result.failure_reason.lower())

    def test_invisible_target_allowed_when_sight_not_required(self):
        service = LocalCombatTargetingService()
        state = self._make_state(target_conditions=["invisible"])
        result = service.validate(
            WeaponAttackIntent(
                session_id="session-vis",
                action_id="a1",
                actor_ref_id="player-vis",
                actor_kind="player",
                requested_target_ref_id="enemy-vis",
                requires_sight=False,
                requires_effect=True,
            ),
            state,
        )
        self.assertTrue(result.is_valid)

    def test_blinded_attacker_rejected_when_sight_required(self):
        service = LocalCombatTargetingService()
        state = self._make_state(attacker_conditions=["blinded"])
        result = service.validate(
            WeaponAttackIntent(
                session_id="session-vis",
                action_id="a1",
                actor_ref_id="player-vis",
                actor_kind="player",
                requested_target_ref_id="enemy-vis",
                requires_sight=True,
                requires_effect=True,
            ),
            state,
        )
        self.assertFalse(result.is_valid)

    def test_heavily_obscured_target_rejected_when_sight_required(self):
        service = LocalCombatTargetingService()
        state = self._make_state(target_conditions=["heavily_obscured"])
        result = service.validate(
            WeaponAttackIntent(
                session_id="session-vis",
                action_id="a1",
                actor_ref_id="player-vis",
                actor_kind="player",
                requested_target_ref_id="enemy-vis",
                requires_sight=True,
                requires_effect=True,
            ),
            state,
        )
        self.assertFalse(result.is_valid)

    def test_lightly_obscured_target_allowed_when_sight_required(self):
        service = LocalCombatTargetingService()
        state = self._make_state(target_conditions=["lightly_obscured"])
        result = service.validate(
            WeaponAttackIntent(
                session_id="session-vis",
                action_id="a1",
                actor_ref_id="player-vis",
                actor_kind="player",
                requested_target_ref_id="enemy-vis",
                requires_sight=True,
                requires_effect=True,
            ),
            state,
        )
        self.assertTrue(result.is_valid)

    def test_visibility_failure_reason_is_machine_readable(self):
        service = LocalCombatTargetingService()
        state = self._make_state(target_conditions=["invisible"])
        result = service.validate(
            WeaponAttackIntent(
                session_id="session-vis",
                action_id="a1",
                actor_ref_id="player-vis",
                actor_kind="player",
                requested_target_ref_id="enemy-vis",
                requires_sight=True,
                requires_effect=True,
            ),
            state,
        )
        self.assertFalse(result.is_valid)
        self.assertIsNotNone(result.failure_reason)
        self.assertIsInstance(result.failure_reason, str)

    def test_spell_intent_sight_required_rejects_invisible(self):
        service = LocalCombatTargetingService()
        state = self._make_state(target_conditions=["invisible"])
        result = service.validate(
            SpellCastIntent(
                session_id="session-vis",
                action_id="a1",
                actor_ref_id="player-vis",
                actor_kind="player",
                requested_target_ref_id="enemy-vis",
                spell_canonical_key="fire_bolt",
                spell_mode="spell_attack",
                requires_sight=True,
                requires_effect=True,
            ),
            state,
        )
        self.assertFalse(result.is_valid)

    def test_player_and_npc_use_same_visibility_rules(self):
        service = LocalCombatTargetingService()
        state_as_player = self._make_state(target_conditions=["invisible"])
        state_as_npc = self._make_state(target_conditions=["invisible"])
        state_as_npc.participants[0]["kind"] = "session_entity"
        result_player = service.validate(
            WeaponAttackIntent(
                session_id="session-vis",
                action_id="a1",
                actor_ref_id="player-vis",
                actor_kind="player",
                requested_target_ref_id="enemy-vis",
                requires_sight=True,
                requires_effect=True,
            ),
            state_as_player,
        )
        result_npc = service.validate(
            WeaponAttackIntent(
                session_id="session-vis",
                action_id="a1",
                actor_ref_id="player-vis",
                actor_kind="session_entity",
                requested_target_ref_id="enemy-vis",
                requires_sight=True,
                requires_effect=True,
            ),
            state_as_npc,
        )
        self.assertEqual(result_player.is_valid, result_npc.is_valid)
        self.assertFalse(result_player.is_valid)
        self.assertFalse(result_npc.is_valid)


# ─── Phase F4 — melee reach range_cells ──────────────────────────────────────


class MeleeReachRangeCellsTests(unittest.TestCase):
    """Verify that LimiarMapTargetingService passes the correct range_cells to
    the map based on melee reach resolution.

    The map enforces the actual distance check; Control's job is to pass the
    right reach in cells so the map can do it correctly.
    """

    def _success_response(self) -> LimiarMapTargetingResponse:
        return LimiarMapTargetingResponse(
            is_valid=True,
            reason=None,
            session_id="session-123",
            action_id="a1",
            version=1,
            source_token_id="token-src",
            target_token_id="token-tgt",
        )

    def _service(
        self, response: LimiarMapTargetingResponse
    ) -> LimiarMapTargetingService:
        return LimiarMapTargetingService(
            StubLimiarMapClient(response=response),
            fallback_service=LocalCombatTargetingService(),
        )

    # ── default reach ─────────────────────────────────────────────────────────
    def test_melee_no_reach_property_sends_range_cells_1(self):
        """Default melee reach (has_reach=False) → map receives range_cells=1."""
        client = StubLimiarMapClient(response=self._success_response())
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )
        service.validate(
            WeaponAttackIntent(
                session_id="session-123",
                action_id="a1",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                weapon_range_type="melee",
                has_reach=False,
            ),
            build_combat_state(),
        )
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["range_cells"], 1)

    # ── extended reach ────────────────────────────────────────────────────────
    def test_melee_reach_property_sends_range_cells_2(self):
        """Melee weapon with reach property (has_reach=True) → map receives range_cells=2."""
        client = StubLimiarMapClient(response=self._success_response())
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )
        service.validate(
            WeaponAttackIntent(
                session_id="session-123",
                action_id="a1",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                weapon_range_type="melee",
                has_reach=True,
            ),
            build_combat_state(),
        )
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["range_cells"], 2)

    # ── reach does not affect ranged weapons ──────────────────────────────────
    def test_ranged_weapon_range_from_meters_not_reach(self):
        """Ranged weapon ignores has_reach — range comes from range_meters."""
        client = StubLimiarMapClient(response=self._success_response())
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )
        service.validate(
            WeaponAttackIntent(
                session_id="session-123",
                action_id="a1",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                weapon_range_type="ranged",
                has_reach=True,  # has_reach must be ignored for ranged
                range_meters=36,  # 36m → 9 cells (4m/cell)
            ),
            build_combat_state(),
        )
        self.assertEqual(len(client.calls), 1)
        # range_cells comes from meters, NOT from reach
        self.assertNotEqual(client.calls[0]["range_cells"], 2)

    # ── melee weapon with no range_type defaults to None ─────────────────────
    def test_melee_no_range_type_sends_none(self):
        """When weapon_range_type is unset, no range_cells constraint is sent."""
        client = StubLimiarMapClient(response=self._success_response())
        service = LimiarMapTargetingService(
            client, fallback_service=LocalCombatTargetingService()
        )
        service.validate(
            WeaponAttackIntent(
                session_id="session-123",
                action_id="a1",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                weapon_range_type=None,
                has_reach=False,
            ),
            build_combat_state(),
        )
        self.assertEqual(len(client.calls), 1)
        self.assertIsNone(client.calls[0]["range_cells"])

    # ── player/NPC parity ─────────────────────────────────────────────────────
    def test_player_and_npc_reach_send_same_range_cells(self):
        """Player and NPC melee attacks with same has_reach pass the same range_cells."""
        player_client = StubLimiarMapClient(response=self._success_response())
        npc_client = StubLimiarMapClient(response=self._success_response())
        state = build_combat_state()

        LimiarMapTargetingService(
            player_client, fallback_service=LocalCombatTargetingService()
        ).validate(
            WeaponAttackIntent(
                session_id="session-123",
                action_id="a1",
                actor_ref_id="player-123",
                actor_kind="player",
                requested_target_ref_id="enemy-123",
                weapon_range_type="melee",
                has_reach=True,
            ),
            state,
        )
        LimiarMapTargetingService(
            npc_client, fallback_service=LocalCombatTargetingService()
        ).validate(
            WeaponAttackIntent(
                session_id="session-123",
                action_id="a1",
                actor_ref_id="enemy-123",
                actor_kind="session_entity",
                requested_target_ref_id="player-123",
                weapon_range_type="melee",
                has_reach=True,
            ),
            state,
        )
        self.assertEqual(
            player_client.calls[0]["range_cells"],
            npc_client.calls[0]["range_cells"],
        )
        self.assertEqual(player_client.calls[0]["range_cells"], 2)


if __name__ == "__main__":
    unittest.main()
