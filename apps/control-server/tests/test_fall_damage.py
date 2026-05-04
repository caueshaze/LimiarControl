from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService, CombatServiceError
from app.services.combat_service.fall_damage import (
    FALL_DAMAGE_DIE_SIDES,
    FALL_DAMAGE_METERS_PER_DIE,
    FALL_DAMAGE_TYPE,
    MAX_FALL_DAMAGE_DICE,
    FallDamageComputation,
    compute_fall_damage,
)


class TestComputeFallDamage(unittest.TestCase):
    def _assert_no_damage(self, result: FallDamageComputation, original_height: float) -> None:
        self.assertFalse(result.causes_damage)
        self.assertEqual(result.dice_count, 0)
        self.assertIsNone(result.damage_formula)
        self.assertEqual(result.height_meters, original_height)
        self.assertEqual(result.effective_height_meters, max(0, original_height))

    def _assert_damage(self, result: FallDamageComputation, expected_dice: int, original_height: float) -> None:
        self.assertTrue(result.causes_damage)
        self.assertEqual(result.dice_count, expected_dice)
        self.assertEqual(result.damage_formula, f"{expected_dice}d{FALL_DAMAGE_DIE_SIDES}")
        self.assertEqual(result.dice_sides, FALL_DAMAGE_DIE_SIDES)
        self.assertEqual(result.damage_type, FALL_DAMAGE_TYPE)
        self.assertEqual(result.height_meters, original_height)
        self.assertEqual(result.effective_height_meters, max(0, original_height))

    def test_zero_height(self):
        self._assert_no_damage(compute_fall_damage(0), 0)

    def test_below_threshold_1_5(self):
        self._assert_no_damage(compute_fall_damage(1.5), 1.5)

    def test_below_threshold_2_99(self):
        self._assert_no_damage(compute_fall_damage(2.99), 2.99)

    def test_exactly_3m_is_1d6(self):
        self._assert_damage(compute_fall_damage(3), 1, 3)

    def test_5_99m_still_1d6(self):
        self._assert_damage(compute_fall_damage(5.99), 1, 5.99)

    def test_6m_is_2d6(self):
        self._assert_damage(compute_fall_damage(6), 2, 6)

    def test_9m_is_3d6(self):
        self._assert_damage(compute_fall_damage(9), 3, 9)

    def test_60m_hits_cap_20d6(self):
        self._assert_damage(compute_fall_damage(60), 20, 60)

    def test_90m_capped_at_20d6(self):
        self._assert_damage(compute_fall_damage(90), 20, 90)

    def test_negative_height_normalizes_to_zero(self):
        result = compute_fall_damage(-1)
        self._assert_no_damage(result, -1)
        self.assertEqual(result.effective_height_meters, 0)

    def test_constants_are_correct(self):
        self.assertEqual(FALL_DAMAGE_METERS_PER_DIE, 3)
        self.assertEqual(FALL_DAMAGE_DIE_SIDES, 6)
        self.assertEqual(MAX_FALL_DAMAGE_DICE, 20)
        self.assertEqual(FALL_DAMAGE_TYPE, "bludgeoning")


def _make_active_state() -> CombatState:
    return CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=[
            {
                "id": "player-p1",
                "ref_id": "player-ref-1",
                "kind": "player",
                "display_name": "Hero",
                "initiative": 10,
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-1",
            },
            {
                "id": "entity-e1",
                "ref_id": "entity-ref-1",
                "kind": "session_entity",
                "display_name": "Goblin",
                "initiative": 8,
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
            },
        ],
    )


def _async_noop(*args, **kwargs):
    pass


