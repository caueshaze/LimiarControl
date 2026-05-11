from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.combat import CombatCastSpellRequest, CombatGridCell
from app.services.combat import CombatService, CombatServiceError


def _state() -> CombatState:
    return CombatState(
        id="c1",
        session_id="s1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        use_map=True,
        participants=[
            {"id": "p1", "ref_id": "player-1", "kind": "player", "display_name": "Lia", "status": "active", "team": "players", "visible": True, "actor_user_id": "u1"},
        ],
    )


def _attacker_state() -> SessionState:
    return SessionState(
        id="ss1",
        session_id="s1",
        player_user_id="u1",
        state_json={"spellcasting": {"spells": [{"name": "Misty Step", "canonicalKey": "misty_step", "level": 2, "prepared": True}], "slots": {"2": {"used": 0, "max": 2}}}},
    )


class MistyStepTeleportTests(unittest.IsolatedAsyncioTestCase):
    async def test_requires_destination_anchor_cell(self):
        state = _state()
        attacker_state = _attacker_state()
        req = CombatCastSpellRequest(actor_participant_id="p1", spell_canonical_key="misty_step")
        spell_context = {"spell_name": "Misty Step", "spell_canonical_key": "misty_step", "spell_mode": "teleport", "slot_level": 2, "action_cost": "bonus_action"}

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
        ):
            with self.assertRaises(CombatServiceError):
                await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)
        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["2"]["used"], 0)

    async def test_invalid_destination_does_not_consume_slot_or_emit_success_log(self):
        state = _state()
        attacker_state = _attacker_state()
        req = CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="misty_step",
            anchor_cell=CombatGridCell(x=99, y=99),
        )
        spell_context = {"spell_name": "Misty Step", "spell_canonical_key": "misty_step", "spell_mode": "teleport", "slot_level": 2, "action_cost": "bonus_action"}
        map_client = MagicMock(move_combatant=MagicMock(return_value=SimpleNamespace(is_valid=False, reason="out_of_range")))

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat.CombatService._build_limiar_map_client", return_value=map_client),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock) as emit_log,
        ):
            with self.assertRaises(CombatServiceError):
                await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)
        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["2"]["used"], 0)
        emit_log.assert_not_called()

    async def test_valid_destination_consumes_single_slot_and_emits_state(self):
        state = _state()
        attacker_state = _attacker_state()
        req = CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="misty_step",
            anchor_cell=CombatGridCell(x=10, y=7),
        )
        spell_context = {"spell_name": "Misty Step", "spell_canonical_key": "misty_step", "spell_mode": "teleport", "slot_level": 2, "action_cost": "bonus_action"}
        map_client = MagicMock(
            move_combatant=MagicMock(
                return_value=SimpleNamespace(is_valid=True, reason=None, destination_cell=SimpleNamespace(x=10, y=7), source_cell=SimpleNamespace(x=5, y=5), path=[], path_cost_units=0, movement_budget=0, movement_speed_cells=0, remaining_budget=0, version=1, source_elevation_meters=0, destination_elevation_meters=0)
            )
        )

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat.CombatService._build_limiar_map_client", return_value=map_client),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock) as emit_state,
        ):
            result = await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)
        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["2"]["used"], 1)
        self.assertEqual(result["action_kind"], "teleport")
        self.assertEqual(result["damage"], 0)
        self.assertIsNone(result["pending_spell_id"])
        self.assertIsNone(result["pending_save_id"])
        emit_state.assert_awaited()

    async def test_large_2x2_partially_blocked_destination_fails_without_side_effects(self):
        state = _state()
        attacker_state = _attacker_state()
        req = CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="misty_step",
            anchor_cell=CombatGridCell(x=12, y=9),
        )
        spell_context = {
            "spell_name": "Misty Step",
            "spell_canonical_key": "misty_step",
            "spell_mode": "teleport",
            "slot_level": 2,
            "action_cost": "bonus_action",
        }
        # Authoritative engine rejects destination because 2x2 footprint does not fit
        # (classic case: anchor looks free, one footprint cell is blocked).
        map_client = MagicMock(
            move_combatant=MagicMock(
                return_value=SimpleNamespace(is_valid=False, reason="invalid_effective_footprint")
            )
        )

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat.CombatService._build_limiar_map_client", return_value=map_client),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock) as emit_state,
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock) as emit_log,
        ):
            with self.assertRaises(CombatServiceError):
                await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)

        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["2"]["used"], 0)
        self.assertNotIn("pending_attack", state.participants[0])
        self.assertNotIn("pending_save", state.participants[0])
        emit_state.assert_not_called()
        emit_log.assert_not_called()

    async def test_large_2x2_fully_free_destination_succeeds(self):
        state = _state()
        attacker_state = _attacker_state()
        req = CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="misty_step",
            anchor_cell=CombatGridCell(x=8, y=6),
        )
        spell_context = {
            "spell_name": "Misty Step",
            "spell_canonical_key": "misty_step",
            "spell_mode": "teleport",
            "slot_level": 2,
            "action_cost": "bonus_action",
        }
        # Authoritative engine accepts destination for full 2x2 footprint fit.
        map_client = MagicMock(
            move_combatant=MagicMock(
                return_value=SimpleNamespace(
                    is_valid=True,
                    reason=None,
                    destination_cell=SimpleNamespace(x=8, y=6),
                    source_cell=SimpleNamespace(x=3, y=3),
                    path=[],
                    path_cost_units=0,
                    movement_budget=0,
                    movement_speed_cells=0,
                    remaining_budget=0,
                    version=5,
                    source_elevation_meters=0,
                    destination_elevation_meters=0,
                )
            )
        )

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat.CombatService._build_limiar_map_client", return_value=map_client),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock) as emit_state,
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock) as emit_log,
        ):
            result = await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)

        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["2"]["used"], 1)
        self.assertEqual(result["action_kind"], "teleport")
        self.assertEqual(result["destination_cell"], {"x": 8, "y": 6})
        emit_state.assert_awaited()
        emit_log.assert_awaited()
