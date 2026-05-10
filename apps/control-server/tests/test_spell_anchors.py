from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.combat_service.exceptions import CombatServiceError
from app.services.combat_service.spell_anchors import (
    create_spell_anchor,
    get_spell_anchor_by_id,
    get_spell_anchors_for_owner,
    move_spell_anchor,
    remove_spell_anchor,
    validate_spell_anchor_placement,
)


def _make_state() -> CombatState:
    state = CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=[
            {
                "id": "p1",
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Hero",
                "initiative": 18,
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-1",
                "active_effects": [],
                "turn_resources": {
                    "action_used": False,
                    "bonus_action_used": False,
                    "reaction_used": False,
                },
            },
            {
                "id": "e1",
                "ref_id": "enemy-1",
                "kind": "session_entity",
                "display_name": "Goblin",
                "initiative": 12,
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
                "active_effects": [],
                "turn_resources": {
                    "action_used": False,
                    "bonus_action_used": False,
                    "reaction_used": False,
                },
            },
        ],
        map_selection={
            "gridWidth": 20,
            "gridHeight": 20,
            "blockedCells": [{"x": 6, "y": 6}],
            "obstacles": [],
        },
        use_map=True,
    )
    state.active_area_effects = []
    state.spell_anchors = []
    return state


class TestSpellAnchorHelpers(unittest.TestCase):
    def test_create_spell_anchor_persists_position_and_metadata(self):
        state = _make_state()

        created = create_spell_anchor(
            state,
            anchor={
                "source_spell_key": "spiritual_weapon",
                "source_spell_name": "Arma Espiritual",
                "owner_participant_id": "p1",
                "created_by_participant_id": "p1",
                "position": {"x": 8, "y": 5},
                "remaining_rounds": 10,
                "expires_on": "turn_start",
                "expires_at_participant_id": "p1",
                "metadata": {"debug": True},
            },
        )

        self.assertEqual(created["render_kind"], "generic")
        self.assertEqual(created["position"], {"x": 8, "y": 5})
        self.assertEqual(created["metadata"], {"debug": True})
        self.assertEqual(len(state.spell_anchors), 1)

    def test_spell_anchor_lookup_by_id_and_owner(self):
        state = _make_state()
        created = create_spell_anchor(
            state,
            anchor={
                "source_spell_key": "spiritual_weapon",
                "owner_participant_id": "p1",
                "created_by_participant_id": "p1",
                "position": {"x": 8, "y": 5},
                "remaining_rounds": 10,
                "expires_on": "turn_start",
                "expires_at_participant_id": "p1",
            },
        )

        self.assertEqual(get_spell_anchor_by_id(state, created["id"])["id"], created["id"])
        self.assertEqual(len(get_spell_anchors_for_owner(state, "p1")), 1)

    def test_spell_anchor_move_updates_position(self):
        state = _make_state()
        created = create_spell_anchor(
            state,
            anchor={
                "source_spell_key": "spiritual_weapon",
                "owner_participant_id": "p1",
                "created_by_participant_id": "p1",
                "position": {"x": 8, "y": 5},
                "remaining_rounds": 10,
                "expires_on": "turn_start",
                "expires_at_participant_id": "p1",
            },
        )

        moved = move_spell_anchor(
            state,
            anchor_id=created["id"],
            destination={"x": 10, "y": 5},
            max_movement_meters=6,
            battle_map=state.map_selection,
        )
        self.assertEqual(moved["position"], {"x": 10, "y": 5})

    def test_spell_anchor_move_rejects_invalid_destination(self):
        state = _make_state()
        created = create_spell_anchor(
            state,
            anchor={
                "source_spell_key": "spiritual_weapon",
                "owner_participant_id": "p1",
                "created_by_participant_id": "p1",
                "position": {"x": 8, "y": 5},
                "remaining_rounds": 10,
                "expires_on": "turn_start",
                "expires_at_participant_id": "p1",
            },
        )

        with self.assertRaises(CombatServiceError):
            move_spell_anchor(
                state,
                anchor_id=created["id"],
                destination={"x": 6, "y": 6},
                max_movement_meters=6,
                battle_map=state.map_selection,
            )

    def test_spell_anchor_move_rejects_out_of_range_destination(self):
        state = _make_state()
        created = create_spell_anchor(
            state,
            anchor={
                "source_spell_key": "spiritual_weapon",
                "owner_participant_id": "p1",
                "created_by_participant_id": "p1",
                "position": {"x": 8, "y": 5},
                "remaining_rounds": 10,
                "expires_on": "turn_start",
                "expires_at_participant_id": "p1",
            },
        )

        with self.assertRaises(CombatServiceError):
            move_spell_anchor(
                state,
                anchor_id=created["id"],
                destination={"x": 14, "y": 5},
                max_movement_meters=6,
                battle_map=state.map_selection,
            )

    def test_validate_spell_anchor_placement_accepts_valid_point(self):
        validate_spell_anchor_placement(
            caster_position={"x": 4, "y": 4},
            target_position={"x": 8, "y": 5},
            range_meters=9,
            requires_point_sight=False,
            requires_point_effect=False,
            battle_map=_make_state().map_selection,
        )

    def test_validate_spell_anchor_placement_rejects_out_of_range_point(self):
        with self.assertRaises(CombatServiceError):
            validate_spell_anchor_placement(
                caster_position={"x": 4, "y": 4},
                target_position={"x": 12, "y": 12},
                range_meters=6,
                requires_point_sight=False,
                requires_point_effect=False,
                battle_map=_make_state().map_selection,
            )

    def test_validate_spell_anchor_placement_rejects_blocked_line_of_effect(self):
        with self.assertRaises(CombatServiceError):
            validate_spell_anchor_placement(
                caster_position={"x": 4, "y": 4},
                target_position={"x": 6, "y": 6},
                range_meters=6,
                requires_point_sight=False,
                requires_point_effect=True,
                battle_map=_make_state().map_selection,
            )

    def test_remove_spell_anchor(self):
        state = _make_state()
        created = create_spell_anchor(
            state,
            anchor={
                "source_spell_key": "spiritual_weapon",
                "owner_participant_id": "p1",
                "created_by_participant_id": "p1",
                "position": {"x": 8, "y": 5},
                "remaining_rounds": 10,
                "expires_on": "turn_start",
                "expires_at_participant_id": "p1",
            },
        )

        removed = remove_spell_anchor(state, created["id"])
        self.assertEqual(removed["id"], created["id"])
        self.assertEqual(state.spell_anchors, [])


