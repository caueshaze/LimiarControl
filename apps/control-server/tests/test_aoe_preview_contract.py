"""AoE preview UX contract tests.

These tests guarantee the following product behaviors for AoE spell preview:

1. Preview is read-only — it never mutates combat state (participants,
   pending spells, spell slots).
2. Preview is authoritative — the backend re-validates independently on cast;
   a failed validation raises 400 even if the client-side preview was valid.
3. Preview does not apply damage or effects.
4. Cast requires a valid targeting result — the frontend gates the Cast button
   on ``preview.is_valid``, and the backend enforces it via its own validation.
5. Preview and cast agree — for the same spell + anchor, both resolve the same
   affected cells and targets (they call the same LimiarMap spatial engine).
6. All shapes (sphere, cone, cube, cylinder, line) are covered.
"""
from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.integrations.limiar_map_client_types import (
    LimiarMapAreaCell,
    LimiarMapAreaTargetingResponse,
    LimiarMapStateResponse,
    LimiarMapTokenState,
)
from app.models.combat import CombatPhase
from app.models.session_state import SessionState
from app.schemas.combat import (
    CombatAreaPreviewRequest,
    CombatCastSpellRequest,
    CombatGridCell,
)
from app.services.combat import CombatService, CombatServiceError
from app.services.combat_service.targeting_result import (
    SpatialMetadata,
    TargetingResult,
)


def _make_attacker_state(spell_key: str = "fireball", spell_name: str = "Fireball", spell_level: int = 3) -> SessionState:
    return SessionState(
        id="state-player",
        session_id="session-123",
        player_user_id="player-123",
        state_json={
            "abilities": {"charisma": 18},
            "spellcasting": {
                "spells": [
                    {
                        "name": spell_name,
                        "canonicalKey": spell_key,
                        "level": spell_level,
                        "prepared": True,
                    }
                ],
                "slots": {str(spell_level): {"used": 0, "max": 2}},
            },
        },
    )


