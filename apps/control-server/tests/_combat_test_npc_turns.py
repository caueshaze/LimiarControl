import unittest
from unittest.mock import MagicMock, patch

from app.models.campaign_entity import CampaignEntity
from app.models.combat import CombatPhase, CombatState
from app.models.item import Item, ItemType
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.schemas.campaign_entity import CombatAction
from app.schemas.combat import (
    CombatApplyDamageRequest,
    CombatApplyHealingRequest,
    CombatAttackRequest,
    CombatEntityActionRequest,
    CombatParticipant,
    CombatSetInitiativeParticipant,
    CombatSetInitiativeRequest,
    CombatStartRequest,
)
from app.services.combat import (
    CombatService,
    CombatServiceError,
    _parse_dice,
    _roll_dice_expression,
)
from app.services.combat_service.combat_targeting import TargetingResult, SpatialMetadata



class CombatNpcTurnTestsMixin:
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_gm_can_execute_structured_attack_with_active_npc(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1
        self.state.participants.append({
            "id": "e2",
            "ref_id": "enemy-456",
            "kind": "session_entity",
            "display_name": "Wolf",
            "initiative": 8,
            "status": "active",
            "team": "enemies",
            "visible": True,
            "actor_user_id": None,
        })

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_combat_action_for_entity",
                return_value=(
                    SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                    MagicMock(),
                    CombatAction(
                        id="claw",
                        name="Claw",
                        kind="weapon_attack",
                        toHitBonus=5,
                        damageDice="1d6",
                        damageBonus=2,
                        damageType="slashing",
                        isMelee=True,
                    ),
                ),
            ):
                with patch(
                    "app.services.combat.CombatService._get_stats",
                    return_value=(SessionEntity(id="enemy-456", session_id="session-123", campaign_entity_id="ce-2", current_hp=5), 10, 10, 10, 2, 0),
                ):
                    res = await CombatService.entity_action(
                        self.db,
                        "session-123",
                        CombatEntityActionRequest(
                            actor_participant_id="e1",
                            target_ref_id="enemy-456",
                            combat_action_id="claw",
                            roll_source="manual",
                            manual_roll=17,
                        ),
                        "gm-user",
                        True,
                    )

        self.assertTrue(res["is_hit"])
        self.assertTrue(res["damage_roll_required"])
        self.assertIsNotNone(res["pending_attack_id"])
        self.assertEqual(self.state.current_turn_index, 1)

    async def test_player_cannot_act_for_npc(self):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.attack(
                    self.db,
                    "session-123",
                    CombatAttackRequest(
                        actor_participant_id="e1",
                        target_ref_id="player-123",
                        weapon_item_id="unarmed",
                    ),
                    "user-1",
                    False,
                )

        self.assertEqual(ctx.exception.status_code, 400)

    async def test_player_cannot_execute_structured_action_for_npc(self):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.entity_action(
                    self.db,
                    "session-123",
                    CombatEntityActionRequest(
                        actor_participant_id="e1",
                        target_ref_id="player-123",
                        combat_action_id="claw",
                    ),
                    "user-1",
                    False,
                )

        self.assertEqual(ctx.exception.status_code, 400)

    # ---------------------------------------------------------------------------
    # Phase 9: Unified NPC Combat Pipeline Tests
    # ---------------------------------------------------------------------------

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_npc_attack_blocked_by_no_line_of_sight(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update):
        """Test that NPC attacks are blocked when there is no line of sight."""
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1
        self.state.participants.append({
            "id": "e2",
            "ref_id": "enemy-456",
            "kind": "session_entity",
            "display_name": "Wolf",
            "initiative": 8,
            "status": "active",
            "team": "enemies",
            "visible": True,
            "actor_user_id": None,
        })

        # Mock targeting service to reject due to no line of sight
        mock_targeting_service = MagicMock()
        mock_targeting_service.validate.return_value = TargetingResult.invalid("Target is blocked by line of sight.")

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat_service.npc_actions.get_combat_targeting_service", return_value=mock_targeting_service):
                with patch(
                    "app.services.combat.CombatService._get_combat_action_for_entity",
                    return_value=(
                        SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                        MagicMock(),
                        CombatAction(
                            id="ranged_attack",
                            name="Ranged Attack",
                            kind="weapon_attack",
                            toHitBonus=5,
                            damageDice="1d8",
                            damageBonus=2,
                            damageType="piercing",
                            isMelee=False,
                            rangeType="ranged",
                            rangeMeters=30,
                        ),
                    ),
                ):
                    with self.assertRaises(CombatServiceError) as ctx:
                        await CombatService.entity_action(
                            self.db,
                            "session-123",
                            CombatEntityActionRequest(
                                actor_participant_id="e1",
                                target_ref_id="enemy-456",
                                combat_action_id="ranged_attack",
                                roll_source="manual",
                                manual_roll=17,
                            ),
                            "gm-user",
                            True,
                        )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("line of sight", str(ctx.exception.detail).lower())

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_npc_attack_applies_half_cover(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update):
        """Test that NPC attacks apply half cover bonus to target AC."""
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1
        self.state.participants.append({
            "id": "e2",
            "ref_id": "enemy-456",
            "kind": "session_entity",
            "display_name": "Wolf",
            "initiative": 8,
            "status": "active",
            "team": "enemies",
            "visible": True,
            "actor_user_id": None,
        })

        # Mock targeting service to return half cover
        mock_targeting_service = MagicMock()
        mock_targeting_service.validate.return_value = TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="enemy-456",
            affected_target_ref_ids=["enemy-456"],
            target_kind="session_entity",
            spatial_metadata=SpatialMetadata(
                targeting_authority="limiar_map",
                cover="half",
            ),
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat_service.npc_actions.get_combat_targeting_service", return_value=mock_targeting_service):
                with patch(
                    "app.services.combat.CombatService._get_combat_action_for_entity",
                    return_value=(
                        SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                        MagicMock(),
                        CombatAction(
                            id="ranged_attack",
                            name="Ranged Attack",
                            kind="weapon_attack",
                            toHitBonus=5,
                            damageDice="1d8",
                            damageBonus=2,
                            damageType="piercing",
                            isMelee=False,
                            rangeType="ranged",
                            rangeMeters=30,
                        ),
                    ),
                ):
                    with patch(
                        "app.services.combat.CombatService._get_stats",
                        return_value=(SessionEntity(id="enemy-456", session_id="session-123", campaign_entity_id="ce-2", current_hp=5), 10, 10, 10, 2, 0),
                    ):
                        res = await CombatService.entity_action(
                            self.db,
                            "session-123",
                            CombatEntityActionRequest(
                                actor_participant_id="e1",
                                target_ref_id="enemy-456",
                                combat_action_id="ranged_attack",
                                roll_source="manual",
                                manual_roll=17,
                            ),
                            "gm-user",
                            True,
                        )

        # Verify the attack hit (roll 17 vs AC 12 = base AC 10 + half cover 2)
        self.assertTrue(res["is_hit"])
        # Verify cover was mentioned in the log
        mock_emit_log.assert_called()
        log_args = mock_emit_log.call_args.args
        log_message = log_args[1]["message"] if len(log_args) > 1 else mock_emit_log.call_args.kwargs.get("message", "")
        self.assertIn("Half Cover", log_message)

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_npc_attack_applies_three_quarters_cover(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update):
        """Test that NPC attacks apply three-quarters cover bonus to target AC."""
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1
        self.state.participants.append({
            "id": "e2",
            "ref_id": "enemy-456",
            "kind": "session_entity",
            "display_name": "Wolf",
            "initiative": 8,
            "status": "active",
            "team": "enemies",
            "visible": True,
            "actor_user_id": None,
        })

        # Mock targeting service to return three-quarters cover
        mock_targeting_service = MagicMock()
        mock_targeting_service.validate.return_value = TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="enemy-456",
            affected_target_ref_ids=["enemy-456"],
            target_kind="session_entity",
            spatial_metadata=SpatialMetadata(
                targeting_authority="limiar_map",
                cover="threeQuarters",
            ),
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat_service.npc_actions.get_combat_targeting_service", return_value=mock_targeting_service):
                with patch(
                    "app.services.combat.CombatService._get_combat_action_for_entity",
                    return_value=(
                        SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                        MagicMock(),
                        CombatAction(
                            id="ranged_attack",
                            name="Ranged Attack",
                            kind="weapon_attack",
                            toHitBonus=5,
                            damageDice="1d8",
                            damageBonus=2,
                            damageType="piercing",
                            isMelee=False,
                            rangeType="ranged",
                            rangeMeters=30,
                        ),
                    ),
                ):
                    with patch(
                        "app.services.combat.CombatService._get_stats",
                        return_value=(SessionEntity(id="enemy-456", session_id="session-123", campaign_entity_id="ce-2", current_hp=5), 10, 10, 10, 2, 0),
                    ):
                        res = await CombatService.entity_action(
                            self.db,
                            "session-123",
                            CombatEntityActionRequest(
                                actor_participant_id="e1",
                                target_ref_id="enemy-456",
                                combat_action_id="ranged_attack",
                                roll_source="manual",
                                manual_roll=17,
                            ),
                            "gm-user",
                            True,
                        )

        # Verify the attack hit (roll 17 vs AC 15 = base AC 10 + three-quarters cover 5)
        self.assertTrue(res["is_hit"])
        # Verify cover was mentioned in the log
        mock_emit_log.assert_called()
        log_args = mock_emit_log.call_args.args
        log_message = log_args[1]["message"] if len(log_args) > 1 else mock_emit_log.call_args.kwargs.get("message", "")
        self.assertIn("Three-Quarters Cover", log_message)

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_npc_saving_throw_applies_cover_to_dc(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update):
        """Test that NPC saving throw actions apply cover modifier to DC."""
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1
        self.state.participants.append({
            "id": "e2",
            "ref_id": "enemy-456",
            "kind": "session_entity",
            "display_name": "Wolf",
            "initiative": 8,
            "status": "active",
            "team": "enemies",
            "visible": True,
            "actor_user_id": None,
        })

        # Mock targeting service to return half cover
        mock_targeting_service = MagicMock()
        mock_targeting_service.validate.return_value = TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="enemy-456",
            affected_target_ref_ids=["enemy-456"],
            target_kind="session_entity",
            spatial_metadata=SpatialMetadata(
                targeting_authority="limiar_map",
                cover="half",
            ),
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat_service.npc_actions.get_combat_targeting_service", return_value=mock_targeting_service):
                with patch(
                    "app.services.combat.CombatService._get_combat_action_for_entity",
                    return_value=(
                        SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                        MagicMock(),
                        CombatAction(
                            id="fire_breath",
                            name="Fire Breath",
                            kind="saving_throw",
                            spellCanonicalKey="fire_breath",
                            saveAbility="dexterity",
                            saveDc=15,
                            damageDice="2d6",
                            damageBonus=0,
                            damageType="fire",
                        ),
                    ),
                ):
                    with patch(
                        "app.services.combat.CombatService._get_stats",
                        return_value=(SessionEntity(id="enemy-456", session_id="session-123", campaign_entity_id="ce-2", current_hp=5), 10, 10, 10, 2, 0),
                    ):
                        res = await CombatService.entity_action(
                            self.db,
                            "session-123",
                            CombatEntityActionRequest(
                                actor_participant_id="e1",
                                target_ref_id="enemy-456",
                                combat_action_id="fire_breath",
                                roll_source="manual",
                                manual_roll=14,
                            ),
                            "gm-user",
                            True,
                        )

        # Verify the save succeeded (roll 14 vs DC 13 = base DC 15 - half cover 2)
        self.assertTrue(res["is_saved"], f"Save failed: roll={res.get('save_roll')}, save_dc={res.get('save_dc')}, is_saved={res.get('is_saved')}")

        # Verify cover was mentioned in the log
        mock_emit_log.assert_called()
        log_args = mock_emit_log.call_args.args
        log_message = log_args[1]["message"] if len(log_args) > 1 else mock_emit_log.call_args.kwargs.get("message", "")
        self.assertIn("Half Cover", log_message)

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_npc_spell_blocked_by_no_line_of_effect(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update):
        """Test that NPC spell attacks are blocked when there is no line of effect."""
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1
        self.state.participants.append({
            "id": "e2",
            "ref_id": "enemy-456",
            "kind": "session_entity",
            "display_name": "Wolf",
            "initiative": 8,
            "status": "active",
            "team": "enemies",
            "visible": True,
            "actor_user_id": None,
        })

        # Mock targeting service to reject due to no line of effect
        mock_targeting_service = MagicMock()
        mock_targeting_service.validate.return_value = TargetingResult.invalid("Target is blocked by line of effect.")

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat_service.npc_actions.get_combat_targeting_service", return_value=mock_targeting_service):
                with patch(
                    "app.services.combat.CombatService._get_combat_action_for_entity",
                    return_value=(
                        SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                        MagicMock(),
                        CombatAction(
                            id="firebolt",
                            name="Firebolt",
                            kind="spell_attack",
                            spellAttackBonus=7,
                            damageDice="2d10",
                            damageBonus=0,
                            damageType="fire",
                            spellCanonicalKey="firebolt",
                            targetMode="ranged",
                            spellMode="spell_attack",
                            rangeMeters=36,
                            requiresTargetSight=True,
                            requiresTargetEffect=True,
                        ),
                    ),
                ):
                    with self.assertRaises(CombatServiceError) as ctx:
                        await CombatService.entity_action(
                            self.db,
                            "session-123",
                            CombatEntityActionRequest(
                                actor_participant_id="e1",
                                target_ref_id="enemy-456",
                                combat_action_id="firebolt",
                                roll_source="manual",
                                manual_roll=17,
                            ),
                            "gm-user",
                            True,
                        )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("line of effect", str(ctx.exception.detail).lower())

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_npc_attack_consistent_error_types(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update):
        """Test that NPC actions return the same error types as player actions."""
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1
        self.state.participants.append({
            "id": "e2",
            "ref_id": "enemy-456",
            "kind": "session_entity",
            "display_name": "Wolf",
            "initiative": 8,
            "status": "active",
            "team": "enemies",
            "visible": True,
            "actor_user_id": None,
        })

        # Test various error types
        error_cases = [
            ("out_of_range", "out_of_range"),
            ("no_line_of_sight", "line_of_sight"),
            ("no_line_of_effect", "line_of_effect"),
            ("full_cover", "full_cover"),
        ]

        for reason, expected_text in error_cases:
            # Reset actor turn resources for each test case
            for p in self.state.participants:
                if p.get("id") == "e1":
                    p["turn_resources"] = {
                        "action_used": False,
                        "bonus_action_used": False,
                        "reaction_used": False,
                        "colossus_slayer_used": False,
                    }

            mock_targeting_service = MagicMock()
            mock_targeting_service.validate.return_value = TargetingResult.invalid(f"Targeting failed: {reason}")

            with patch("app.services.combat.CombatService.get_state", return_value=self.state):
                with patch("app.services.combat_service.npc_actions.get_combat_targeting_service", return_value=mock_targeting_service):
                    with patch(
                        "app.services.combat.CombatService._get_combat_action_for_entity",
                        return_value=(
                            SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                            MagicMock(),
                            CombatAction(
                                id="ranged_attack",
                                name="Ranged Attack",
                                kind="weapon_attack",
                                toHitBonus=5,
                                damageDice="1d8",
                                damageBonus=2,
                                damageType="piercing",
                                isMelee=False,
                                rangeType="ranged",
                                rangeMeters=30,
                            ),
                        ),
                    ):
                        with self.assertRaises(CombatServiceError) as ctx:
                            await CombatService.entity_action(
                                self.db,
                                "session-123",
                                CombatEntityActionRequest(
                                    actor_participant_id="e1",
                                    target_ref_id="enemy-456",
                                    combat_action_id="ranged_attack",
                                    roll_source="manual",
                                    manual_roll=17,
                                ),
                                "gm-user",
                                True,
                            )

                        self.assertEqual(ctx.exception.status_code, 400)
                        self.assertIn(expected_text, str(ctx.exception.detail).lower())
