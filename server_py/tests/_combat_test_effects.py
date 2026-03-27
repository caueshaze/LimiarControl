import unittest
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.schemas.combat import (
    CombatApplyEffectRequest,
    CombatEntityActionRequest,
    CombatRemoveEffectRequest,
)
from app.schemas.campaign_entity import CombatAction
from app.services.combat import CombatService, CombatServiceError


class CombatEffectsTestsMixin:

    # ---- apply / remove ----

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_apply_effect_to_participant(self, mock_emit_log, mock_emit_state):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            result = await CombatService.apply_effect(
                self.db,
                "session-123",
                CombatApplyEffectRequest(
                    target_participant_id="p1",
                    kind="condition",
                    condition_type="poisoned",
                    duration_type="manual",
                ),
            )

        effects = result.participants[0].get("active_effects", [])
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["kind"], "condition")
        self.assertEqual(effects[0]["condition_type"], "poisoned")
        self.assertEqual(effects[0]["duration_type"], "manual")
        self.assertIsNone(effects[0]["expires_on"])
        mock_emit_state.assert_called_once()
        mock_emit_log.assert_called_once()

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_apply_effect_validates_condition_type(self, mock_emit_log, mock_emit_state):
        self.state.phase = CombatPhase.active

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError):
                await CombatService.apply_effect(
                    self.db,
                    "session-123",
                    CombatApplyEffectRequest(
                        target_participant_id="p1",
                        kind="condition",
                        duration_type="manual",
                    ),
                )

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_apply_effect_validates_numeric_value(self, mock_emit_log, mock_emit_state):
        self.state.phase = CombatPhase.active

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError):
                await CombatService.apply_effect(
                    self.db,
                    "session-123",
                    CombatApplyEffectRequest(
                        target_participant_id="p1",
                        kind="temp_ac_bonus",
                        duration_type="manual",
                    ),
                )

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_remove_effect_from_participant(self, mock_emit_log, mock_emit_state):
        self.state.phase = CombatPhase.active
        self.state.participants[0]["active_effects"] = [
            {"id": "eff-1", "kind": "condition", "condition_type": "prone", "duration_type": "manual"},
        ]

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            result = await CombatService.remove_effect(
                self.db,
                "session-123",
                CombatRemoveEffectRequest(
                    target_participant_id="p1",
                    effect_id="eff-1",
                ),
            )

        effects = result.participants[0].get("active_effects", [])
        self.assertEqual(len(effects), 0)

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_remove_nonexistent_effect(self, mock_emit_log, mock_emit_state):
        self.state.phase = CombatPhase.active
        self.state.participants[0]["active_effects"] = []

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError):
                await CombatService.remove_effect(
                    self.db,
                    "session-123",
                    CombatRemoveEffectRequest(
                        target_participant_id="p1",
                        effect_id="nonexistent",
                    ),
                )

    # ---- expiration ----

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_expire_effect_on_turn_end(self, mock_emit_log, mock_emit_state):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.participants[0]["initiative"] = 20
        self.state.participants[1]["initiative"] = 10
        self.state.participants[0]["active_effects"] = [
            {
                "id": "eff-end",
                "kind": "condition",
                "condition_type": "frightened",
                "duration_type": "until_turn_end",
                "expires_on": "turn_end",
                "expires_at_participant_id": "p1",
            },
        ]

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            await CombatService.next_turn(self.db, "session-123", "user-1", False)

        effects = self.state.participants[0].get("active_effects", [])
        self.assertEqual(len(effects), 0)

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_expire_effect_on_turn_start(self, mock_emit_log, mock_emit_state):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.participants[0]["initiative"] = 20
        self.state.participants[1]["initiative"] = 10
        # Effect on p1 that expires at start of e1's turn (i.e. when e1 begins)
        self.state.participants[0]["active_effects"] = [
            {
                "id": "eff-start",
                "kind": "temp_ac_bonus",
                "numeric_value": 2,
                "duration_type": "until_turn_start",
                "expires_on": "turn_start",
                "expires_at_participant_id": "e1",
            },
        ]

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            await CombatService.next_turn(self.db, "session-123", "user-1", False)

        # After advancing from p1 → e1, turn_start effects for e1 should be expired
        effects = self.state.participants[0].get("active_effects", [])
        self.assertEqual(len(effects), 0)

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_decrement_rounds_effect(self, mock_emit_log, mock_emit_state):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.participants[0]["initiative"] = 20
        self.state.participants[1]["initiative"] = 10
        # Effect on e1, expires at start of e1's turn, 2 rounds remaining
        self.state.participants[1]["active_effects"] = [
            {
                "id": "eff-rounds",
                "kind": "condition",
                "condition_type": "restrained",
                "duration_type": "rounds",
                "remaining_rounds": 2,
                "expires_on": "turn_start",
                "expires_at_participant_id": "e1",
            },
        ]

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            # Advance p1 → e1: triggers turn_start for e1, should decrement to 1
            await CombatService.next_turn(self.db, "session-123", "user-1", False)

        effects = self.state.participants[1].get("active_effects", [])
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["remaining_rounds"], 1)

        # Now advance e1 → p1 → e1 (full round) to expire it
        self.state.current_turn_index = 1
        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            # e1 → p1
            await CombatService.next_turn(self.db, "session-123", "gm-user", True)

        self.state.current_turn_index = 0
        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            # p1 → e1: triggers turn_start for e1 again, remaining=1 → expire
            await CombatService.next_turn(self.db, "session-123", "user-1", False)

        effects = self.state.participants[1].get("active_effects", [])
        self.assertEqual(len(effects), 0)

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_manual_effect_does_not_expire(self, mock_emit_log, mock_emit_state):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.participants[0]["initiative"] = 20
        self.state.participants[1]["initiative"] = 10
        self.state.participants[0]["active_effects"] = [
            {
                "id": "eff-manual",
                "kind": "condition",
                "condition_type": "prone",
                "duration_type": "manual",
                "expires_on": None,
                "expires_at_participant_id": None,
            },
        ]

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            await CombatService.next_turn(self.db, "session-123", "user-1", False)

        effects = self.state.participants[0].get("active_effects", [])
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["id"], "eff-manual")

    # ---- mechanical impact ----

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_temp_ac_bonus_modifies_ac(self, mock_emit_log, mock_emit_state):
        """temp_ac_bonus should increase effective AC used in attack resolution."""
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1  # NPC attacks player
        # Player target has +2 AC bonus
        self.state.participants[0]["active_effects"] = [
            {"id": "eff-ac", "kind": "temp_ac_bonus", "numeric_value": 2, "duration_type": "manual"},
        ]

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_combat_action_for_entity",
                return_value=(
                    SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                    MagicMock(),
                    CombatAction(
                        id="claw", name="Claw", kind="weapon_attack",
                        toHitBonus=5, damageDice="1d6", damageBonus=2, damageType="slashing", isMelee=True,
                    ),
                ),
            ):
                with patch(
                    "app.services.combat.CombatService._get_stats",
                    return_value=(SessionState(id="s1", session_id="session-123", player_user_id="player-123", state_json={}), 15, 10, 10, 2, 0),
                ):
                    # Roll 12 + 5 = 17 vs AC 15+2=17 → hit (equal to AC)
                    with patch("random.randint", return_value=12):
                        result = await CombatService.entity_action(
                            self.db, "session-123",
                            CombatEntityActionRequest(
                                actor_participant_id="e1",
                                target_ref_id="player-123",
                                combat_action_id="claw",
                            ),
                            "gm-user", True,
                        )

        # 12 + 5 = 17, AC is 15 + 2 = 17 → should hit
        self.assertTrue(result["is_hit"])
        self.assertEqual(result["target_ac"], 17)

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_attack_bonus_modifies_roll(self, mock_emit_log, mock_emit_state):
        """attack_bonus effect should increase the to-hit bonus for the attacker."""
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1
        # NPC attacker has +3 attack bonus from effect
        self.state.participants[1]["active_effects"] = [
            {"id": "eff-atk", "kind": "attack_bonus", "numeric_value": 3, "duration_type": "manual"},
        ]

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_combat_action_for_entity",
                return_value=(
                    SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                    MagicMock(),
                    CombatAction(
                        id="claw", name="Claw", kind="weapon_attack",
                        toHitBonus=2, damageDice="1d6", damageBonus=1, damageType="slashing", isMelee=True,
                    ),
                ),
            ):
                with patch(
                    "app.services.combat.CombatService._get_stats",
                    return_value=(SessionState(id="s1", session_id="session-123", player_user_id="player-123", state_json={}), 15, 10, 10, 2, 0),
                ):
                    # Roll 10 + 2(base) + 3(effect) = 15 vs AC 15 → hit
                    with patch("random.randint", return_value=10):
                        result = await CombatService.entity_action(
                            self.db, "session-123",
                            CombatEntityActionRequest(
                                actor_participant_id="e1",
                                target_ref_id="player-123",
                                combat_action_id="claw",
                            ),
                            "gm-user", True,
                        )

        # 10 + 2 + 3 = 15 vs AC 15 → hit
        self.assertTrue(result["is_hit"])
        self.assertEqual(result["attack_bonus"], 5)  # 2 base + 3 effect

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_advantage_on_attacks_effect(self, mock_emit_log, mock_emit_state):
        """advantage_on_attacks effect should force advantage mode."""
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1
        self.state.participants[1]["active_effects"] = [
            {"id": "eff-adv", "kind": "advantage_on_attacks", "duration_type": "manual"},
        ]

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_combat_action_for_entity",
                return_value=(
                    SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                    MagicMock(),
                    CombatAction(
                        id="claw", name="Claw", kind="weapon_attack",
                        toHitBonus=5, damageDice="1d6", damageBonus=2, damageType="slashing", isMelee=True,
                    ),
                ),
            ):
                with patch(
                    "app.services.combat.CombatService._get_stats",
                    return_value=(SessionState(id="s1", session_id="session-123", player_user_id="player-123", state_json={}), 12, 10, 10, 2, 0),
                ):
                    with patch("random.randint", side_effect=[5, 18]) as mock_rand:
                        result = await CombatService.entity_action(
                            self.db, "session-123",
                            CombatEntityActionRequest(
                                actor_participant_id="e1",
                                target_ref_id="player-123",
                                combat_action_id="claw",
                            ),
                            "gm-user", True,
                        )

        # With advantage, roll_resolution should roll 2 dice
        roll_result = result.get("roll_result")
        if roll_result:
            rr = roll_result if isinstance(roll_result, dict) else roll_result.model_dump()
            # Advantage means two rolls were made
            self.assertEqual(len(rr.get("rolls", [])), 2)

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_effects_visible_in_state(self, mock_emit_log, mock_emit_state):
        """Applied effects should be visible in the combat state."""
        self.state.phase = CombatPhase.active

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            result = await CombatService.apply_effect(
                self.db,
                "session-123",
                CombatApplyEffectRequest(
                    target_participant_id="e1",
                    kind="advantage_on_attacks",
                    duration_type="rounds",
                    remaining_rounds=3,
                ),
            )

        effects = result.participants[1].get("active_effects", [])
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["kind"], "advantage_on_attacks")
        self.assertEqual(effects[0]["remaining_rounds"], 3)
        self.assertEqual(effects[0]["expires_on"], "turn_start")

        # Also verify get_all_effects
        all_effects = CombatService.get_all_effects(result)
        self.assertEqual(len(all_effects), 1)
        self.assertEqual(all_effects[0]["target_participant_id"], "e1")
        self.assertEqual(all_effects[0]["target_display_name"], "Goblin")