def _make_spell_catalog(**overrides) -> MagicMock:
    defaults = dict(
        canonical_key="fireball",
        name_en="Fireball",
        name_pt="Bola de Fogo",
        level=3,
        resolution_type="saving_throw",
        saving_throw="dexterity",
        save_success_outcome="half_damage",
        damage_type="fire",
        damage_dice="8d6",
        heal_dice=None,
        upcast_json=None,
        casting_time_type="action",
        target_type="ranged",
        area_shape="sphere",
        range_meters=45,
        radius_meters=6.0,
        length_meters=None,
        side_meters=None,
        requires_target_sight=False,
        requires_target_effect=False,
        requires_point_sight=False,
        requires_point_effect=False,
        cover_applies_to_save=None,
        material_component_consumed=False,
        consumable_material_options_json=None,
        concentration=False,
        duration=None,
        effects_json=None,
        max_targets=None,
        variants_json=None,
        persistent_area_json=None,
        requires_target_hearing=None,
        on_end_effects_json=None,
        attack_advantage_condition_json=None,
        material_component_text=None,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_map_preview_response(
    *,
    is_valid: bool = True,
    cells: list[tuple[int, int]] | None = None,
    combatant_ids: list[str] | None = None,
    token_ids: list[str] | None = None,
    shape: str = "sphere",
) -> LimiarMapAreaTargetingResponse:
    return LimiarMapAreaTargetingResponse(
        is_valid=is_valid,
        reason=None if is_valid else "Anchor out of range",
        session_id="session-123",
        action_id="preview:test",
        version=12,
        shape=shape,
        source_token_id="tok_player",
        affected_cells=tuple(
            LimiarMapAreaCell(x=x, y=y) for x, y in (cells or [])
        ),
        affected_token_ids=tuple(token_ids or []),
        affected_combatant_ids=tuple(combatant_ids or []),
    )


def _make_map_session_state() -> LimiarMapStateResponse:
    return LimiarMapStateResponse(
        session_id="session-123",
        version=12,
        grid_width=20,
        grid_height=20,
        tokens=(
            LimiarMapTokenState(
                token_id="tok_player",
                label="Hero",
                position_x=8,
                position_y=8,
                combatant_id="player-123",
                controller_type="player",
                controller_id="player-123",
                movement_speed_cells=6,
                movement_budget=6,
            ),
            LimiarMapTokenState(
                token_id="tok_enemy",
                label="Goblin",
                position_x=10,
                position_y=10,
                combatant_id="enemy-123",
                controller_type="session_entity",
                controller_id="enemy-123",
                movement_speed_cells=6,
                movement_budget=6,
            ),
        ),
    )


def _make_targeting_result(
    *,
    is_valid: bool = True,
    cells: list[tuple[int, int]] | None = None,
    target_ref_ids: list[str] | None = None,
    shape: str = "sphere",
) -> TargetingResult:
    return TargetingResult(
        is_valid=is_valid,
        validated_primary_target_ref_id=target_ref_ids[0] if target_ref_ids and is_valid else "",
        affected_target_ref_ids=target_ref_ids if is_valid else [],
        target_kind="session_entity",
        failure_reason=None if is_valid else "Anchor out of range",
        spatial_metadata=SpatialMetadata(
            source_token_id="tok_player",
            affected_token_ids=["tok_player", "tok_enemy"] if is_valid else [],
            affected_cells=[{"x": x, "y": y} for x, y in (cells or [])] if is_valid else [],
            area_shape=shape,
            map_version=12,
            targeting_authority="limiar_map",
        ),
    )


class AoEPreviewReadOnlyTests(TestCombatServiceBase):
    """Preview must never mutate combat state."""

    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.use_map = True

    def test_sphere_preview_does_not_mutate_participants(self):
        attacker_state = _make_attacker_state()
        catalog = _make_spell_catalog()
        participants_before = [dict(p) for p in self.state.participants]
        map_client = MagicMock()
        map_client.get_session_state.return_value = _make_map_session_state()
        map_client.preview_area_targeting.return_value = _make_map_preview_response(
            cells=[(10, 10), (10, 9)],
            combatant_ids=["player-123", "enemy-123"],
            token_ids=["tok_player", "tok_enemy"],
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=catalog), \
             patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)), \
             patch("app.services.combat.CombatService._build_limiar_map_client", return_value=map_client):
            CombatService.preview_area_spell_targeting(
                self.db,
                "session-123",
                CombatAreaPreviewRequest(
                    actor_participant_id="p1",
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=10),
                    spell_canonical_key="fireball",
                ),
                "user-1",
                False,
            )

        self.assertEqual(
            [dict(p) for p in self.state.participants],
            participants_before,
        )
        self.assertIsNone(self.state.participants[0].get("pending_attack"))
        slots = attacker_state.state_json["spellcasting"]["slots"]["3"]
        self.assertEqual(slots["used"], 0)

    def test_preview_surfaces_guardrail_exclusions_for_spatial_targets(self):
        attacker_state = _make_attacker_state()
        catalog = _make_spell_catalog()
        self.state.participants.append(
            {
                "id": "p2",
                "ref_id": "charmer-123",
                "kind": "player",
                "display_name": "Charmed Noble",
                "initiative": 9,
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-2",
            }
        )
        self.state.participants[0]["active_effects"] = [
            {
                "kind": "condition",
                "condition_type": "charmed",
                "metadata": {"charmer_participant_id": "p2"},
            }
        ]

        map_client = MagicMock()
        map_client.get_session_state.return_value = _make_map_session_state()
        map_client.preview_area_targeting.return_value = _make_map_preview_response(
            cells=[(10, 10), (10, 9)],
            combatant_ids=["charmer-123", "enemy-123"],
            token_ids=["tok_charmer", "tok_enemy"],
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=catalog), \
             patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)), \
             patch("app.services.combat.CombatService._build_limiar_map_client", return_value=map_client):
            result = CombatService.preview_area_spell_targeting(
                self.db,
                "session-123",
                CombatAreaPreviewRequest(
                    actor_participant_id="p1",
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=10),
                    spell_canonical_key="fireball",
                ),
                "user-1",
                False,
            )

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["affected_target_ref_ids"], ["charmer-123", "enemy-123"])
        self.assertEqual(len(result["guardrail_target_outcomes"]), 1)
        self.assertEqual(
            result["guardrail_target_outcomes"][0]["target_ref_id"],
            "charmer-123",
        )
        self.assertIn(
            "hostile spell",
            result["guardrail_target_outcomes"][0]["guardrail_reason"],
        )

    def test_cone_preview_does_not_create_pending_spell(self):
        attacker_state = _make_attacker_state("burning_hands", "Burning Hands", 1)
        catalog = _make_spell_catalog(
            canonical_key="burning_hands",
            name_en="Burning Hands",
            level=1,
            area_shape="cone",
            range_meters=0,
            radius_meters=None,
            length_meters=4.5,
            damage_dice="3d6",
        )
        map_client = MagicMock()
        map_client.get_session_state.return_value = _make_map_session_state()
        map_client.preview_area_targeting.return_value = _make_map_preview_response(
            cells=[(9, 8), (10, 8)],
            combatant_ids=["enemy-123"],
            token_ids=["tok_enemy"],
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=catalog), \
             patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)), \
             patch("app.services.combat.CombatService._build_limiar_map_client", return_value=map_client):
            CombatService.preview_area_spell_targeting(
                self.db,
                "session-123",
                CombatAreaPreviewRequest(
                    actor_participant_id="p1",
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=8),
                    spell_canonical_key="burning_hands",
                ),
                "user-1",
                False,
            )

        self.assertIsNone(self.state.participants[0].get("pending_attack"))

    def test_cube_preview_does_not_consume_spell_slot(self):
        attacker_state = _make_attacker_state()
        attacker_state.state_json["spellcasting"]["spells"] = [
            {"name": "Thunderwave", "canonicalKey": "thunderwave", "level": 1, "prepared": True}
        ]
        attacker_state.state_json["spellcasting"]["slots"] = {"1": {"used": 0, "max": 2}}
        catalog = _make_spell_catalog(
            canonical_key="thunderwave",
            name_en="Thunderwave",
            level=1,
            area_shape="cube",
            range_meters=0,
            radius_meters=None,
            length_meters=None,
            side_meters=4.5,
            damage_dice="2d8",
        )
        map_client = MagicMock()
        map_client.get_session_state.return_value = _make_map_session_state()
        map_client.preview_area_targeting.return_value = _make_map_preview_response(
            cells=[(8, 8), (9, 8), (8, 9), (9, 9)],
            combatant_ids=["enemy-123"],
            token_ids=["tok_enemy"],
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=catalog), \
             patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)), \
             patch("app.services.combat.CombatService._build_limiar_map_client", return_value=map_client):
            CombatService.preview_area_spell_targeting(
                self.db,
                "session-123",
                CombatAreaPreviewRequest(
                    actor_participant_id="p1",
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=9, y=9),
                    spell_canonical_key="thunderwave",
                ),
                "user-1",
                False,
            )

        slots = attacker_state.state_json["spellcasting"]["slots"]["1"]
        self.assertEqual(slots["used"], 0)


