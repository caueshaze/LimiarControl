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
    CombatResolveDamageRequest,
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


class CombatStatusTestsMixin:
    def test_apply_damage_to_player_sets_downed_at_zero_hp(self):
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "currentHP": 4,
                "maxHP": 12,
                "deathSaves": {"successes": 1, "failures": 1},
            },
        )

        with patch("app.services.combat.CombatService._get_stats", return_value=(session_state, 10, 10, 10, 2, 0)):
            new_hp, _, previous_hp, concentration_check = CombatService._apply_damage_to_target(
                self.db,
                "player-123",
                "player",
                6,
                False,
                self.state,
            )

        self.assertEqual(previous_hp, 4)
        self.assertEqual(new_hp, 0)
        self.assertIsNone(concentration_check)
        self.assertEqual(session_state.state_json["currentHP"], 0)
        self.assertEqual(session_state.state_json["deathSaves"], {"successes": 0, "failures": 0})
        self.assertEqual(self.state.participants[0]["status"], "downed")

    def test_apply_healing_to_player_returns_active(self):
        self.state.participants[0]["status"] = "downed"
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "currentHP": 0,
                "maxHP": 12,
                "deathSaves": {"successes": 2, "failures": 1},
            },
        )

        with patch("app.services.combat.CombatService._get_stats", return_value=(session_state, 10, 10, 10, 2, 0)):
            new_hp, _, previous_hp = CombatService._apply_healing_to_target(
                self.db,
                "player-123",
                "player",
                5,
                self.state,
            )

        self.assertEqual(previous_hp, 0)
        self.assertEqual(new_hp, 5)
        self.assertEqual(session_state.state_json["deathSaves"], {"successes": 0, "failures": 0})
        self.assertEqual(self.state.participants[0]["status"], "active")

    def test_apply_damage_to_draconic_bloodline_player_applies_resistance_at_level_6(self):
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "class": "sorcerer",
                "subclass": "draconic_bloodline",
                "level": 6,
                "subclassConfig": {"draconicAncestry": "red"},
                "abilities": {"charisma": 18},
                "currentHP": 24,
                "maxHP": 24,
                "deathSaves": {"successes": 0, "failures": 0},
            },
        )

        with patch("app.services.combat.CombatService._get_stats", return_value=(session_state, 10, 10, 10, 2, 0)):
            new_hp, effect_msg, previous_hp, concentration_check = CombatService._apply_damage_to_target(
                self.db,
                "player-123",
                "player",
                11,
                False,
                self.state,
                damage_type="fire",
            )

        self.assertEqual(previous_hp, 24)
        self.assertEqual(new_hp, 19)
        self.assertIsNone(concentration_check)
        self.assertIn("Resistência a fire: 11 -> 5", effect_msg)

    def test_apply_damage_to_dragonborn_player_applies_racial_resistance(self):
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "race": "dragonborn",
                "raceConfig": {"draconicAncestry": "silver"},
                "currentHP": 24,
                "maxHP": 24,
                "deathSaves": {"successes": 0, "failures": 0},
            },
        )

        with patch("app.services.combat.CombatService._get_stats", return_value=(session_state, 10, 10, 10, 2, 0)):
            new_hp, effect_msg, previous_hp, concentration_check = CombatService._apply_damage_to_target(
                self.db,
                "player-123",
                "player",
                9,
                False,
                self.state,
                damage_type="cold",
            )

        self.assertEqual(previous_hp, 24)
        self.assertEqual(new_hp, 20)
        self.assertIsNone(concentration_check)
        self.assertIn("Resistência a cold: 9 -> 4", effect_msg)

    @patch("app.services.combat_service.spell_automation.resolve_saving_throw")
    @patch("app.services.combat.CombatService._build_roll_actor_stats_for_save")
    def test_apply_damage_to_concentrating_player_breaks_concentration_on_failed_save(
        self,
        mock_build_roll_stats,
        mock_resolve_saving_throw,
    ):
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "currentHP": 20,
                "maxHP": 20,
                "deathSaves": {"successes": 0, "failures": 0},
            },
        )
        self.state.participants[0]["active_effects"] = [
            {
                "id": "hm-self",
                "kind": "spell_effect",
                "source_participant_id": "p1",
                "duration_type": "manual",
                "created_at": "2026-03-28T00:00:00Z",
                "display_label": "Hunter's Mark",
                "metadata": {
                    "concentration": True,
                    "concentration_group": "conc-1",
                    "source_spell_key": "hunters_mark",
                    "marked_target_participant_id": "e1",
                },
            }
        ]
        self.state.participants[1]["active_effects"] = [
            {
                "id": "hm-target",
                "kind": "spell_effect",
                "source_participant_id": "p1",
                "duration_type": "manual",
                "created_at": "2026-03-28T00:00:00Z",
                "display_label": "Hunter's Mark",
                "metadata": {
                    "concentration": True,
                    "concentration_group": "conc-1",
                    "source_spell_key": "hunters_mark",
                    "mark_owner_participant_id": "p1",
                },
            }
        ]
        mock_resolve_saving_throw.return_value = MagicMock(total=7, success=False)

        with patch("app.services.combat.CombatService._get_stats", return_value=(session_state, 10, 10, 10, 2, 0)):
            new_hp, _, previous_hp, concentration_check = CombatService._apply_damage_to_target(
                self.db,
                "player-123",
                "player",
                8,
                False,
                self.state,
            )

        self.assertEqual(previous_hp, 20)
        self.assertEqual(new_hp, 12)
        self.assertIsNotNone(concentration_check)
        self.assertEqual(concentration_check["dc"], 10)
        self.assertFalse(concentration_check["success"])
        self.assertEqual(self.state.participants[0]["active_effects"], [])
        self.assertEqual(self.state.participants[1]["active_effects"], [])
        self.assertIn("hunters_mark", concentration_check["source_spell_keys"])
        mock_build_roll_stats.assert_called_once()

    @patch("app.services.combat_service.spell_automation.resolve_saving_throw")
    @patch("app.services.combat.CombatService._build_roll_actor_stats_for_save")
    def test_apply_damage_to_concentrating_player_keeps_concentration_on_success(
        self,
        mock_build_roll_stats,
        mock_resolve_saving_throw,
    ):
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "currentHP": 40,
                "maxHP": 40,
                "deathSaves": {"successes": 0, "failures": 0},
            },
        )
        self.state.participants[0]["active_effects"] = [
            {
                "id": "hm-self",
                "kind": "spell_effect",
                "source_participant_id": "p1",
                "duration_type": "manual",
                "created_at": "2026-03-28T00:00:00Z",
                "display_label": "Hunter's Mark",
                "metadata": {
                    "concentration": True,
                    "concentration_group": "conc-1",
                    "source_spell_key": "hunters_mark",
                    "marked_target_participant_id": "e1",
                },
            }
        ]
        mock_resolve_saving_throw.return_value = MagicMock(total=16, success=True)

        with patch("app.services.combat.CombatService._get_stats", return_value=(session_state, 10, 10, 10, 2, 0)):
            new_hp, _, previous_hp, concentration_check = CombatService._apply_damage_to_target(
                self.db,
                "player-123",
                "player",
                28,
                False,
                self.state,
            )

        self.assertEqual(previous_hp, 40)
        self.assertEqual(new_hp, 12)
        self.assertIsNotNone(concentration_check)
        self.assertEqual(concentration_check["dc"], 14)
        self.assertTrue(concentration_check["success"])
        self.assertEqual(len(self.state.participants[0]["active_effects"]), 1)
        self.assertIn("manteve a concentração", concentration_check["summary_text"])
        mock_build_roll_stats.assert_called_once()

    @patch("app.services.combat_service.spell_automation.resolve_saving_throw")
    @patch("app.services.combat.CombatService._build_roll_actor_stats_for_save")
    def test_apply_damage_to_concentrating_player_accepts_manual_concentration_roll(
        self,
        mock_build_roll_stats,
        mock_resolve_saving_throw,
    ):
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "currentHP": 20,
                "maxHP": 20,
                "deathSaves": {"successes": 0, "failures": 0},
            },
        )
        self.state.participants[0]["active_effects"] = [
            {
                "id": "hm-self",
                "kind": "spell_effect",
                "source_participant_id": "p1",
                "duration_type": "manual",
                "created_at": "2026-03-28T00:00:00Z",
                "display_label": "Hunter's Mark",
                "metadata": {
                    "concentration": True,
                    "concentration_group": "conc-1",
                    "source_spell_key": "hunters_mark",
                    "marked_target_participant_id": "e1",
                },
            }
        ]
        mock_resolve_saving_throw.return_value = MagicMock(total=12, success=True)

        with patch("app.services.combat.CombatService._get_stats", return_value=(session_state, 10, 10, 10, 2, 0)):
            new_hp, _, previous_hp, concentration_check = CombatService._apply_damage_to_target(
                self.db,
                "player-123",
                "player",
                8,
                False,
                self.state,
                concentration_roll_source="manual",
                concentration_manual_roll=13,
            )

        self.assertEqual(previous_hp, 20)
        self.assertEqual(new_hp, 12)
        self.assertIsNotNone(concentration_check)
        mock_build_roll_stats.assert_called_once()
        mock_resolve_saving_throw.assert_called_once_with(
            mock_build_roll_stats.return_value,
            ability="constitution",
            dc=10,
            roll_source="manual",
            manual_roll=13,
        )

    @patch("app.services.combat_service.spell_automation.resolve_saving_throw")
    def test_zero_damage_does_not_trigger_concentration_check(self, mock_resolve_saving_throw):
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "currentHP": 20,
                "maxHP": 20,
                "deathSaves": {"successes": 0, "failures": 0},
            },
        )
        self.state.participants[0]["active_effects"] = [
            {
                "id": "hm-self",
                "kind": "spell_effect",
                "source_participant_id": "p1",
                "duration_type": "manual",
                "created_at": "2026-03-28T00:00:00Z",
                "display_label": "Hunter's Mark",
                "metadata": {
                    "concentration": True,
                    "concentration_group": "conc-1",
                    "source_spell_key": "hunters_mark",
                },
            }
        ]

        with patch("app.services.combat.CombatService._get_stats", return_value=(session_state, 10, 10, 10, 2, 0)):
            new_hp, _, previous_hp, concentration_check = CombatService._apply_damage_to_target(
                self.db,
                "player-123",
                "player",
                0,
                False,
                self.state,
            )

        self.assertEqual(previous_hp, 20)
        self.assertEqual(new_hp, 20)
        self.assertIsNone(concentration_check)
        mock_resolve_saving_throw.assert_not_called()

    def test_apply_damage_to_npc_sets_defeated_at_zero_hp(self):
        self.state.current_turn_index = 1
        session_entity = SessionEntity(
            id="enemy-123",
            session_id="session-123",
            campaign_entity_id="ce-1",
            current_hp=6,
        )
        npc_result = MagicMock()
        npc_result.first.return_value = MagicMock(base_hp=6)
        self.db.exec.return_value = npc_result

        with patch("app.services.combat.CombatService._get_stats", return_value=(session_entity, 12, 10, 10, 2, 0)):
            new_hp, _, previous_hp, concentration_check = CombatService._apply_damage_to_target(
                self.db,
                "enemy-123",
                "session_entity",
                8,
                False,
                self.state,
            )

        self.assertEqual(previous_hp, 6)
        self.assertEqual(new_hp, 0)
        self.assertIsNone(concentration_check)
        self.assertEqual(session_entity.current_hp, 0)
        self.assertEqual(self.state.participants[1]["status"], "defeated")

    async def test_downed_player_cannot_attack(self):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.participants[0]["status"] = "downed"

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.attack(
                    self.db,
                    "session-123",
                    CombatAttackRequest(
                        actor_participant_id="p1",
                        target_ref_id="enemy-123",
                        weapon_item_id="unarmed",
                    ),
                    "user-1",
                    False,
                )

        self.assertEqual(ctx.exception.status_code, 403)

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_attack_updates_player_target_to_downed(self, mock_emit_log, mock_emit_state, mock_emit_player_state_update):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "currentHP": 3,
                "maxHP": 12,
                "deathSaves": {"successes": 0, "failures": 0},
            },
        )

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
                        damageDice="1d4",
                        damageBonus=2,
                        damageType="slashing",
                        isMelee=True,
                    ),
                ),
            ):
                with patch(
                    "app.services.combat.CombatService._get_stats",
                    side_effect=[
                        (session_state, 10, 10, 10, 2, 0),
                        (session_state, 10, 10, 10, 2, 0),
                        (session_state, 10, 10, 10, 2, 0),
                    ],
                ):
                    attack_result = await CombatService.entity_action(
                        self.db,
                        "session-123",
                        CombatEntityActionRequest(
                            actor_participant_id="e1",
                            target_ref_id="player-123",
                            combat_action_id="claw",
                            roll_source="manual",
                            manual_roll=18,
                        ),
                        "gm-user",
                        True,
                    )
                    damage_result = await CombatService.entity_action_damage(
                        self.db,
                        "session-123",
                        CombatResolveDamageRequest(
                            actor_participant_id="e1",
                            pending_attack_id=attack_result["pending_attack_id"],
                            roll_source="manual",
                            manual_rolls=[1],
                        ),
                        "gm-user",
                        True,
                    )

        self.assertTrue(attack_result["is_hit"])
        self.assertEqual(damage_result["new_hp"], 0)
        self.assertEqual(self.state.participants[0]["status"], "downed")

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_death_save_advances_turn_without_manual_end_turn_error(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.participants[0]["status"] = "downed"
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "currentHP": 0,
                "maxHP": 12,
                "deathSaves": {"successes": 0, "failures": 0},
            },
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat.CombatService._get_stats", return_value=(session_state, 10, 10, 10, 2, 0)):
                with patch("random.randint", return_value=12):
                    result = await CombatService.death_save(
                        self.db,
                        "session-123",
                        "user-1",
                        False,
                        "p1",
                    )

        self.assertEqual(result["roll"], 12)
        self.assertEqual(result["status"], "downed")
        self.assertEqual(session_state.state_json["deathSaves"]["successes"], 1)
        self.assertEqual(self.state.current_turn_index, 1)

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_apply_damage_and_healing_sync_status(self, mock_emit_log, mock_emit_state, mock_emit_player_state_update):
        self.state.phase = CombatPhase.active
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "currentHP": 4,
                "maxHP": 12,
                "deathSaves": {"successes": 0, "failures": 0},
            },
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat.CombatService._get_stats", side_effect=[
                (session_state, 10, 10, 10, 2, 0),
                (session_state, 10, 10, 10, 2, 0),
            ]):
                await CombatService.apply_damage(
                    self.db,
                    "session-123",
                    CombatApplyDamageRequest(target_ref_id="player-123", amount=6, kind="player"),
                    "gm-user",
                    True,
                )

        self.assertEqual(self.state.participants[0]["status"], "downed")

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat.CombatService._get_stats", side_effect=[
                (session_state, 10, 10, 10, 2, 0),
                (session_state, 10, 10, 10, 2, 0),
            ]):
                await CombatService.apply_healing(
                    self.db,
                    "session-123",
                    CombatApplyHealingRequest(target_ref_id="player-123", amount=5, kind="player"),
                    "gm-user",
                    True,
                )

        self.assertEqual(self.state.participants[0]["status"], "active")
