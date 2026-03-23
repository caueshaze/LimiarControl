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