class AoEPreviewValidityGatingTests(TestCombatServiceBase):
    """Invalid targeting must prevent cast."""

    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.use_map = True

    @patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_entity_hp_update", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock)
    async def test_cast_raises_400_when_targeting_validation_fails(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        attacker_state = _make_attacker_state()
        catalog = _make_spell_catalog()
        targeting_result = _make_targeting_result(
            is_valid=False,
            cells=[],
            target_ref_ids=[],
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=catalog), \
             patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)), \
             patch(
                 "app.services.combat_service.spells.cast_area.get_combat_targeting_service",
                 return_value=SimpleNamespace(validate=MagicMock(return_value=targeting_result)),
             ):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.cast_spell(
                    self.db,
                    "session-123",
                    CombatCastSpellRequest(
                        actor_participant_id="p1",
                        origin_cell=CombatGridCell(x=8, y=8),
                        anchor_cell=CombatGridCell(x=10, y=10),
                        spell_canonical_key="fireball",
                    ),
                    "user-1",
                    False,
                )
            self.assertEqual(ctx.exception.status_code, 400)

    @patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_entity_hp_update", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock)
    @patch("app.services.combat_service.spells.cast_area.resolve_saving_throw")
    async def test_cast_succeeds_when_targeting_validation_passes(
        self,
        mock_resolve_saving_throw,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        attacker_state = _make_attacker_state()
        catalog = _make_spell_catalog()
        targeting_result = _make_targeting_result(
            cells=[(10, 10), (10, 9)],
            target_ref_ids=["player-123", "enemy-123"],
        )
        mock_resolve_saving_throw.return_value = MagicMock(total=10, success=False)

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=catalog), \
             patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)), \
             patch(
                 "app.services.combat.CombatService._build_roll_actor_stats_for_save",
                 return_value=MagicMock(),
             ), \
             patch(
                 "app.services.combat_service.spells.cast_area.get_combat_targeting_service",
                 return_value=SimpleNamespace(validate=MagicMock(return_value=targeting_result)),
             ):
            result = await CombatService.cast_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id="p1",
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=10),
                    spell_canonical_key="fireball",
                ),
                "user-1",
                False,
            )

        self.assertTrue(result["effect_roll_required"])
        self.assertEqual(result["area_shape"], "sphere")
        self.assertIn("pending_spell_id", result)


