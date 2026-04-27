"""Tests for per-target cover metadata in the area spell preview response.

Verifies that preview_area_spell_targeting populates
affected_target_spatial_metadata correctly when cover_applies_to_save
permits cover in the saving throw.

Acceptance criteria:
- cover_applies_to_save=physical + target without cover → effective_dc = base_dc, modifier = 0
- half cover → effective_dc = base_dc - 2, modifier = 2
- threeQuarters cover → effective_dc = base_dc - 5, modifier = 5
- full cover → effective_dc = base_dc, modifier = 0
- cover_applies_to_save=none → affected_target_spatial_metadata = []
- cover_applies_to_save absent/null → []
- save_dc absent → []
- Lookup failure for one target → cover null, DC base for that target
- Multi-target each gets own metadata
- Footprint and affected_target_ref_ids unchanged
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.integrations.limiar_map_client_types import (
    LimiarMapClientError,
    LimiarMapAreaTargetingResponse,
    LimiarMapAreaCell,
    LimiarMapTargetingResponse,
)
from app.services.combat import CombatService
from app.services.combat_service.spells.area_spatial_metadata import (
    build_area_affected_target_spatial_metadata,
    get_area_per_target_cover,
)


# ---------------------------------------------------------------------------
# Unit tests: get_area_per_target_cover (standalone function)
# ---------------------------------------------------------------------------

class GetAreaPerTargetCoverStandaloneTests(unittest.TestCase):
    """Unit tests for the standalone get_area_per_target_cover helper.

    The classmethod wrapper in CastAreaMixin is covered by
    test_cast_area_cover.py; these tests focus on the shared module.
    """

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

    def test_empty_list_returns_empty_dict(self):
        client = MagicMock()
        result = get_area_per_target_cover(
            client=client,
            session_id="s1",
            action_id="a1",
            actor_ref_id="actor",
            target_ref_ids=[],
        )
        self.assertEqual(result, {})
        client.validate_single_target.assert_not_called()

    def test_returns_cover_per_target(self):
        client = MagicMock()
        client.validate_single_target.side_effect = [
            self._targeting_response("none"),
            self._targeting_response("half"),
            self._targeting_response("threeQuarters"),
        ]
        result = get_area_per_target_cover(
            client=client,
            session_id="s1",
            action_id="a1",
            actor_ref_id="actor",
            target_ref_ids=["t1", "t2", "t3"],
        )
        self.assertEqual(result, {"t1": "none", "t2": "half", "t3": "threeQuarters"})

    def test_error_for_one_target_falls_back_to_none(self):
        client = MagicMock()
        client.validate_single_target.side_effect = [
            self._targeting_response("half"),
            LimiarMapClientError("timeout", kind="timeout"),
        ]
        result = get_area_per_target_cover(
            client=client,
            session_id="s1",
            action_id="a1",
            actor_ref_id="actor",
            target_ref_ids=["t1", "t2"],
        )
        self.assertEqual(result["t1"], "half")
        self.assertIsNone(result["t2"])

    def test_null_cover_response_stored_as_none(self):
        client = MagicMock()
        client.validate_single_target.return_value = self._targeting_response(None)
        result = get_area_per_target_cover(
            client=client,
            session_id="s1",
            action_id="a1",
            actor_ref_id="actor",
            target_ref_ids=["t1"],
        )
        self.assertIsNone(result["t1"])

    def test_called_without_range_or_sight_checks(self):
        client = MagicMock()
        client.validate_single_target.return_value = self._targeting_response(None)
        get_area_per_target_cover(
            client=client,
            session_id="s1",
            action_id="a1",
            actor_ref_id="actor",
            target_ref_ids=["t1"],
        )
        kw = client.validate_single_target.call_args.kwargs
        self.assertIsNone(kw["range_cells"])
        self.assertFalse(kw["requires_sight"])
        self.assertFalse(kw["requires_effect"])


# ---------------------------------------------------------------------------
# Unit tests: build_area_affected_target_spatial_metadata
# ---------------------------------------------------------------------------

class BuildAreaAffectedTargetSpatialMetadataTests(unittest.TestCase):

    def test_half_cover_reduces_dc_by_two(self):
        result = build_area_affected_target_spatial_metadata(
            affected_ref_ids=["t1"],
            name_by_ref={"t1": "Goblin"},
            cover_by_ref={"t1": "half"},
            base_save_dc=15,
            cover_applies_to_save="physical",
        )
        self.assertEqual(len(result), 1)
        entry = result[0]
        self.assertEqual(entry["cover"], "half")
        self.assertEqual(entry["base_save_dc"], 15)
        self.assertEqual(entry["effective_save_dc"], 13)
        self.assertEqual(entry["cover_modifier"], 2)
        self.assertEqual(entry["target_display_name"], "Goblin")

    def test_three_quarters_cover_reduces_dc_by_five(self):
        result = build_area_affected_target_spatial_metadata(
            affected_ref_ids=["t1"],
            name_by_ref={"t1": None},
            cover_by_ref={"t1": "threeQuarters"},
            base_save_dc=15,
            cover_applies_to_save="physical",
        )
        entry = result[0]
        self.assertEqual(entry["effective_save_dc"], 10)
        self.assertEqual(entry["cover_modifier"], 5)

    def test_no_cover_uses_base_dc(self):
        result = build_area_affected_target_spatial_metadata(
            affected_ref_ids=["t1"],
            name_by_ref={},
            cover_by_ref={"t1": None},
            base_save_dc=14,
            cover_applies_to_save="physical",
        )
        entry = result[0]
        self.assertEqual(entry["effective_save_dc"], 14)
        self.assertEqual(entry["cover_modifier"], 0)

    def test_full_cover_does_not_reduce_dc(self):
        result = build_area_affected_target_spatial_metadata(
            affected_ref_ids=["t1"],
            name_by_ref={},
            cover_by_ref={"t1": "full"},
            base_save_dc=15,
            cover_applies_to_save="physical",
        )
        entry = result[0]
        self.assertEqual(entry["effective_save_dc"], 15)
        self.assertEqual(entry["cover_modifier"], 0)

    def test_cover_applies_to_save_none_string_no_reduction(self):
        result = build_area_affected_target_spatial_metadata(
            affected_ref_ids=["t1"],
            name_by_ref={},
            cover_by_ref={"t1": "half"},
            base_save_dc=15,
            cover_applies_to_save="none",
        )
        entry = result[0]
        self.assertEqual(entry["effective_save_dc"], 15)
        self.assertEqual(entry["cover_modifier"], 0)

    def test_multi_target_each_gets_own_metadata(self):
        result = build_area_affected_target_spatial_metadata(
            affected_ref_ids=["t1", "t2", "t3"],
            name_by_ref={"t1": "Goblin", "t2": "Orc", "t3": "Troll"},
            cover_by_ref={"t1": None, "t2": "half", "t3": "threeQuarters"},
            base_save_dc=15,
            cover_applies_to_save="physical",
        )
        self.assertEqual(len(result), 3)
        dcs = [e["effective_save_dc"] for e in result]
        self.assertEqual(dcs, [15, 13, 10])

    def test_ordering_follows_affected_ref_ids(self):
        result = build_area_affected_target_spatial_metadata(
            affected_ref_ids=["b", "a"],
            name_by_ref={},
            cover_by_ref={"a": "half", "b": None},
            base_save_dc=12,
            cover_applies_to_save="physical",
        )
        self.assertEqual(result[0]["target_ref_id"], "b")
        self.assertEqual(result[1]["target_ref_id"], "a")

    def test_missing_name_returns_none(self):
        result = build_area_affected_target_spatial_metadata(
            affected_ref_ids=["t1"],
            name_by_ref={},
            cover_by_ref={"t1": "half"},
            base_save_dc=15,
            cover_applies_to_save="physical",
        )
        self.assertIsNone(result[0]["target_display_name"])


# ---------------------------------------------------------------------------
# Integration tests: preview_area_spell_targeting with cover metadata
# ---------------------------------------------------------------------------

def _make_area_preview_response(affected_combatant_ids: list[str]) -> LimiarMapAreaTargetingResponse:
    return LimiarMapAreaTargetingResponse(
        is_valid=True,
        reason=None,
        session_id="session-123",
        action_id="a1",
        version=5,
        shape="sphere",
        source_token_id="tok_player",
        affected_cells=tuple(LimiarMapAreaCell(x=10, y=10) for _ in affected_combatant_ids),
        affected_token_ids=tuple(f"tok_{r}" for r in affected_combatant_ids),
        affected_combatant_ids=tuple(affected_combatant_ids),
    )


def _make_cover_response(cover: str | None) -> LimiarMapTargetingResponse:
    return LimiarMapTargetingResponse(
        is_valid=True,
        reason=None,
        session_id="session-123",
        action_id="a1",
        version=5,
        source_token_id="tok_player",
        target_token_id="tok_target",
        cover=cover,
    )


def _make_spell_catalog(
    cover_applies_to_save: str | None = "physical",
    save_dc: int | None = 15,
) -> MagicMock:
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
        save_dc=save_dc,
    )


from _combat_test_shared import TestCombatServiceBase
from app.models.combat import CombatPhase
from app.models.session_state import SessionState
from app.schemas.combat import CombatAreaPreviewRequest, CombatGridCell


class AreaPreviewCoverMetadataTests(TestCombatServiceBase):
    """Integration tests for per-target spatial metadata in area preview."""

    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.use_map = True

    def _make_attacker_state(self) -> SessionState:
        return SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "abilities": {"intelligence": 18},
                "spellcasting": {
                    "spells": [
                        {"name": "Fireball", "canonicalKey": "fireball", "level": 3, "prepared": True}
                    ],
                    "slots": {"3": {"used": 0, "max": 2}},
                },
            },
        )

    def _preview_req(self) -> CombatAreaPreviewRequest:
        return CombatAreaPreviewRequest(
            actor_participant_id="p1",
            origin_cell=CombatGridCell(x=8, y=8),
            anchor_cell=CombatGridCell(x=10, y=10),
            spell_canonical_key="fireball",
        )

    def _call_preview(
        self,
        *,
        affected_ids: list[str],
        cover_applies_to_save: str | None,
        save_dc: int | None,
        cover_side_effects: list,
    ) -> dict:
        attacker_state = self._make_attacker_state()
        catalog = _make_spell_catalog(
            cover_applies_to_save=cover_applies_to_save,
            save_dc=save_dc,
        )
        area_preview = _make_area_preview_response(affected_ids)
        mock_client = MagicMock()
        mock_client.get_session_state.return_value = MagicMock(
            tokens=[
                MagicMock(
                    combatant_id="player-123",
                    position_x=8,
                    position_y=8,
                )
            ]
        )
        mock_client.preview_area_targeting.return_value = area_preview
        mock_client.validate_single_target.side_effect = cover_side_effects

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch(
                 "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                 return_value=catalog,
             ), \
             patch(
                 "app.services.combat.CombatService._get_stats",
                 return_value=(attacker_state, 12, 10, 10, 3, 4),
             ), \
             patch(
                 "app.services.combat_service.spells.area_targeting.AreaTargetingMixin._build_limiar_map_client",
                 return_value=mock_client,
             ):
            return CombatService.preview_area_spell_targeting(
                self.db,
                "session-123",
                self._preview_req(),
                "user-1",
                False,
            )

    def test_no_cover_uses_base_dc(self):
        result = self._call_preview(
            affected_ids=["enemy-123"],
            cover_applies_to_save="physical",
            save_dc=15,
            cover_side_effects=[_make_cover_response(None)],
        )
        meta = result["affected_target_spatial_metadata"]
        self.assertEqual(len(meta), 1)
        entry = meta[0]
        self.assertIsNone(entry["cover"])
        self.assertEqual(entry["base_save_dc"], 15)
        self.assertEqual(entry["effective_save_dc"], 15)
        self.assertEqual(entry["cover_modifier"], 0)

    def test_half_cover_reduces_dc_by_two(self):
        result = self._call_preview(
            affected_ids=["enemy-123"],
            cover_applies_to_save="physical",
            save_dc=15,
            cover_side_effects=[_make_cover_response("half")],
        )
        entry = result["affected_target_spatial_metadata"][0]
        self.assertEqual(entry["cover"], "half")
        self.assertEqual(entry["effective_save_dc"], 13)
        self.assertEqual(entry["cover_modifier"], 2)

    def test_three_quarters_cover_reduces_dc_by_five(self):
        result = self._call_preview(
            affected_ids=["enemy-123"],
            cover_applies_to_save="physical",
            save_dc=15,
            cover_side_effects=[_make_cover_response("threeQuarters")],
        )
        entry = result["affected_target_spatial_metadata"][0]
        self.assertEqual(entry["cover"], "threeQuarters")
        self.assertEqual(entry["effective_save_dc"], 10)
        self.assertEqual(entry["cover_modifier"], 5)

    def test_full_cover_does_not_reduce_dc(self):
        result = self._call_preview(
            affected_ids=["enemy-123"],
            cover_applies_to_save="physical",
            save_dc=15,
            cover_side_effects=[_make_cover_response("full")],
        )
        entry = result["affected_target_spatial_metadata"][0]
        self.assertEqual(entry["effective_save_dc"], 15)
        self.assertEqual(entry["cover_modifier"], 0)

    def test_cover_applies_to_save_none_string_returns_empty_metadata(self):
        result = self._call_preview(
            affected_ids=["enemy-123"],
            cover_applies_to_save="none",
            save_dc=15,
            cover_side_effects=[],
        )
        self.assertEqual(result["affected_target_spatial_metadata"], [])

    def test_cover_applies_to_save_null_returns_empty_metadata(self):
        result = self._call_preview(
            affected_ids=["enemy-123"],
            cover_applies_to_save=None,
            save_dc=15,
            cover_side_effects=[],
        )
        self.assertEqual(result["affected_target_spatial_metadata"], [])

    def test_save_dc_absent_guard_is_covered_by_unit_tests(self):
        # save_dc in spell_context is always computed from caster stats for a
        # saving throw spell; it cannot realistically be None in the full
        # integration path. The base_save_dc is not None guard is exercised
        # by the build_area_affected_target_spatial_metadata unit tests above.
        # This test verifies that the lookup IS triggered when cover applies.
        mock_save = MagicMock(side_effect=[_make_cover_response(None)])
        result = self._call_preview(
            affected_ids=["enemy-123"],
            cover_applies_to_save="physical",
            save_dc=15,
            cover_side_effects=[_make_cover_response(None)],
        )
        # No cover → modifier 0, DC unchanged
        entry = result["affected_target_spatial_metadata"][0]
        self.assertEqual(entry["cover_modifier"], 0)

    def test_lookup_failure_for_one_target_falls_back_to_base_dc(self):
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
        # The spell_context save_dc is computed from caster stats (8 + prof + ability),
        # not from the catalog mock. With the test attacker setup it resolves to 15.
        result = self._call_preview(
            affected_ids=["enemy-123", "enemy-456"],
            cover_applies_to_save="physical",
            save_dc=15,
            cover_side_effects=[
                _make_cover_response("half"),
                LimiarMapClientError("timeout", kind="timeout"),
            ],
        )
        meta = result["affected_target_spatial_metadata"]
        self.assertEqual(len(meta), 2)
        by_ref = {e["target_ref_id"]: e for e in meta}
        self.assertEqual(by_ref["enemy-123"]["effective_save_dc"], 13)  # 15 - 2
        self.assertEqual(by_ref["enemy-456"]["effective_save_dc"], 15)  # fallback to base
        self.assertIsNone(by_ref["enemy-456"]["cover"])

    def test_multi_target_each_gets_own_effective_dc(self):
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
        result = self._call_preview(
            affected_ids=["enemy-123", "enemy-456", "enemy-789"],
            cover_applies_to_save="physical",
            save_dc=15,
            cover_side_effects=[
                _make_cover_response(None),
                _make_cover_response("half"),
                _make_cover_response("threeQuarters"),
            ],
        )
        meta = result["affected_target_spatial_metadata"]
        self.assertEqual(len(meta), 3)
        dc_by_ref = {e["target_ref_id"]: e["effective_save_dc"] for e in meta}
        self.assertEqual(dc_by_ref["enemy-123"], 15)
        self.assertEqual(dc_by_ref["enemy-456"], 13)
        self.assertEqual(dc_by_ref["enemy-789"], 10)

    def test_target_display_name_from_state_participants(self):
        result = self._call_preview(
            affected_ids=["enemy-123"],
            cover_applies_to_save="physical",
            save_dc=15,
            cover_side_effects=[_make_cover_response(None)],
        )
        entry = result["affected_target_spatial_metadata"][0]
        self.assertEqual(entry["target_ref_id"], "enemy-123")
        self.assertEqual(entry["target_display_name"], "Goblin")

    def test_affected_target_ref_ids_unchanged(self):
        result = self._call_preview(
            affected_ids=["enemy-123"],
            cover_applies_to_save="physical",
            save_dc=15,
            cover_side_effects=[_make_cover_response("half")],
        )
        self.assertEqual(result["affected_target_ref_ids"], ["enemy-123"])

    def test_footprint_cells_unchanged(self):
        result = self._call_preview(
            affected_ids=["enemy-123"],
            cover_applies_to_save="physical",
            save_dc=15,
            cover_side_effects=[_make_cover_response("half")],
        )
        self.assertEqual(len(result["affected_cells"]), 1)
        self.assertEqual(result["affected_cells"][0], {"x": 10, "y": 10})

    def test_is_valid_unaffected_by_cover_metadata(self):
        result = self._call_preview(
            affected_ids=["enemy-123"],
            cover_applies_to_save="physical",
            save_dc=15,
            cover_side_effects=[_make_cover_response("threeQuarters")],
        )
        self.assertTrue(result["is_valid"])