class TestResolveFallDamage(unittest.IsolatedAsyncioTestCase):
    @patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_state", new_callable=AsyncMock)
    @patch.object(CombatService, "get_state")
    async def test_rejects_non_gm(self, mock_get_state, mock_emit_state, mock_emit_log):
        mock_get_state.return_value = _make_active_state()
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService.resolve_fall(
                MagicMock(), "session-1", "entity-e1", 6.0, "user-1", is_gm=False,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    @patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_state", new_callable=AsyncMock)
    @patch.object(CombatService, "get_state")
    async def test_rejects_unknown_participant(self, mock_get_state, mock_emit_state, mock_emit_log):
        mock_get_state.return_value = _make_active_state()
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService.resolve_fall(
                MagicMock(), "session-1", "nonexistent", 6.0, "user-1", is_gm=True,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    @patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_state", new_callable=AsyncMock)
    @patch.object(CombatService, "get_state")
    async def test_zero_height_no_damage(self, mock_get_state, mock_emit_state, mock_emit_log):
        mock_get_state.return_value = _make_active_state()
        db = MagicMock()

        result = await CombatService.resolve_fall(
            db, "session-1", "entity-e1", 0.0, "user-1", is_gm=True,
        )

        resolution = result["resolution"]
        self.assertFalse(resolution["causes_damage"])
        self.assertFalse(resolution["applied_damage"])
        self.assertEqual(resolution["damage_total"], 0)
        self.assertIsNone(result["concentration_check"])
        mock_emit_state.assert_called_once()
        mock_emit_log.assert_called_once()

    @patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_state", new_callable=AsyncMock)
    @patch.object(CombatService, "get_state")
    async def test_below_threshold_no_damage(self, mock_get_state, mock_emit_state, mock_emit_log):
        mock_get_state.return_value = _make_active_state()
        db = MagicMock()

        result = await CombatService.resolve_fall(
            db, "session-1", "entity-e1", 2.99, "user-1", is_gm=True,
        )

        resolution = result["resolution"]
        self.assertFalse(resolution["causes_damage"])
        self.assertFalse(resolution["applied_damage"])
        self.assertEqual(resolution["damage_total"], 0)

    @patch("app.services.combat_service.damage_admin._roll_dice_expression", return_value=4)
    @patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_state", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_entity_hp_update", new_callable=AsyncMock)
    @patch.object(CombatService, "_apply_damage_to_target")
    @patch.object(CombatService, "get_state")
    async def test_3m_fall_rolls_1d6_and_applies_damage_to_entity(
        self, mock_get_state, mock_apply_damage, mock_emit_entity_hp, mock_emit_state, mock_emit_log, mock_roll,
    ):
        mock_get_state.return_value = _make_active_state()
        mock_apply_damage.return_value = (6, "", 10, None)
        db = MagicMock()

        result = await CombatService.resolve_fall(
            db, "session-1", "entity-e1", 3.0, "user-1", is_gm=True,
        )

        resolution = result["resolution"]
        self.assertTrue(resolution["causes_damage"])
        self.assertTrue(resolution["applied_damage"])
        self.assertEqual(resolution["dice_count"], 1)
        self.assertEqual(resolution["damage_total"], 4)
        self.assertEqual(resolution["damage_type"], "bludgeoning")
        self.assertEqual(result["new_hp"], 6)
        mock_apply_damage.assert_called_once_with(
            db, "entity-ref-1", "session_entity", 4,
            damage_type="bludgeoning", is_crit=False, state=mock_get_state.return_value,
        )
        mock_emit_entity_hp.assert_called_once()

    @patch("app.services.combat_service.damage_admin._roll_dice_expression", return_value=7)
    @patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_state", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_entity_hp_update", new_callable=AsyncMock)
    @patch.object(CombatService, "_apply_damage_to_target")
    @patch.object(CombatService, "get_state")
    async def test_6m_fall_rolls_2d6(
        self, mock_get_state, mock_apply_damage, mock_emit_entity_hp, mock_emit_state, mock_emit_log, mock_roll,
    ):
        mock_get_state.return_value = _make_active_state()
        mock_apply_damage.return_value = (3, "", 10, None)
        db = MagicMock()

        result = await CombatService.resolve_fall(
            db, "session-1", "entity-e1", 6.0, "user-1", is_gm=True,
        )

        self.assertEqual(result["resolution"]["dice_count"], 2)
        self.assertEqual(result["resolution"]["damage_total"], 7)

    @patch("app.services.combat_service.damage_admin._roll_dice_expression", return_value=40)
    @patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_state", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_entity_hp_update", new_callable=AsyncMock)
    @patch.object(CombatService, "_apply_damage_to_target")
    @patch.object(CombatService, "get_state")
    async def test_90m_fall_capped_at_20d6(
        self, mock_get_state, mock_apply_damage, mock_emit_entity_hp, mock_emit_state, mock_emit_log, mock_roll,
    ):
        mock_get_state.return_value = _make_active_state()
        mock_apply_damage.return_value = (0, "", 10, None)
        db = MagicMock()

        result = await CombatService.resolve_fall(
            db, "session-1", "entity-e1", 90.0, "user-1", is_gm=True,
        )

        self.assertEqual(result["resolution"]["dice_count"], 20)
        self.assertEqual(result["resolution"]["damage_total"], 40)

    @patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_state", new_callable=AsyncMock)
    @patch.object(CombatService, "get_state")
    async def test_no_damage_log_message(self, mock_get_state, mock_emit_state, mock_emit_log):
        mock_get_state.return_value = _make_active_state()
        db = MagicMock()

        await CombatService.resolve_fall(
            db, "session-1", "entity-e1", 2.0, "user-1", is_gm=True,
        )

        log_payload = mock_emit_log.call_args[0][4]
        self.assertIn("takes no damage", log_payload["message"])
        self.assertEqual(log_payload["source"], "environmental_fall")

    @patch("app.services.combat_service.damage_admin._roll_dice_expression", return_value=7)
    @patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_state", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_entity_hp_update", new_callable=AsyncMock)
    @patch.object(CombatService, "_apply_damage_to_target")
    @patch.object(CombatService, "get_state")
    async def test_damaging_fall_log_message(
        self, mock_get_state, mock_apply_damage, mock_emit_entity_hp, mock_emit_state, mock_emit_log, mock_roll,
    ):
        mock_get_state.return_value = _make_active_state()
        mock_apply_damage.return_value = (3, "", 10, None)
        db = MagicMock()

        await CombatService.resolve_fall(
            db, "session-1", "entity-e1", 6.0, "user-1", is_gm=True,
        )

        log_payload = mock_emit_log.call_args[0][4]
        self.assertIn("falls 6.0m and takes", log_payload["message"])
        self.assertIn("7 bludgeoning damage", log_payload["message"])
        self.assertEqual(log_payload["source"], "environmental_fall")

    @patch("app.services.combat_service.damage_admin._roll_dice_expression", return_value=5)
    @patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_state", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_player_state_update", new_callable=AsyncMock)
    @patch.object(CombatService, "_get_stats")
    @patch.object(CombatService, "_apply_damage_to_target")
    @patch.object(CombatService, "get_state")
    async def test_player_participant_emits_player_state_update(
        self, mock_get_state, mock_apply_damage, mock_get_stats, mock_emit_player, mock_emit_state, mock_emit_log, mock_roll,
    ):
        mock_get_state.return_value = _make_active_state()
        mock_apply_damage.return_value = (15, "", 20, None)
        mock_get_stats.return_value = (MagicMock(),)
        db = MagicMock()

        result = await CombatService.resolve_fall(
            db, "session-1", "player-p1", 6.0, "user-1", is_gm=True,
        )

        self.assertEqual(result["resolution"]["participant_id"], "player-p1")
        mock_emit_player.assert_called_once()
        mock_apply_damage.assert_called_once_with(
            db, "player-ref-1", "player", 5,
            damage_type="bludgeoning", is_crit=False, state=mock_get_state.return_value,
        )


if __name__ == "__main__":
    unittest.main()