class AoEPreviewCastAgreementTests(TestCombatServiceBase):
    """Preview and cast must resolve the same affected cells and targets."""

    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.use_map = True

    @patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_entity_hp_update", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock)
    @patch("app.services.combat_service.spells.cast_area.resolve_saving_throw")
    async def test_fireball_sphere_preview_matches_cast_affected_targets(
        self,
        mock_resolve_saving_throw,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        await self._assert_preview_cast_agreement(
            catalog=_make_spell_catalog(),
            expected_cells=[(10, 10), (10, 9)],
            expected_target_ids=["player-123", "enemy-123"],
            expected_token_ids=["tok_player", "tok_enemy"],
            shape="sphere",
            anchor=CombatGridCell(x=10, y=10),
            mock_resolve_saving_throw=mock_resolve_saving_throw,
        )

    @patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_entity_hp_update", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock)
    @patch("app.services.combat_service.spells.cast_area.resolve_saving_throw")
    async def test_burning_hands_cone_preview_matches_cast(
        self,
        mock_resolve_saving_throw,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        await self._assert_preview_cast_agreement(
            catalog=_make_spell_catalog(
                canonical_key="burning_hands",
                name_en="Burning Hands",
                level=1,
                area_shape="cone",
                range_meters=0,
                radius_meters=None,
                length_meters=4.5,
                damage_dice="3d6",
            ),
            expected_cells=[(9, 8), (10, 8)],
            expected_target_ids=["enemy-123"],
            expected_token_ids=["tok_enemy"],
            shape="cone",
            anchor=CombatGridCell(x=10, y=8),
            attacker_state=_make_attacker_state("burning_hands", "Burning Hands", 1),
            mock_resolve_saving_throw=mock_resolve_saving_throw,
            excluded_target_ids=["ally-outside-cone-123"],
        )

    @patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_entity_hp_update", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock)
    @patch("app.services.combat_service.spells.cast_area.resolve_saving_throw")
    async def test_thunderwave_cube_preview_matches_cast(
        self,
        mock_resolve_saving_throw,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        attacker_state = _make_attacker_state()
        attacker_state.state_json["spellcasting"]["spells"] = [
            {"name": "Thunderwave", "canonicalKey": "thunderwave", "level": 1, "prepared": True}
        ]
        attacker_state.state_json["spellcasting"]["slots"] = {"1": {"used": 0, "max": 2}}

        await self._assert_preview_cast_agreement(
            catalog=_make_spell_catalog(
                canonical_key="thunderwave",
                name_en="Thunderwave",
                level=1,
                area_shape="cube",
                range_meters=0,
                radius_meters=None,
                length_meters=None,
                side_meters=4.5,
                damage_dice="2d8",
            ),
            expected_cells=[(8, 8), (9, 8), (8, 9), (9, 9)],
            expected_target_ids=["enemy-123"],
            expected_token_ids=["tok_enemy"],
            shape="cube",
            anchor=CombatGridCell(x=9, y=9),
            attacker_state=attacker_state,
            mock_resolve_saving_throw=mock_resolve_saving_throw,
        )

    async def _assert_preview_cast_agreement(
        self,
        catalog,
        expected_cells,
        expected_target_ids,
        expected_token_ids,
        shape,
        anchor,
        mock_resolve_saving_throw,
        attacker_state=None,
        excluded_target_ids=None,
    ):
        if attacker_state is None:
            attacker_state = _make_attacker_state()

        map_response = _make_map_preview_response(
            cells=expected_cells,
            combatant_ids=expected_target_ids,
            token_ids=expected_token_ids,
        )
        targeting_result = _make_targeting_result(
            cells=expected_cells,
            target_ref_ids=expected_target_ids,
            shape=shape,
        )
        map_client = MagicMock()
        map_client.get_session_state.return_value = _make_map_session_state()
        map_client.preview_area_targeting.return_value = map_response

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=catalog), \
             patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)), \
             patch("app.services.combat.CombatService._build_limiar_map_client", return_value=map_client):
            preview_result = CombatService.preview_area_spell_targeting(
                self.db,
                "session-123",
                CombatAreaPreviewRequest(
                    actor_participant_id="p1",
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=anchor,
                    spell_canonical_key=catalog.canonical_key,
                ),
                "user-1",
                False,
            )

        mock_resolve_saving_throw.return_value = MagicMock(total=10, success=False)

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=catalog), \
             patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)), \
             patch(
                 "app.services.combat.CombatService._build_roll_actor_stats_for_save",
                 return_value=MagicMock(),
             ), \
             patch(
                 "app.services.combat_service.spells.cast_area.get_combat_targeting_service",
                 return_value=SimpleNamespace(validate=MagicMock(return_value=targeting_result)),
             ):
            cast_result = await CombatService.cast_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id="p1",
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=anchor,
                    spell_canonical_key=catalog.canonical_key,
                ),
                "user-1",
                False,
            )

        self.assertEqual(
            sorted(preview_result["affected_target_ref_ids"]),
            sorted(cast_result["affected_target_ref_ids"]),
        )
        for excluded_target_id in excluded_target_ids or []:
            self.assertNotIn(
                excluded_target_id,
                preview_result["affected_target_ref_ids"],
            )
            self.assertNotIn(
                excluded_target_id,
                cast_result["affected_target_ref_ids"],
            )
        preview_cells_set = {(c["x"], c["y"]) for c in preview_result["affected_cells"]}
        pending = self.state.participants[0].get("pending_attack", {})
        cast_cells_raw = pending.get("affected_cells") or cast_result.get("affected_cells") or []
        cast_cells_set = set()
        for c in cast_cells_raw:
            if isinstance(c, dict):
                cast_cells_set.add((c["x"], c["y"]))
            else:
                cast_cells_set.add(c)
        self.assertEqual(preview_cells_set, cast_cells_set)


