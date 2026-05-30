"""Tests for per-target cover metadata in area saving throw spells.

Verifies that _get_area_per_target_cover returns the correct cover per target,
and that _cast_area_spell applies resolve_cover_save_dc per target when
cover_applies_to_save permits.

Acceptance criteria:
- Half cover reduces DC by 2 per target.
- Three-quarters cover reduces DC by 5 per target.
- No cover / None metadata keeps base DC.
- cover_applies_to_save=None/none keeps base DC even with cover.
- Full cover does not reduce DC.
- Each target gets its own effective DC independently.
- Map unavailable or disabled → all targets fall back to None cover.
- Metadata lookup failure for one target → that target falls back to None.
- Footprint/affected targets are unchanged.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.integrations.limiar_map_client_types import (
    LimiarMapBatchTargetingResponse,
    LimiarMapBatchTargetingResult,
    LimiarMapClientError,
    LimiarMapTargetingResponse,
)
from app.models.combat import CombatPhase
from app.models.session_state import SessionState
from app.schemas.combat import CombatCastSpellRequest, CombatGridCell
from app.schemas.roll import RollActorStats
from app.services.combat import CombatService
from app.services.combat_service.targeting_result import SpatialMetadata, TargetingResult


# ---------------------------------------------------------------------------
# Unit tests: _get_area_per_target_cover
# ---------------------------------------------------------------------------

def _batch_unavailable() -> MagicMock:
    """Return a side_effect that makes validate_targets_batch raise LimiarMapClientError.

    Use this on mock clients in tests that exercise the individual-fallback path,
    so the new batch-preferring logic still falls back to validate_single_target.
    """
    return MagicMock(side_effect=LimiarMapClientError("batch not available", kind="network"))


def _batch_response(*results: tuple[str, str | None]) -> LimiarMapBatchTargetingResponse:
    """Build a LimiarMapBatchTargetingResponse for test use."""
    return LimiarMapBatchTargetingResponse(
        session_id="s1",
        action_id="a1",
        version=1,
        results=tuple(
            LimiarMapBatchTargetingResult(target_combatant_id=ref_id, cover=cover)
            for ref_id, cover in results
        ),
    )


class GetAreaPerTargetCoverTests(unittest.TestCase):
    """Unit tests for the _get_area_per_target_cover helper."""

    def _targeting_response(self, cover: str | None) -> LimiarMapTargetingResponse:
        return LimiarMapTargetingResponse(
            is_valid=True,
            reason=None,
            session_id="s1",
            action_id="a1",
            version=1,
            source_token_id="tok_actor",
            target_token_id="tok_target",
            cover=cover,
        )

    def test_empty_target_list_returns_empty_dict(self):
        result = CombatService._get_area_per_target_cover(
            session_id="s1",
            action_id="a1",
            actor_ref_id="actor",
            target_ref_ids=[],
            use_map=True,
        )
        self.assertEqual(result, {})

    def test_use_map_false_returns_all_none(self):
        result = CombatService._get_area_per_target_cover(
            session_id="s1",
            action_id="a1",
            actor_ref_id="actor",
            target_ref_ids=["t1", "t2"],
            use_map=False,
        )
        self.assertEqual(result, {"t1": None, "t2": None})

    @patch("app.services.combat_service.spells.cast_area.settings")
    def test_limiar_map_disabled_returns_all_none(self, mock_settings):
        mock_settings.limiar_map_enabled = False
        result = CombatService._get_area_per_target_cover(
            session_id="s1",
            action_id="a1",
            actor_ref_id="actor",
            target_ref_ids=["t1"],
            use_map=True,
        )
        self.assertEqual(result, {"t1": None})

    @patch("app.services.combat_service.spells.cast_area.settings")
    def test_returns_cover_per_target_from_map(self, mock_settings):
        mock_settings.limiar_map_enabled = True
        mock_client = MagicMock()
        mock_client.validate_targets_batch = _batch_unavailable()
        mock_client.validate_single_target.side_effect = [
            self._targeting_response("none"),
            self._targeting_response("half"),
            self._targeting_response("threeQuarters"),
        ]
        with patch.object(CombatService, "_build_limiar_map_client", return_value=mock_client):
            result = CombatService._get_area_per_target_cover(
                session_id="s1",
                action_id="a1",
                actor_ref_id="actor",
                target_ref_ids=["t1", "t2", "t3"],
                use_map=True,
            )
        self.assertEqual(result, {"t1": "none", "t2": "half", "t3": "threeQuarters"})

    @patch("app.services.combat_service.spells.cast_area.settings")
    def test_map_error_for_one_target_falls_back_to_none(self, mock_settings):
        mock_settings.limiar_map_enabled = True
        mock_client = MagicMock()
        mock_client.validate_targets_batch = _batch_unavailable()
        mock_client.validate_single_target.side_effect = [
            self._targeting_response("half"),
            LimiarMapClientError("timeout", kind="timeout"),
        ]
        with patch.object(CombatService, "_build_limiar_map_client", return_value=mock_client):
            result = CombatService._get_area_per_target_cover(
                session_id="s1",
                action_id="a1",
                actor_ref_id="actor",
                target_ref_ids=["t1", "t2"],
                use_map=True,
            )
        self.assertEqual(result["t1"], "half")
        self.assertIsNone(result["t2"])

    @patch("app.services.combat_service.spells.cast_area.settings")
    def test_response_cover_none_stored_as_none(self, mock_settings):
        mock_settings.limiar_map_enabled = True
        mock_client = MagicMock()
        mock_client.validate_targets_batch = _batch_unavailable()
        mock_client.validate_single_target.return_value = self._targeting_response(None)
        with patch.object(CombatService, "_build_limiar_map_client", return_value=mock_client):
            result = CombatService._get_area_per_target_cover(
                session_id="s1",
                action_id="a1",
                actor_ref_id="actor",
                target_ref_ids=["t1"],
                use_map=True,
            )
        self.assertIsNone(result["t1"])

    @patch("app.services.combat_service.spells.cast_area.settings")
    def test_validate_single_target_called_without_range_or_sight_checks(self, mock_settings):
        mock_settings.limiar_map_enabled = True
        mock_client = MagicMock()
        mock_client.validate_targets_batch = _batch_unavailable()
        mock_client.validate_single_target.return_value = self._targeting_response("half")
        with patch.object(CombatService, "_build_limiar_map_client", return_value=mock_client):
            CombatService._get_area_per_target_cover(
                session_id="s1",
                action_id="a1",
                actor_ref_id="actor",
                target_ref_ids=["t1"],
                use_map=True,
            )
        call_kwargs = mock_client.validate_single_target.call_args.kwargs
        self.assertIsNone(call_kwargs["range_cells"])
        self.assertFalse(call_kwargs["requires_sight"])
        self.assertFalse(call_kwargs["requires_effect"])


class GetAreaPerTargetCoverBatchTests(unittest.TestCase):
    """Unit tests for the batch path in get_area_per_target_cover."""

    @patch("app.services.combat_service.spells.cast_area.settings")
    def test_batch_called_once_for_all_targets(self, mock_settings):
        """When batch is available, validate_targets_batch is called once and
        validate_single_target is never called."""
        mock_settings.limiar_map_enabled = True
        mock_client = MagicMock()
        mock_client.validate_targets_batch.return_value = _batch_response(
            ("t1", "none"), ("t2", "half"), ("t3", "threeQuarters")
        )
        with patch.object(CombatService, "_build_limiar_map_client", return_value=mock_client):
            result = CombatService._get_area_per_target_cover(
                session_id="s1",
                action_id="a1",
                actor_ref_id="actor",
                target_ref_ids=["t1", "t2", "t3"],
                use_map=True,
            )
        mock_client.validate_targets_batch.assert_called_once()
        mock_client.validate_single_target.assert_not_called()
        self.assertEqual(result, {"t1": "none", "t2": "half", "t3": "threeQuarters"})

    @patch("app.services.combat_service.spells.cast_area.settings")
    def test_batch_result_missing_target_filled_with_none(self, mock_settings):
        """If a target ref_id is absent from the batch response, it gets None."""
        mock_settings.limiar_map_enabled = True
        mock_client = MagicMock()
        mock_client.validate_targets_batch.return_value = _batch_response(
            ("t1", "half"),
            # t2 deliberately omitted from results
        )
        with patch.object(CombatService, "_build_limiar_map_client", return_value=mock_client):
            result = CombatService._get_area_per_target_cover(
                session_id="s1",
                action_id="a1",
                actor_ref_id="actor",
                target_ref_ids=["t1", "t2"],
                use_map=True,
            )
        self.assertEqual(result["t1"], "half")
        self.assertIsNone(result["t2"])

    @patch("app.services.combat_service.spells.cast_area.settings")
    def test_batch_failure_falls_back_to_individual(self, mock_settings):
        """A LimiarMapClientError from batch triggers fallback to individual calls."""
        mock_settings.limiar_map_enabled = True
        mock_client = MagicMock()
        mock_client.validate_targets_batch.side_effect = LimiarMapClientError(
            "service unavailable", kind="http", status_code=503
        )
        mock_client.validate_single_target.side_effect = [
            LimiarMapTargetingResponse(
                is_valid=True, reason=None, session_id="s1", action_id="a1",
                version=1, source_token_id=None, target_token_id=None, cover="half",
            ),
            LimiarMapTargetingResponse(
                is_valid=True, reason=None, session_id="s1", action_id="a1",
                version=1, source_token_id=None, target_token_id=None, cover="none",
            ),
        ]
        with patch.object(CombatService, "_build_limiar_map_client", return_value=mock_client):
            result = CombatService._get_area_per_target_cover(
                session_id="s1",
                action_id="a1",
                actor_ref_id="actor",
                target_ref_ids=["t1", "t2"],
                use_map=True,
            )
        mock_client.validate_targets_batch.assert_called_once()
        self.assertEqual(mock_client.validate_single_target.call_count, 2)
        self.assertEqual(result, {"t1": "half", "t2": "none"})

    @patch("app.services.combat_service.spells.cast_area.settings")
    def test_duplicate_target_ref_ids_are_deduped(self, mock_settings):
        """Duplicate target_ref_ids must be deduped before the batch/individual call."""
        mock_settings.limiar_map_enabled = True
        mock_client = MagicMock()
        mock_client.validate_targets_batch.return_value = _batch_response(
            ("t1", "half"),
        )
        with patch.object(CombatService, "_build_limiar_map_client", return_value=mock_client):
            result = CombatService._get_area_per_target_cover(
                session_id="s1",
                action_id="a1",
                actor_ref_id="actor",
                target_ref_ids=["t1", "t1", "t1"],
                use_map=True,
            )
        batch_call = mock_client.validate_targets_batch.call_args.kwargs
        self.assertEqual(batch_call["target_combatant_ids"], ["t1"],
                         "Batch must receive deduplicated list")
        self.assertEqual(result["t1"], "half")

    @patch("app.services.combat_service.spells.cast_area.settings")
    def test_duplicate_deduplication_with_individual_fallback(self, mock_settings):
        """Dedupe also applies when falling back to individual calls."""
        mock_settings.limiar_map_enabled = True
        mock_client = MagicMock()
        mock_client.validate_targets_batch = _batch_unavailable()
        mock_client.validate_single_target.return_value = LimiarMapTargetingResponse(
            is_valid=True, reason=None, session_id="s1", action_id="a1",
            version=1, source_token_id=None, target_token_id=None, cover="half",
        )
        with patch.object(CombatService, "_build_limiar_map_client", return_value=mock_client):
            result = CombatService._get_area_per_target_cover(
                session_id="s1",
                action_id="a1",
                actor_ref_id="actor",
                target_ref_ids=["t1", "t1", "t1"],
                use_map=True,
            )
        self.assertEqual(mock_client.validate_single_target.call_count, 1,
                         "Individual fallback must call validate_single_target only once per unique ref_id")
        self.assertEqual(result["t1"], "half")

    @patch("app.services.combat_service.spells.cast_area.settings")
    def test_batch_cover_null_stored_as_none(self, mock_settings):
        """cover=null from batch (token not found) is stored as None."""
        mock_settings.limiar_map_enabled = True
        mock_client = MagicMock()
        mock_client.validate_targets_batch.return_value = _batch_response(("t1", None))
        with patch.object(CombatService, "_build_limiar_map_client", return_value=mock_client):
            result = CombatService._get_area_per_target_cover(
                session_id="s1",
                action_id="a1",
                actor_ref_id="actor",
                target_ref_ids=["t1"],
                use_map=True,
            )
        self.assertIsNone(result["t1"])


# ---------------------------------------------------------------------------
# Integration tests: per-target DC in _cast_area_spell
# ---------------------------------------------------------------------------

def _make_map_targeting_result(affected_ref_ids: list[str]) -> TargetingResult:
    return TargetingResult(
        is_valid=True,
        validated_primary_target_ref_id=affected_ref_ids[0] if affected_ref_ids else "",
        affected_target_ref_ids=affected_ref_ids,
        target_kind="session_entity",
        spatial_metadata=SpatialMetadata(
            source_token_id="tok_player",
            affected_token_ids=[f"tok_{r}" for r in affected_ref_ids],
            affected_cells=[{"x": 10, "y": 10}],
            area_shape="sphere",
            map_version=1,
            targeting_authority="limiar_map",
        ),
    )


def _make_spell_catalog_entry(cover_applies_to_save: str | None = None):
    return MagicMock(
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
        radius_meters=6,
        cover_applies_to_save=cover_applies_to_save,
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


def _make_attacker_state() -> SessionState:
    return SessionState(
        id="state-player",
        session_id="session-123",
        player_user_id="player-123",
        state_json={
            "abilities": {"intelligence": 18},
            "spellcasting": {
                "spells": [{"name": "Fireball", "canonicalKey": "fireball", "level": 3, "prepared": True}],
                "slots": {"3": {"used": 0, "max": 2}},
            },
        },
    )


def _make_roll_actor_stats(ref_id: str) -> RollActorStats:
    return RollActorStats(
        display_name="Target",
        abilities={"dexterity": 10},
        actor_kind="session_entity",
        actor_ref_id=ref_id,
    )


class AreaSaveCoverApplyTests(TestCombatServiceBase):
    """Integration tests: verify per-target DC reduction in _cast_area_spell."""

    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0

    async def _cast_fireball(self) -> dict:
        return await CombatService.cast_spell(
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

    async def test_no_cover_metadata_uses_base_dc(self):
        mock_save = MagicMock(side_effect=[MagicMock(total=10, success=False)])
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                   return_value=_make_spell_catalog_entry("physical")), \
             patch("app.services.combat.CombatService._get_stats",
                   return_value=(_make_attacker_state(), 12, 10, 10, 3, 4)), \
             patch("app.services.combat.CombatService._build_roll_actor_stats_for_save",
                   side_effect=lambda _db, _sid, ref_id, *a, **kw: _make_roll_actor_stats(ref_id)), \
             patch("app.services.combat_service.spells.cast_area.get_combat_targeting_service",
                   return_value=SimpleNamespace(validate=MagicMock(
                       return_value=_make_map_targeting_result(["enemy-123"])))), \
             patch("app.services.combat.CombatService._get_area_per_target_cover",
                   return_value={"enemy-123": None}), \
             patch("app.services.combat_service.spells.cast_area.resolve_saving_throw", mock_save), \
             patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock):
            await self._cast_fireball()
        dc_used = mock_save.call_args.kwargs["dc"]
        self.assertEqual(dc_used, 15)

    async def test_cover_applies_to_save_null_does_not_reduce_dc(self):
        mock_save = MagicMock(side_effect=[MagicMock(total=10, success=False)])
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                   return_value=_make_spell_catalog_entry(None)), \
             patch("app.services.combat.CombatService._get_stats",
                   return_value=(_make_attacker_state(), 12, 10, 10, 3, 4)), \
             patch("app.services.combat.CombatService._build_roll_actor_stats_for_save",
                   side_effect=lambda _db, _sid, ref_id, *a, **kw: _make_roll_actor_stats(ref_id)), \
             patch("app.services.combat_service.spells.cast_area.get_combat_targeting_service",
                   return_value=SimpleNamespace(validate=MagicMock(
                       return_value=_make_map_targeting_result(["enemy-123"])))), \
             patch("app.services.combat.CombatService._get_area_per_target_cover") as mock_cover_lookup, \
             patch("app.services.combat_service.spells.cast_area.resolve_saving_throw", mock_save), \
             patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock):
            await self._cast_fireball()
        mock_cover_lookup.assert_not_called()
        dc_used = mock_save.call_args.kwargs["dc"]
        self.assertEqual(dc_used, 15)

    async def test_full_cover_does_not_reduce_dc(self):
        mock_save = MagicMock(side_effect=[MagicMock(total=10, success=False)])
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                   return_value=_make_spell_catalog_entry("physical")), \
             patch("app.services.combat.CombatService._get_stats",
                   return_value=(_make_attacker_state(), 12, 10, 10, 3, 4)), \
             patch("app.services.combat.CombatService._build_roll_actor_stats_for_save",
                   side_effect=lambda _db, _sid, ref_id, *a, **kw: _make_roll_actor_stats(ref_id)), \
             patch("app.services.combat_service.spells.cast_area.get_combat_targeting_service",
                   return_value=SimpleNamespace(validate=MagicMock(
                       return_value=_make_map_targeting_result(["enemy-123"])))), \
             patch("app.services.combat.CombatService._get_area_per_target_cover",
                   return_value={"enemy-123": "full"}), \
             patch("app.services.combat_service.spells.cast_area.resolve_saving_throw", mock_save), \
             patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock):
            await self._cast_fireball()
        dc_used = mock_save.call_args.kwargs["dc"]
        # full cover modifier is 0 (blocked upstream, not a DC modifier)
        self.assertEqual(dc_used, 15)

    async def test_multi_target_each_uses_own_dc(self):
        """Three targets: no cover, half, three-quarters → three different effective DCs."""
        self.state.participants.append({
            "id": "e2",
            "ref_id": "enemy-456",
            "kind": "session_entity",
            "display_name": "Orc",
            "initiative": None,
            "status": "active",
            "team": "enemies",
            "visible": True,
            "actor_user_id": None,
        })
        self.state.participants.append({
            "id": "e3",
            "ref_id": "enemy-789",
            "kind": "session_entity",
            "display_name": "Troll",
            "initiative": None,
            "status": "active",
            "team": "enemies",
            "visible": True,
            "actor_user_id": None,
        })
        affected_ids = ["enemy-123", "enemy-456", "enemy-789"]
        mock_save = MagicMock(side_effect=[
            MagicMock(total=10, success=False),
            MagicMock(total=12, success=True),
            MagicMock(total=11, success=True),
        ])
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                   return_value=_make_spell_catalog_entry("physical")), \
             patch("app.services.combat.CombatService._get_stats",
                   return_value=(_make_attacker_state(), 12, 10, 10, 3, 4)), \
             patch("app.services.combat.CombatService._build_roll_actor_stats_for_save",
                   side_effect=lambda _db, _sid, ref_id, *a, **kw: _make_roll_actor_stats(ref_id)), \
             patch("app.services.combat_service.spells.cast_area.get_combat_targeting_service",
                   return_value=SimpleNamespace(validate=MagicMock(
                       return_value=_make_map_targeting_result(affected_ids)))), \
             patch("app.services.combat.CombatService._get_area_per_target_cover",
                   return_value={
                       "enemy-123": None,          # no cover → DC 15
                       "enemy-456": "half",         # half cover → DC 13
                       "enemy-789": "threeQuarters", # 3/4 cover → DC 10
                   }), \
             patch("app.services.combat_service.spells.cast_area.resolve_saving_throw", mock_save), \
             patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock):
            result = await self._cast_fireball()

        dc_values = [call.kwargs["dc"] for call in mock_save.call_args_list]
        self.assertEqual(dc_values, [15, 13, 10])
        self.assertEqual(result["target_count"], 3)
        self.assertEqual(result["affected_target_ref_ids"], affected_ids)

    async def test_outcomes_include_cover_and_effective_dc(self):
        mock_save = MagicMock(side_effect=[MagicMock(total=10, success=False)])
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                   return_value=_make_spell_catalog_entry("physical")), \
             patch("app.services.combat.CombatService._get_stats",
                   return_value=(_make_attacker_state(), 12, 10, 10, 3, 4)), \
             patch("app.services.combat.CombatService._build_roll_actor_stats_for_save",
                   side_effect=lambda _db, _sid, ref_id, *a, **kw: _make_roll_actor_stats(ref_id)), \
             patch("app.services.combat_service.spells.cast_area.get_combat_targeting_service",
                   return_value=SimpleNamespace(validate=MagicMock(
                       return_value=_make_map_targeting_result(["enemy-123"])))), \
             patch("app.services.combat.CombatService._get_area_per_target_cover",
                   return_value={"enemy-123": "half"}), \
             patch("app.services.combat_service.spells.cast_area.resolve_saving_throw", mock_save), \
             patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock):
            result = await self._cast_fireball()
        outcome = result["area_target_outcomes"][0]
        self.assertEqual(outcome["cover"], "half")
        self.assertEqual(outcome["effective_save_dc"], 13)
        self.assertEqual(outcome["base_save_dc"], 15)
        self.assertEqual(outcome["cover_modifier"], 2)

    async def test_affected_targets_unchanged_by_cover_logic(self):
        """Cover metadata does not change which targets are affected."""
        mock_save = MagicMock(side_effect=[MagicMock(total=10, success=False)])
        target_result = _make_map_targeting_result(["enemy-123"])
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                   return_value=_make_spell_catalog_entry("physical")), \
             patch("app.services.combat.CombatService._get_stats",
                   return_value=(_make_attacker_state(), 12, 10, 10, 3, 4)), \
             patch("app.services.combat.CombatService._build_roll_actor_stats_for_save",
                   side_effect=lambda _db, _sid, ref_id, *a, **kw: _make_roll_actor_stats(ref_id)), \
             patch("app.services.combat_service.spells.cast_area.get_combat_targeting_service",
                   return_value=SimpleNamespace(validate=MagicMock(return_value=target_result))), \
             patch("app.services.combat.CombatService._get_area_per_target_cover",
                   return_value={"enemy-123": "threeQuarters"}), \
             patch("app.services.combat_service.spells.cast_area.resolve_saving_throw", mock_save), \
             patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock):
            result = await self._cast_fireball()
        self.assertEqual(result["affected_target_ref_ids"], ["enemy-123"])
        self.assertEqual(result["affected_cells"], [{"x": 10, "y": 10}])

    async def test_cover_lookup_not_called_when_cover_does_not_apply(self):
        """_get_area_per_target_cover must not be called when cover_applies_to_save is absent."""
        mock_save = MagicMock(side_effect=[MagicMock(total=10, success=False)])
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                   return_value=_make_spell_catalog_entry(None)), \
             patch("app.services.combat.CombatService._get_stats",
                   return_value=(_make_attacker_state(), 12, 10, 10, 3, 4)), \
             patch("app.services.combat.CombatService._build_roll_actor_stats_for_save",
                   side_effect=lambda _db, _sid, ref_id, *a, **kw: _make_roll_actor_stats(ref_id)), \
             patch("app.services.combat_service.spells.cast_area.get_combat_targeting_service",
                   return_value=SimpleNamespace(validate=MagicMock(
                       return_value=_make_map_targeting_result(["enemy-123"])))), \
             patch("app.services.combat.CombatService._get_area_per_target_cover") as mock_cover_lookup, \
             patch("app.services.combat_service.spells.cast_area.resolve_saving_throw", mock_save), \
             patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock):
            await self._cast_fireball()
        mock_cover_lookup.assert_not_called()