class TestSpellAnchorLifecycle(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = MagicMock()
        self.state = _make_state()

    async def test_spell_anchor_expires_on_owner_turn_start_after_ten_triggers(self):
        create_spell_anchor(
            self.state,
            anchor={
                "id": "spell_anchor:1",
                "source_spell_key": "spiritual_weapon",
                "source_spell_name": "Arma Espiritual",
                "owner_participant_id": "p1",
                "created_by_participant_id": "p1",
                "position": {"x": 8, "y": 5},
                "remaining_rounds": 10,
                "expires_on": "turn_start",
                "expires_at_participant_id": "p1",
            },
        )

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock),
            patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock),
        ):
            for trigger_index in range(9):
                self.state.current_turn_index = 1
                await CombatService.next_turn(self.db, "session-1", "gm-user", True)
                self.assertEqual(self.state.spell_anchors[0]["remaining_rounds"], 9 - trigger_index)
                self.state.current_turn_index = 0
                await CombatService.next_turn(self.db, "session-1", "user-1", False)

            self.state.current_turn_index = 1
            await CombatService.next_turn(self.db, "session-1", "gm-user", True)

        self.assertEqual(self.state.spell_anchors, [])

    async def test_spell_anchor_is_not_removed_when_owner_effects_change(self):
        create_spell_anchor(
            self.state,
            anchor={
                "id": "spell_anchor:1",
                "source_spell_key": "spiritual_weapon",
                "owner_participant_id": "p1",
                "created_by_participant_id": "p1",
                "position": {"x": 8, "y": 5},
                "remaining_rounds": 10,
                "expires_on": "turn_start",
                "expires_at_participant_id": "p1",
            },
        )
        self.state.participants[0]["active_effects"] = [
            {
                "id": "eff-1",
                "kind": "condition",
                "condition_type": "prone",
                "duration_type": "manual",
                "created_at": "2026-01-01T00:00:00Z",
                "metadata": {},
            }
        ]
        self.state.participants[0]["active_effects"] = []

        self.assertEqual(len(self.state.spell_anchors), 1)

    async def test_end_combat_clears_spell_anchors(self):
        create_spell_anchor(
            self.state,
            anchor={
                "id": "spell_anchor:1",
                "source_spell_key": "spiritual_weapon",
                "owner_participant_id": "p1",
                "created_by_participant_id": "p1",
                "position": {"x": 8, "y": 5},
                "remaining_rounds": 10,
                "expires_on": "turn_start",
                "expires_at_participant_id": "p1",
            },
        )

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock),
            patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock),
        ):
            result = await CombatService.end_combat(self.db, "session-1", is_gm=True)

        self.assertEqual(result.spell_anchors, [])
