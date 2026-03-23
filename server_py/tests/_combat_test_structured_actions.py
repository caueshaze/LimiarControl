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
    CombatResolveDamageRequest,
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
from app.schemas.roll import RollActorStats



class CombatStructuredActionTestsMixin:
    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_gm_can_execute_structured_weapon_action(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1

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
                    return_value=(SessionState(id="state-1", session_id="session-123", player_user_id="player-123", state_json={}), 12, 10, 10, 2, 0),
                ):
                    with patch("random.randint", return_value=18):
                        result = await CombatService.entity_action(
                            self.db,
                            "session-123",
                            CombatEntityActionRequest(
                                actor_participant_id="e1",
                                target_ref_id="player-123",
                                combat_action_id="claw",
                            ),
                            "gm-user",
                            True,
                        )

        self.assertTrue(result["is_hit"])
        self.assertEqual(result["damage"], 0)
        self.assertTrue(result["damage_roll_required"])
        self.assertIsNotNone(result["pending_attack_id"])
        self.assertEqual(self.state.current_turn_index, 1)

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_structured_spell_attack_can_use_creature_spell_attack_bonus(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_combat_action_for_entity",
                return_value=(
                    SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                    CampaignEntity(
                        id="ce-1",
                        campaign_id="camp-1",
                        name="Goblin Shaman",
                        spellcasting={"attackBonus": 7},
                    ),
                    CombatAction(
                        id="shadow_bolt",
                        name="Shadow Bolt",
                        kind="spell_attack",
                        spellCanonicalKey="witch_bolt",
                        damageDice="1d8",
                        damageType="force",
                    ),
                ),
            ):
                with patch("app.services.combat.CombatService._get_campaign_system_for_session", return_value="DND5E"):
                    with patch(
                        "app.services.combat_service.entity_actions.get_base_spell_by_canonical_key",
                        return_value=MagicMock(damage_type="force", saving_throw=None),
                    ):
                        with patch(
                            "app.services.combat.CombatService._get_stats",
                            return_value=(SessionState(id="state-1", session_id="session-123", player_user_id="player-123", state_json={}), 12, 10, 10, 2, 0),
                        ):
                            with patch("random.randint", return_value=15):
                                result = await CombatService.entity_action(
                                    self.db,
                                    "session-123",
                                    CombatEntityActionRequest(
                                        actor_participant_id="e1",
                                        target_ref_id="player-123",
                                        combat_action_id="shadow_bolt",
                                    ),
                                    "gm-user",
                                    True,
                                )

        self.assertTrue(result["is_hit"])
        self.assertEqual(result["roll"], 22)
        self.assertEqual(result["damage"], 0)
        self.assertTrue(result["damage_roll_required"])
        self.assertIsNotNone(result["pending_attack_id"])

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_structured_weapon_action_accepts_manual_roll(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_combat_action_for_entity",
                return_value=(
                    SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                    MagicMock(),
                    CombatAction(
                        id="shortbow",
                        name="Ataque a distancia com Arco curto",
                        kind="weapon_attack",
                        toHitBonus=4,
                        damageDice="1d6",
                        damageBonus=1,
                        damageType="piercing",
                        isMelee=False,
                    ),
                ),
            ):
                with patch(
                    "app.services.combat.CombatService._get_stats",
                    return_value=(SessionState(id="state-1", session_id="session-123", player_user_id="player-123", state_json={}), 13, 10, 10, 2, 0),
                ):
                    result = await CombatService.entity_action(
                        self.db,
                        "session-123",
                        CombatEntityActionRequest(
                            actor_participant_id="e1",
                            target_ref_id="player-123",
                            combat_action_id="shortbow",
                            roll_source="manual",
                            manual_roll=17,
                        ),
                        "gm-user",
                        True,
                    )

        self.assertTrue(result["is_hit"])
        self.assertEqual(result["roll"], 21)
        self.assertEqual(result["damage"], 0)
        self.assertTrue(result["damage_roll_required"])
        self.assertIsNotNone(result["pending_attack_id"])
        self.assertEqual(result["roll_result"].roll_source, "manual")
        self.assertEqual(result["roll_result"].selected_roll, 17)
        self.assertEqual(result["target_ac"], 13)

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_structured_weapon_action_damage_accepts_manual_rolls(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1
        self.state.participants[1]["pending_attack"] = {
            "id": "pending-entity-1",
            "type": "entity_attack",
            "action_name": "Ataque a distancia com Arco curto",
            "action_kind": "weapon_attack",
            "target_ref_id": "player-123",
            "target_kind": "player",
            "target_display_name": "Hero",
            "target_ac": 13,
            "damage_dice": "1d6",
            "damage_bonus": 1,
            "damage_type": "piercing",
            "attack_bonus": 4,
            "is_critical": False,
            "roll": 21,
            "roll_result": {
                "event_id": "roll-2",
                "roll_type": "attack",
                "actor_kind": "session_entity",
                "actor_ref_id": "enemy-123",
                "actor_display_name": "Goblin",
                "rolls": [17],
                "selected_roll": 17,
                "advantage_mode": "normal",
                "modifier_used": 4,
                "override_used": True,
                "formula": "d20 + 4",
                "total": 21,
                "target_ac": 13,
                "success": True,
                "is_gm_roll": True,
                "roll_source": "manual",
                "timestamp": "2026-03-22T00:00:00Z",
            },
        }

        target_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={},
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._apply_damage_to_target",
                return_value=(5, "", 8),
            ) as mock_apply_damage:
                with patch(
                    "app.services.combat.CombatService._get_stats",
                    return_value=(target_state, 13, 10, 10, 2, 0),
                ):
                    result = await CombatService.entity_action_damage(
                        self.db,
                        "session-123",
                        CombatResolveDamageRequest(
                            actor_participant_id="e1",
                            pending_attack_id="pending-entity-1",
                            roll_source="manual",
                            manual_rolls=[2],
                        ),
                        "gm-user",
                        True,
                    )

        self.assertEqual(result["damage"], 3)
        self.assertEqual(result["damage_rolls"], [2])
        self.assertEqual(result["base_damage"], 2)
        self.assertEqual(result["damage_roll_source"], "manual")
        self.assertNotIn("pending_attack", self.state.participants[1])
        mock_apply_damage.assert_called_once_with(
            self.db,
            "player-123",
            "player",
            3,
            False,
            self.state,
        )

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_gm_can_execute_structured_saving_throw_action(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_combat_action_for_entity",
                return_value=(
                    SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                    MagicMock(),
                    CombatAction(
                        id="fire_breath",
                        name="Fire Breath",
                        kind="saving_throw",
                        spellCanonicalKey="burning_hands",
                        saveAbility="dexterity",
                        saveDc=13,
                        damageDice="2d6",
                        damageBonus=1,
                        damageType="fire",
                    ),
                ),
            ):
                with patch(
                    "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                    return_value=MagicMock(damage_type="fire", saving_throw="dexterity"),
                ):
                    with patch(
                        "app.services.combat.CombatService._build_roll_actor_stats_for_save",
                        return_value=RollActorStats(
                            display_name="Hero",
                            abilities={"dexterity": 10},
                            actor_kind="player",
                            actor_ref_id="player-123",
                        ),
                    ):
                        with patch("random.randint", return_value=5):
                            with patch("app.services.combat_service.npc_actions._roll_dice_expression", return_value=7):
                                with patch(
                                    "app.services.combat.CombatService._apply_damage_to_target",
                                    return_value=(1, "", 9),
                                ):
                                    result = await CombatService.entity_action(
                                        self.db,
                                        "session-123",
                                        CombatEntityActionRequest(
                                            actor_participant_id="e1",
                                            target_ref_id="player-123",
                                            combat_action_id="fire_breath",
                                        ),
                                        "gm-user",
                                        True,
                                    )

        self.assertFalse(result["is_saved"])
        self.assertEqual(result["damage"], 8)
        self.assertEqual(result["save_dc"], 13)
        self.assertIsNotNone(result["roll_result"])
        self.assertEqual(result["roll_result"].roll_type, "save")

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_structured_saving_throw_can_use_creature_spell_save_dc(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_combat_action_for_entity",
                return_value=(
                    SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                    CampaignEntity(
                        id="ce-1",
                        campaign_id="camp-1",
                        name="Goblin Shaman",
                        spellcasting={"saveDc": 14},
                    ),
                    CombatAction(
                        id="mind_shriek",
                        name="Mind Shriek",
                        kind="saving_throw",
                        spellCanonicalKey="dissonant_whispers",
                        saveAbility="wisdom",
                        damageDice="2d6",
                        damageType="psychic",
                    ),
                ),
            ):
                with patch(
                    "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                    return_value=MagicMock(damage_type="psychic", saving_throw="wisdom"),
                ):
                    with patch(
                        "app.services.combat.CombatService._build_roll_actor_stats_for_save",
                        return_value=RollActorStats(
                            display_name="Hero",
                            abilities={"wisdom": 10},
                            actor_kind="player",
                            actor_ref_id="player-123",
                        ),
                    ):
                        with patch("random.randint", return_value=8):
                            with patch("app.services.combat_service.npc_actions._roll_dice_expression", return_value=7):
                                with patch(
                                    "app.services.combat.CombatService._apply_damage_to_target",
                                    return_value=(2, "", 9),
                                ):
                                    result = await CombatService.entity_action(
                                        self.db,
                                        "session-123",
                                        CombatEntityActionRequest(
                                            actor_participant_id="e1",
                                            target_ref_id="player-123",
                                            combat_action_id="mind_shriek",
                                        ),
                                        "gm-user",
                                        True,
                                    )

        self.assertFalse(result["is_saved"])
        self.assertEqual(result["save_dc"], 14)
        self.assertEqual(result["damage"], 7)
        self.assertEqual(result["roll_result"].roll_type, "save")

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_gm_can_execute_structured_heal_action(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_player_state_update,
        mock_emit_entity_hp_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_combat_action_for_entity",
                return_value=(
                    SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1", current_hp=7),
                    MagicMock(),
                    CombatAction(
                        id="dark_mend",
                        name="Dark Mend",
                        kind="heal",
                        healDice="1d8",
                        healBonus=2,
                    ),
                ),
            ):
                with patch("app.services.combat_service.npc_actions._roll_dice_expression", return_value=5):
                    with patch(
                        "app.services.combat.CombatService._apply_healing_to_target",
                        return_value=(7, "", 0),
                    ):
                        result = await CombatService.entity_action(
                            self.db,
                            "session-123",
                            CombatEntityActionRequest(
                                actor_participant_id="e1",
                                target_ref_id="enemy-123",
                                combat_action_id="dark_mend",
                            ),
                            "gm-user",
                            True,
                        )

        self.assertEqual(result["healing"], 7)
        self.assertEqual(result["action_kind"], "heal")
