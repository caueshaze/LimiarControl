import unittest
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.schemas.combat import CombatAttackRequest, CombatStandardActionRequest
from app.schemas.roll import RollActorStats
from app.services.combat import CombatService, CombatServiceError


class CombatStandardActionTestsMixin:

    def _make_active_state(self):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        for p in self.state.participants:
            p["turn_resources"] = {
                "action_used": False,
                "bonus_action_used": False,
                "reaction_used": False,
            }
            p["active_effects"] = []

    # ---- dodge ----

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_dodge_applies_dodging_effect(self, mock_emit_log, mock_emit_state):
        self._make_active_state()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            result = await CombatService.standard_action(
                self.db, "session-123",
                CombatStandardActionRequest(action="dodge"),
                "user-1", False,
            )

        self.assertEqual(result["action"], "dodge")
        self.assertTrue(result["effect_applied"])
        actor = self.state.participants[0]
        effects = actor.get("active_effects", [])
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["kind"], "dodging")
        self.assertEqual(effects[0]["duration_type"], "until_turn_start")
        self.assertEqual(effects[0]["expires_at_participant_id"], actor["id"])

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_dodge_consumes_action(self, mock_emit_log, mock_emit_state):
        self._make_active_state()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            await CombatService.standard_action(
                self.db, "session-123",
                CombatStandardActionRequest(action="dodge"),
                "user-1", False,
            )

        self.assertTrue(self.state.participants[0]["turn_resources"]["action_used"])

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_dodge_cannot_be_used_twice(self, mock_emit_log, mock_emit_state):
        self._make_active_state()
        self.state.participants[0]["turn_resources"]["action_used"] = True

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.standard_action(
                    self.db, "session-123",
                    CombatStandardActionRequest(action="dodge"),
                    "user-1", False,
                )
        self.assertIn("action", str(ctx.exception).lower())

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_dodge_causes_disadvantage_on_attacker(
        self, mock_emit_log, mock_emit_state, mock_emit_hp
    ):
        """p1 (player) attacks e1 which is dodging — should get disadvantage."""
        self._make_active_state()
        # e1 (enemy, index 1) is dodging
        self.state.participants[1]["active_effects"] = [{
            "id": "eff-1",
            "kind": "dodging",
            "duration_type": "until_turn_start",
            "condition_type": None,
            "numeric_value": None,
            "remaining_rounds": None,
            "expires_on": "turn_start",
            "expires_at_participant_id": "e1",
            "source_participant_id": "e1",
            "created_at": "2026-01-01T00:00:00+00:00",
        }]
        # p1's turn (index 0)
        self.state.current_turn_index = 0

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(), 10, 14, 12, 2, 0),  # attacker (p1)
                (MagicMock(), 15, 10, 10, 2, 0),  # defender (e1)
            ]):
                with patch("random.randint", return_value=5):
                    result = await CombatService.attack(
                        self.db, "session-123",
                        CombatAttackRequest(target_ref_id="enemy-123"),
                        "user-1", False,
                    )

        roll_result = result.get("roll_result")
        self.assertIsNotNone(roll_result)
        self.assertEqual(roll_result.advantage_mode, "disadvantage")

    # ---- help ----

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_help_applies_advantage_to_target(self, mock_emit_log, mock_emit_state):
        self._make_active_state()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            result = await CombatService.standard_action(
                self.db, "session-123",
                CombatStandardActionRequest(
                    action="help",
                    target_participant_id="e1",
                ),
                "user-1", False,
            )

        self.assertTrue(result["effect_applied"])
        target = self.state.participants[1]  # e1
        effects = target.get("active_effects", [])
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["kind"], "advantage_on_attacks")
        self.assertEqual(effects[0]["expires_at_participant_id"], "e1")

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_help_requires_target(self, mock_emit_log, mock_emit_state):
        self._make_active_state()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError):
                await CombatService.standard_action(
                    self.db, "session-123",
                    CombatStandardActionRequest(action="help"),
                    "user-1", False,
                )

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_help_advantage_consumed_on_first_attack(
        self, mock_emit_log, mock_emit_state, mock_emit_hp
    ):
        """advantage_on_attacks on p1 is removed after their first attack roll."""
        self._make_active_state()
        self.state.participants[0]["active_effects"] = [{
            "id": "eff-adv",
            "kind": "advantage_on_attacks",
            "duration_type": "until_turn_start",
            "condition_type": None,
            "numeric_value": None,
            "remaining_rounds": None,
            "expires_on": "turn_start",
            "expires_at_participant_id": "p1",
            "source_participant_id": "e1",
            "created_at": "2026-01-01T00:00:00+00:00",
        }]

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(), 10, 16, 14, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0),
            ]):
                with patch("random.randint", return_value=12):
                    await CombatService.attack(
                        self.db, "session-123",
                        CombatAttackRequest(target_ref_id="enemy-123"),
                        "user-1", False,
                    )

        effects = self.state.participants[0].get("active_effects", [])
        adv_effects = [e for e in effects if e["kind"] == "advantage_on_attacks"]
        self.assertEqual(len(adv_effects), 0, "advantage_on_attacks must be consumed after first attack")

    # ---- hide ----

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_hide_applies_hidden_effect_and_returns_roll(self, mock_emit_log, mock_emit_state):
        self._make_active_state()

        # skills is dict[str, int] — final modifier values
        fake_stats = RollActorStats(
            display_name="Hero",
            abilities={"dexterity": 16},
            skills={"stealth": 5},  # +2 prof + +3 dex
            proficiency_bonus=2,
            actor_kind="player",
            actor_ref_id="player-123",
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._build_roll_actor_stats_for_skill",
                return_value=fake_stats,
            ):
                with patch("random.randint", return_value=14):
                    result = await CombatService.standard_action(
                        self.db, "session-123",
                        CombatStandardActionRequest(action="hide", roll_source="system"),
                        "user-1", False,
                    )

        self.assertTrue(result["effect_applied"])
        roll_result = result.get("roll_result")
        self.assertIsNotNone(roll_result)
        self.assertEqual(roll_result.roll_type, "skill")

        actor = self.state.participants[0]
        effects = actor.get("active_effects", [])
        hidden_effects = [e for e in effects if e["kind"] == "hidden"]
        self.assertEqual(len(hidden_effects), 1)
        self.assertEqual(hidden_effects[0]["duration_type"], "manual")
        self.assertIsNone(hidden_effects[0]["expires_on"])

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_hide_manual_roll(self, mock_emit_log, mock_emit_state):
        """Hide should accept a manual_roll value and use it as the d20 result."""
        self._make_active_state()

        fake_stats = RollActorStats(
            display_name="Hero",
            abilities={"dexterity": 14},
            skills=None,
            proficiency_bonus=2,
            actor_kind="player",
            actor_ref_id="player-123",
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._build_roll_actor_stats_for_skill",
                return_value=fake_stats,
            ):
                result = await CombatService.standard_action(
                    self.db, "session-123",
                    CombatStandardActionRequest(
                        action="hide",
                        roll_source="manual",
                        manual_roll=18,
                    ),
                    "user-1", False,
                )

        roll = result.get("roll_result")
        self.assertIsNotNone(roll)
        # The d20 portion should reflect the manual value
        self.assertEqual(roll.selected_roll, 18)
        self.assertEqual(roll.roll_source, "manual")

    # ---- use_object ----

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_use_object_logs_description(self, mock_emit_log, mock_emit_state):
        self._make_active_state()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            result = await CombatService.standard_action(
                self.db, "session-123",
                CombatStandardActionRequest(
                    action="use_object",
                    description="drink healing potion",
                ),
                "user-1", False,
            )

        self.assertFalse(result["effect_applied"])
        self.assertIn("healing potion", result["message"])
        self.assertIn("Hero", result["message"])
        mock_emit_log.assert_called_once()

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_use_object_without_description_uses_fallback(self, mock_emit_log, mock_emit_state):
        self._make_active_state()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            result = await CombatService.standard_action(
                self.db, "session-123",
                CombatStandardActionRequest(action="use_object"),
                "user-1", False,
            )

        self.assertIn("an object", result["message"])

    # ---- dash / disengage ----

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_dash_logs_and_no_effect(self, mock_emit_log, mock_emit_state):
        self._make_active_state()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            result = await CombatService.standard_action(
                self.db, "session-123",
                CombatStandardActionRequest(action="dash"),
                "user-1", False,
            )

        self.assertFalse(result["effect_applied"])
        self.assertIn("Dash", result["message"])
        self.assertEqual(result["actor_name"], "Hero")
        self.assertEqual(len(self.state.participants[0].get("active_effects", [])), 0)

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_disengage_logs_and_no_effect(self, mock_emit_log, mock_emit_state):
        self._make_active_state()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            result = await CombatService.standard_action(
                self.db, "session-123",
                CombatStandardActionRequest(action="disengage"),
                "user-1", False,
            )

        self.assertFalse(result["effect_applied"])
        self.assertIn("Disengage", result["message"])
        self.assertEqual(len(self.state.participants[0].get("active_effects", [])), 0)

    # ---- GM override ----

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_gm_can_dodge_even_with_action_used(self, mock_emit_log, mock_emit_state):
        self._make_active_state()
        self.state.participants[0]["turn_resources"]["action_used"] = True

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            result = await CombatService.standard_action(
                self.db, "session-123",
                CombatStandardActionRequest(action="dodge"),
                "user-gm", True,
            )

        self.assertTrue(result["effect_applied"])
        effects = self.state.participants[0].get("active_effects", [])
        self.assertEqual(effects[0]["kind"], "dodging")

    # ---- dodge + existing advantage cancel to normal ----

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_dodge_and_existing_advantage_cancel_to_normal(
        self, mock_emit_log, mock_emit_state, mock_emit_hp
    ):
        """p1 (attacker) has advantage_on_attacks, e1 (target) is dodging — adv+dis = normal."""
        self._make_active_state()
        # e1 (enemy, index 1) is dodging
        self.state.participants[1]["active_effects"] = [{
            "id": "eff-dodge",
            "kind": "dodging",
            "duration_type": "until_turn_start",
            "condition_type": None,
            "numeric_value": None,
            "remaining_rounds": None,
            "expires_on": "turn_start",
            "expires_at_participant_id": "e1",
            "source_participant_id": "e1",
            "created_at": "2026-01-01T00:00:00+00:00",
        }]
        # p1 (attacker, index 0) has advantage_on_attacks
        self.state.participants[0]["active_effects"] = [{
            "id": "eff-adv",
            "kind": "advantage_on_attacks",
            "duration_type": "until_turn_start",
            "condition_type": None,
            "numeric_value": None,
            "remaining_rounds": None,
            "expires_on": "turn_start",
            "expires_at_participant_id": "p1",
            "source_participant_id": "e1",
            "created_at": "2026-01-01T00:00:00+00:00",
        }]
        self.state.current_turn_index = 0  # p1's turn

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(), 10, 14, 12, 2, 0),  # attacker (p1)
                (MagicMock(), 15, 10, 10, 2, 0),  # defender (e1)
            ]):
                with patch("random.randint", return_value=10):
                    result = await CombatService.attack(
                        self.db, "session-123",
                        CombatAttackRequest(target_ref_id="enemy-123"),
                        "user-1", False,
                    )

        roll_result = result.get("roll_result")
        self.assertIsNotNone(roll_result)
        self.assertEqual(roll_result.advantage_mode, "normal")

    # ---- must be active phase ----

    async def test_standard_action_requires_active_phase(self):
        self.state.phase = CombatPhase.initiative

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError):
                await CombatService.standard_action(
                    self.db, "session-123",
                    CombatStandardActionRequest(action="dash"),
                    "user-1", False,
                )