class AoEPreviewShapePathTests(TestCombatServiceBase):
    """Each AoE shape must pass through the full preview pipeline."""

    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.use_map = True

    def _run_preview_for_shape(self, catalog, anchor):
        attacker_state = _make_attacker_state(
            catalog.canonical_key,
            catalog.name_en,
            catalog.level,
        )
        map_client = MagicMock()
        map_client.get_session_state.return_value = _make_map_session_state()
        map_client.preview_area_targeting.return_value = _make_map_preview_response(
            cells=[(10, 10)],
            combatant_ids=["enemy-123"],
            token_ids=["tok_enemy"],
            shape=catalog.area_shape,
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=catalog), \
             patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)), \
             patch("app.services.combat.CombatService._build_limiar_map_client", return_value=map_client):
            return CombatService.preview_area_spell_targeting(
                self.db,
                "session-123",
                CombatAreaPreviewRequest(
                    actor_participant_id="p1",
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=anchor,
                    spell_canonical_key=catalog.canonical_key,
                ),
                "user-1",
                False,
            )

    def test_sphere_preview_returns_shape_and_cells(self):
        result = self._run_preview_for_shape(
            _make_spell_catalog(),
            CombatGridCell(x=10, y=10),
        )
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["shape"], "sphere")
        self.assertGreater(len(result["affected_cells"]), 0)

    def test_cone_preview_returns_shape_and_cells(self):
        result = self._run_preview_for_shape(
            _make_spell_catalog(
                canonical_key="burning_hands",
                name_en="Burning Hands",
                level=1,
                area_shape="cone",
                range_meters=0,
                radius_meters=None,
                length_meters=4.5,
            ),
            CombatGridCell(x=10, y=8),
        )
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["shape"], "cone")

    def test_cube_preview_returns_shape_and_cells(self):
        result = self._run_preview_for_shape(
            _make_spell_catalog(
                canonical_key="thunderwave",
                name_en="Thunderwave",
                level=1,
                area_shape="cube",
                range_meters=0,
                radius_meters=None,
                length_meters=None,
                side_meters=4.5,
            ),
            CombatGridCell(x=9, y=9),
        )
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["shape"], "cube")

    def test_cylinder_preview_returns_shape_and_cells(self):
        result = self._run_preview_for_shape(
            _make_spell_catalog(
                canonical_key="flame_strike",
                name_en="Flame Strike",
                level=5,
                area_shape="cylinder",
                range_meters=18,
                radius_meters=3.0,
            ),
            CombatGridCell(x=10, y=10),
        )
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["shape"], "cylinder")

    def test_line_preview_returns_shape_and_cells(self):
        result = self._run_preview_for_shape(
            _make_spell_catalog(
                canonical_key="lightning_bolt",
                name_en="Lightning Bolt",
                level=3,
                area_shape="line",
                range_meters=0,
                radius_meters=None,
                length_meters=30.0,
            ),
            CombatGridCell(x=10, y=8),
        )
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["shape"], "line")
