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
    CombatCastSpellRequest,
    CombatEntityActionRequest,
    CombatParticipant,
    CombatResolveDamageRequest,
    CombatResolveSpellEffectRequest,
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


class CombatFlowTestsMixin:
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    @patch("app.services.combat.CombatService._sync_all_participant_statuses")
    @patch("app.services.combat.CombatService.get_state", return_value=None)
    async def test_start_combat_keeps_session_entity_initiative_pending(
        self,
        _mock_get_state,
        mock_sync_all_participant_statuses,
        mock_emit_log,
        mock_emit_state,
    ):
        req = CombatStartRequest(
            participants=[
                CombatParticipant(
                    id="p1",
                    ref_id="player-123",
                    kind="player",
                    display_name="Hero",
                    team="players",
                    visible=True,
                    actor_user_id="user-1",
                ),
                CombatParticipant(
                    id="e1",
                    ref_id="enemy-123",
                    kind="session_entity",
                    display_name="Goblin",
                    team="enemies",
                    visible=True,
                ),
            ]
        )

        new_state = await CombatService.start_combat(self.db, "session-123", req)

        self.assertEqual(new_state.phase, CombatPhase.initiative)
        self.assertEqual(new_state.participants[0]["initiative"], None)
        self.assertEqual(new_state.participants[1]["initiative"], None)
        self.db.add.assert_called_once()
        self.db.commit.assert_called_once()
        mock_emit_state.assert_called_once()
        mock_sync_all_participant_statuses.assert_called_once()

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    @patch("app.services.combat.CombatService._sync_all_participant_statuses")
    @patch("app.services.combat.CombatService.get_state", return_value=None)
    async def test_start_combat(self, mock_get_state, mock_sync_all_participant_statuses, mock_emit_log, mock_emit_state):
        req = CombatStartRequest(
            participants=[
                CombatParticipant(
                    id="p1", ref_id="player-123", kind="player", display_name="Hero", team="players", visible=True
                )
            ]
        )
        new_state = await CombatService.start_combat(self.db, "session-123", req)
        self.assertEqual(new_state.phase, CombatPhase.initiative)
        self.assertEqual(len(new_state.participants), 1)
        self.db.add.assert_called_once()
        self.db.commit.assert_called_once()
        mock_emit_state.assert_called_once()

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_set_initiative(self, mock_emit_log, mock_emit_state):
        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            req = CombatSetInitiativeRequest(
                initiatives=[
                    CombatSetInitiativeParticipant(id="p1", initiative=15),
                    CombatSetInitiativeParticipant(id="e1", initiative=20)
                ]
            )
            state = await CombatService.set_initiative(self.db, "session-123", req)
            
            # Enemy should be first now, sorted by int
            self.assertEqual(state.phase, CombatPhase.active)
            self.assertEqual(state.participants[0]["id"], "e1")
            self.assertEqual(state.participants[1]["id"], "p1")

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_apply_initiative_roll_transitions_when_all_are_ready(self, mock_emit_log, mock_emit_state):
        self.state.participants[1]["initiative"] = 12
        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            state = await CombatService.apply_initiative_roll(
                self.db,
                "session-123",
                "player",
                "player-123",
                15,
            )

            self.assertIsNotNone(state)
            self.assertEqual(state.phase, CombatPhase.active)
            self.assertEqual(state.participants[0]["id"], "p1")
            self.assertEqual(state.participants[0]["initiative"], 15)
            mock_emit_state.assert_called_once()
            mock_emit_log.assert_called_once()

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_next_turn(self, mock_emit_log, mock_emit_state):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            state = await CombatService.next_turn(self.db, "session-123", actor_user_id="user-xyz", is_gm=True)
            self.assertEqual(state.current_turn_index, 1)

            state = await CombatService.next_turn(self.db, "session-123", actor_user_id="user-xyz", is_gm=True)
            self.assertEqual(state.current_turn_index, 0)
            self.assertEqual(state.round, 2)

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_attack_hit_and_miss(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        
        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(), 10, 16, 14, 2, 0), # attacker: AC 10, STR 16 (+3), DEX 14 (+2), Prof 2
                (MagicMock(), 15, 10, 10, 2, 0)  # target: AC 15
            ]):
                req = CombatAttackRequest(target_ref_id="enemy-123", weapon_item_id="unarmed")
                
                # Force d20 roll to 15 (Hit: 15 + 3 str + 2 prof = 20 >= 15)
                with patch("random.randint", return_value=15):
                    res = await CombatService.attack(self.db, "session-123", req, "user-xyz", True)
                    self.assertTrue(res["is_hit"])
                    self.assertEqual(res["damage"], 0)
                    self.assertTrue(res["damage_roll_required"])
                    self.assertIsNotNone(res["pending_attack_id"])
                    self.assertIn("pending_attack", self.state.participants[0])

                # Reset patches for miss
            with patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(), 10, 16, 14, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0) 
            ]):
                # Force d20 roll to 2 (Miss: 2 + 3 + 2 = 7 < 15)
                with patch("random.randint", return_value=2):
                    res = await CombatService.attack(self.db, "session-123", req, "user-xyz", True)
                    self.assertFalse(res["is_hit"])
                    self.assertEqual(res["damage"], 0)
                    self.assertFalse(res["damage_roll_required"])
                    self.assertNotIn("pending_attack", self.state.participants[0])

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_attack_uses_current_weapon_when_payload_omits_weapon(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        attacker_state = MagicMock()
        attacker_state.state_json = {"currentWeaponId": "inv-1"}

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_stats",
                side_effect=[
                    (attacker_state, 12, 16, 14, 2, 0),
                    (MagicMock(), 15, 10, 10, 2, 0),
                ],
            ):
                with patch(
                    "app.services.combat.CombatService._build_player_attack_context",
                    return_value={
                        "name": "Longsword",
                        "damage_dice": "1d8",
                        "attack_bonus": 5,
                        "damage_bonus": 3,
                    },
                ) as mock_context:
                    with patch("random.randint", return_value=15):
                        res = await CombatService.attack(
                            self.db,
                            "session-123",
                            CombatAttackRequest(target_ref_id="enemy-123"),
                            "user-xyz",
                            True,
                        )

        self.assertTrue(res["is_hit"])
        self.assertEqual(res["damage"], 0)
        self.assertTrue(res["damage_roll_required"])
        self.assertIsNotNone(res["pending_attack_id"])
        mock_context.assert_called_once_with(
            self.db,
            "session-123",
            "player-123",
            {"currentWeaponId": "inv-1"},
            None,
        )

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_attack_accepts_manual_roll_and_returns_roll_result(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        attacker_state = MagicMock()
        attacker_state.state_json = {"currentWeaponId": "inv-1"}

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_stats",
                side_effect=[
                    (attacker_state, 12, 16, 14, 2, 0),
                    (MagicMock(), 14, 10, 10, 2, 0),
                ],
            ):
                with patch(
                    "app.services.combat.CombatService._build_player_attack_context",
                    return_value={
                        "name": "Longsword",
                        "damage_dice": "1d8",
                        "damage_bonus": 3,
                        "attack_bonus": 5,
                        "damage_type": "slashing",
                    },
                ):
                    res = await CombatService.attack(
                        self.db,
                        "session-123",
                        CombatAttackRequest(
                            target_ref_id="enemy-123",
                            roll_source="manual",
                            manual_roll=17,
                        ),
                        "user-xyz",
                        True,
                    )

        self.assertTrue(res["is_hit"])
        self.assertEqual(res["roll"], 22)
        self.assertEqual(res["damage"], 0)
        self.assertTrue(res["damage_roll_required"])
        self.assertIsNotNone(res["pending_attack_id"])
        self.assertEqual(res["roll_result"].roll_source, "manual")
        self.assertEqual(res["roll_result"].selected_roll, 17)
        self.assertEqual(res["target_ac"], 14)

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_attack_damage_accepts_manual_rolls(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.participants[0]["pending_attack"] = {
            "id": "pending-1",
            "type": "player_attack",
            "target_ref_id": "enemy-123",
            "target_kind": "session_entity",
            "target_display_name": "Goblin",
            "target_ac": 14,
            "weapon_name": "Longsword",
            "damage_dice": "1d8",
            "damage_bonus": 3,
            "attack_bonus": 5,
            "damage_type": "slashing",
            "is_critical": False,
            "roll": 22,
            "roll_result": {
                "event_id": "roll-1",
                "roll_type": "attack",
                "actor_kind": "player",
                "actor_ref_id": "player-123",
                "actor_display_name": "Hero",
                "rolls": [17],
                "selected_roll": 17,
                "advantage_mode": "normal",
                "modifier_used": 5,
                "override_used": True,
                "formula": "d20 + 5",
                "total": 22,
                "target_ac": 14,
                "success": True,
                "is_gm_roll": True,
                "roll_source": "manual",
                "timestamp": "2026-03-22T00:00:00Z",
            },
        }

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._apply_damage_to_target",
                return_value=(5, "", 12),
            ) as mock_apply_damage:
                res = await CombatService.attack_damage(
                    self.db,
                    "session-123",
                    CombatResolveDamageRequest(
                        actor_participant_id="p1",
                        pending_attack_id="pending-1",
                        roll_source="manual",
                        manual_rolls=[4],
                    ),
                    "user-xyz",
                    True,
                )

        self.assertEqual(res["damage"], 7)
        self.assertEqual(res["damage_rolls"], [4])
        self.assertEqual(res["base_damage"], 4)
        self.assertEqual(res["damage_roll_source"], "manual")
        self.assertNotIn("pending_attack", self.state.participants[0])
        mock_apply_damage.assert_called_once_with(
            self.db,
            "enemy-123",
            "session_entity",
            7,
            False,
            self.state,
        )

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_player_spell_attack_hit_and_miss_use_spell_bonus(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "spellcasting": {
                    "spells": [
                        {
                            "name": "Fire Bolt",
                            "canonicalKey": "fire_bolt",
                            "level": 0,
                            "prepared": True,
                        }
                    ]
                }
            },
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                return_value=MagicMock(
                    canonical_key="fire_bolt",
                    name_en="Fire Bolt",
                    name_pt=None,
                    level=0,
                    damage_type="fire",
                    saving_throw=None,
                ),
            ):
                def get_stats_side_effect(_db, ref_id, kind, _session_id=""):
                    if ref_id == "player-123" and kind == "player":
                        return (attacker_state, 12, 10, 10, 2, 3)
                    return (MagicMock(), 14, 10, 10, 2, 0)

                with patch(
                    "app.services.combat.CombatService._get_stats",
                    side_effect=get_stats_side_effect,
                ):
                    hit_result = await CombatService.cast_spell(
                        self.db,
                        "session-123",
                        CombatCastSpellRequest(
                            actor_participant_id="p1",
                            target_ref_id="enemy-123",
                            spell_canonical_key="fire_bolt",
                            spell_mode="spell_attack",
                            damage_dice="1d10",
                            damage_type="fire",
                            roll_source="manual",
                            manual_roll=12,
                        ),
                        "user-1",
                        False,
                    )
                    miss_result = await CombatService.cast_spell(
                        self.db,
                        "session-123",
                        CombatCastSpellRequest(
                            actor_participant_id="p1",
                            target_ref_id="enemy-123",
                            spell_canonical_key="fire_bolt",
                            spell_mode="spell_attack",
                            damage_dice="1d10",
                            damage_type="fire",
                            roll_source="manual",
                            manual_roll=1,
                        ),
                        "user-1",
                        False,
                    )

        self.assertTrue(hit_result["is_hit"])
        self.assertEqual(hit_result["roll"], 17)
        self.assertEqual(hit_result["action_kind"], "spell_attack")
        self.assertTrue(hit_result["effect_roll_required"])
        self.assertIsNotNone(hit_result["pending_spell_id"])
        self.assertEqual(hit_result["roll_result"].total, 17)

        self.assertFalse(miss_result["is_hit"])
        self.assertIsNone(miss_result["pending_spell_id"])
        self.assertFalse(miss_result["effect_roll_required"])
        self.assertEqual(miss_result["roll_result"].total, 6)

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_player_saving_throw_spell_handles_failure_and_success(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "spellcasting": {
                    "spells": [
                        {
                            "name": "Sacred Flame",
                            "canonicalKey": "sacred_flame",
                            "level": 0,
                            "prepared": True,
                        }
                    ]
                }
            },
        )
        target_roll_stats = RollActorStats(
            display_name="Goblin",
            abilities={"dexterity": 10},
            actor_kind="session_entity",
            actor_ref_id="enemy-123",
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                return_value=MagicMock(
                    canonical_key="sacred_flame",
                    name_en="Sacred Flame",
                    name_pt=None,
                    level=0,
                    damage_type="radiant",
                    saving_throw="dexterity",
                ),
            ):
                with patch(
                    "app.services.combat.CombatService._get_stats",
                    return_value=(attacker_state, 12, 10, 10, 2, 3),
                ):
                    with patch(
                        "app.services.combat.CombatService._build_roll_actor_stats_for_save",
                        return_value=target_roll_stats,
                    ):
                        with patch("random.randint", return_value=5):
                            failed_result = await CombatService.cast_spell(
                                self.db,
                                "session-123",
                                CombatCastSpellRequest(
                                    actor_participant_id="p1",
                                    target_ref_id="enemy-123",
                                    spell_canonical_key="sacred_flame",
                                    spell_mode="saving_throw",
                                    damage_dice="1d8",
                                    damage_type="radiant",
                                    save_ability="dexterity",
                                ),
                                "user-1",
                                False,
                            )
                        with patch("random.randint", return_value=18):
                            saved_result = await CombatService.cast_spell(
                                self.db,
                                "session-123",
                                CombatCastSpellRequest(
                                    actor_participant_id="p1",
                                    target_ref_id="enemy-123",
                                    spell_canonical_key="sacred_flame",
                                    spell_mode="saving_throw",
                                    damage_dice="1d8",
                                    damage_type="radiant",
                                    save_ability="dexterity",
                                ),
                                "user-1",
                                False,
                            )

        self.assertFalse(failed_result["is_saved"])
        self.assertEqual(failed_result["save_dc"], 13)
        self.assertEqual(failed_result["roll_result"].roll_type, "save")
        self.assertTrue(failed_result["effect_roll_required"])
        self.assertIsNotNone(failed_result["pending_spell_id"])

        self.assertTrue(saved_result["is_saved"])
        self.assertFalse(saved_result["effect_roll_required"])
        self.assertIsNone(saved_result["pending_spell_id"])

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    @patch("app.services.combat.CombatService._apply_healing_to_target", return_value=(5, " (Revived!)", 0))
    async def test_player_heal_spell_spends_slot_and_applies_healing(
        self,
        mock_apply_healing,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "spellcasting": {
                    "spells": [
                        {
                            "name": "Cure Wounds",
                            "canonicalKey": "cure_wounds",
                            "level": 1,
                            "prepared": True,
                        }
                    ],
                    "slots": {"1": {"used": 0, "max": 2}},
                }
            },
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                return_value=MagicMock(
                    canonical_key="cure_wounds",
                    name_en="Cure Wounds",
                    name_pt=None,
                    level=1,
                    damage_type=None,
                    saving_throw=None,
                ),
            ):
                with patch(
                    "app.services.combat.CombatService._get_stats",
                    return_value=(attacker_state, 12, 10, 10, 2, 3),
                ):
                    result = await CombatService.cast_spell(
                        self.db,
                        "session-123",
                        CombatCastSpellRequest(
                            actor_participant_id="p1",
                            target_ref_id="player-123",
                            spell_canonical_key="cure_wounds",
                            spell_mode="heal",
                            slot_level=1,
                            heal_bonus=5,
                        ),
                        "user-1",
                        False,
                    )

        self.assertEqual(result["action_kind"], "heal")
        self.assertEqual(result["healing"], 5)
        self.assertEqual(result["new_hp"], 5)
        self.assertFalse(result["effect_roll_required"])
        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["1"]["used"], 1)
        mock_apply_healing.assert_called_once_with(
            self.db,
            "player-123",
            "player",
            5,
            self.state,
        )

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    @patch("app.services.combat.CombatService._apply_healing_to_target", return_value=(6, " (Revived!)", 0))
    async def test_player_heal_spell_can_target_downed_ally(
        self,
        mock_apply_healing,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.participants.append(
            {
                "id": "p2",
                "ref_id": "player-ally",
                "kind": "player",
                "display_name": "Luna",
                "initiative": 11,
                "status": "downed",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-2",
            }
        )
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "spellcasting": {
                    "spells": [
                        {
                            "name": "Healing Word",
                            "canonicalKey": "healing_word",
                            "level": 1,
                            "prepared": True,
                        }
                    ],
                    "slots": {"1": {"used": 0, "max": 2}},
                }
            },
        )
        ally_state = SessionState(
            id="state-ally",
            session_id="session-123",
            player_user_id="player-ally",
            state_json={},
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                return_value=MagicMock(
                    canonical_key="healing_word",
                    name_en="Healing Word",
                    name_pt=None,
                    level=1,
                    damage_type=None,
                    saving_throw=None,
                ),
            ):
                def get_stats_side_effect(_db, ref_id, kind, _session_id=""):
                    if ref_id == "player-123" and kind == "player":
                        return (attacker_state, 12, 10, 10, 2, 3)
                    if ref_id == "player-ally" and kind == "player":
                        return (ally_state, 12, 10, 10, 2, 0)
                    raise AssertionError(f"Unexpected get_stats call for {ref_id}/{kind}")

                with patch(
                    "app.services.combat.CombatService._get_stats",
                    side_effect=get_stats_side_effect,
                ):
                    result = await CombatService.cast_spell(
                        self.db,
                        "session-123",
                        CombatCastSpellRequest(
                            actor_participant_id="p1",
                            target_ref_id="player-ally",
                            spell_canonical_key="healing_word",
                            spell_mode="heal",
                            slot_level=1,
                            heal_bonus=6,
                        ),
                        "user-1",
                        False,
                    )

        self.assertEqual(result["action_kind"], "heal")
        self.assertEqual(result["healing"], 6)
        self.assertEqual(result["new_hp"], 6)
        self.assertFalse(result["effect_roll_required"])
        mock_apply_healing.assert_called_once_with(
            self.db,
            "player-ally",
            "player",
            6,
            self.state,
        )
        mock_emit_player_state_update.assert_called()

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_player_heal_spell_rejects_when_slot_is_unavailable(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "spellcasting": {
                    "spells": [
                        {
                            "name": "Healing Word",
                            "canonicalKey": "healing_word",
                            "level": 1,
                            "prepared": True,
                        }
                    ],
                    "slots": {"1": {"used": 1, "max": 1}},
                }
            },
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                return_value=MagicMock(
                    canonical_key="healing_word",
                    name_en="Healing Word",
                    name_pt=None,
                    level=1,
                    damage_type=None,
                    saving_throw=None,
                ),
            ):
                with patch(
                    "app.services.combat.CombatService._get_stats",
                    return_value=(attacker_state, 12, 10, 10, 2, 3),
                ):
                    with self.assertRaises(CombatServiceError) as context:
                        await CombatService.cast_spell(
                            self.db,
                            "session-123",
                            CombatCastSpellRequest(
                                actor_participant_id="p1",
                                target_ref_id="player-123",
                                spell_canonical_key="healing_word",
                                spell_mode="heal",
                                slot_level=1,
                                heal_bonus=4,
                            ),
                            "user-1",
                            False,
                        )

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("No spell slots", str(context.exception.detail))

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_player_spell_effect_lifecycle_creates_and_clears_pending_effect(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "spellcasting": {
                    "spells": [
                        {
                            "name": "Fire Bolt",
                            "canonicalKey": "fire_bolt",
                            "level": 0,
                            "prepared": True,
                        }
                    ]
                }
            },
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                return_value=MagicMock(
                    canonical_key="fire_bolt",
                    name_en="Fire Bolt",
                    name_pt=None,
                    level=0,
                    damage_type="fire",
                    saving_throw=None,
                ),
            ):
                def get_stats_side_effect(_db, ref_id, kind, _session_id=""):
                    if ref_id == "player-123" and kind == "player":
                        return (attacker_state, 12, 10, 10, 2, 3)
                    if ref_id == "enemy-123" and kind == "session_entity":
                        return (MagicMock(), 14, 10, 10, 2, 0)
                    raise AssertionError(f"Unexpected get_stats call for {ref_id}/{kind}")

                with patch(
                    "app.services.combat.CombatService._get_stats",
                    side_effect=get_stats_side_effect,
                ):
                    first_result = await CombatService.cast_spell(
                        self.db,
                        "session-123",
                        CombatCastSpellRequest(
                            actor_participant_id="p1",
                            target_ref_id="enemy-123",
                            spell_canonical_key="fire_bolt",
                            spell_mode="spell_attack",
                            damage_dice="1d10",
                            damage_type="fire",
                            roll_source="manual",
                            manual_roll=12,
                        ),
                        "user-1",
                        False,
                    )

            self.assertTrue(first_result["effect_roll_required"])
            self.assertIsNotNone(first_result["pending_spell_id"])
            self.assertEqual(self.state.participants[0]["pending_attack"]["type"], "player_spell_effect")

            with patch(
                "app.services.combat.CombatService._apply_damage_to_target",
                return_value=(9, "", 16),
            ) as mock_apply_damage:
                second_result = await CombatService.cast_spell_effect(
                    self.db,
                    "session-123",
                    CombatResolveSpellEffectRequest(
                        actor_participant_id="p1",
                        pending_spell_id=first_result["pending_spell_id"],
                        roll_source="manual",
                        manual_rolls=[7],
                    ),
                    "user-1",
                    False,
                )

        self.assertEqual(second_result["damage"], 7)
        self.assertEqual(second_result["effect_rolls"], [7])
        self.assertEqual(second_result["effect_roll_source"], "manual")
        self.assertNotIn("pending_attack", self.state.participants[0])
        mock_apply_damage.assert_called_once_with(
            self.db,
            "enemy-123",
            "session_entity",
            7,
            False,
            self.state,
        )

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_direct_damage_rejects_structured_saving_throw_spell(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "spellcasting": {
                    "spells": [
                        {
                            "name": "Sacred Flame",
                            "canonicalKey": "sacred_flame",
                            "level": 0,
                            "prepared": True,
                        }
                    ]
                }
            },
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                return_value=MagicMock(
                    canonical_key="sacred_flame",
                    name_en="Sacred Flame",
                    name_pt=None,
                    level=0,
                    damage_type="radiant",
                    saving_throw="dexterity",
                ),
            ):
                with patch(
                    "app.services.combat.CombatService._get_stats",
                    return_value=(attacker_state, 12, 10, 10, 2, 3),
                ):
                    with self.assertRaises(CombatServiceError) as context:
                        await CombatService.cast_spell(
                            self.db,
                            "session-123",
                            CombatCastSpellRequest(
                                actor_participant_id="p1",
                                target_ref_id="enemy-123",
                                spell_canonical_key="sacred_flame",
                                spell_mode="direct_damage",
                                damage_dice="1d8",
                                damage_type="radiant",
                            ),
                            "user-1",
                            False,
                        )

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("direct_damage", str(context.exception.detail))

    def test_build_roll_actor_stats_for_save_uses_explicit_entity_save_override(self):
        session_entity = SessionEntity(
            id="enemy-123",
            session_id="session-123",
            campaign_entity_id="ce-1",
            overrides={},
        )
        npc = CampaignEntity(
            id="ce-1",
            campaign_id="camp-1",
            name="Goblin Shaman",
            abilities={"dexterity": 14},
            saving_throws={"dexterity": 5},
        )

        with patch(
            "app.services.combat.CombatService._get_session_entity_and_campaign_entity",
            return_value=(session_entity, npc),
        ):
            with patch(
                "app.services.combat.CombatService._get_stats",
                return_value=(session_entity, 13, 10, 14, 2, 2),
            ):
                stats = CombatService._build_roll_actor_stats_for_save(
                    self.db,
                    "session-123",
                    "enemy-123",
                    "session_entity",
                    "Goblin Shaman",
                )

        self.assertEqual(stats.abilities["dexterity"], 14)
        self.assertEqual(stats.saving_throws["dexterity"], 5)

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_next_turn_skips_dead_and_defeated(self, mock_emit_log, mock_emit_state):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.participants[1]["status"] = "defeated"  # the goblin e1
        # Add a third participant
        self.state.participants.append({
             "id": "p2", "ref_id": "player-456", "kind": "player", "display_name": "Ally",
             "initiative": None, "status": "active", "team": "players", "visible": True, "actor_user_id": "user-2"
        })
        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            state = await CombatService.next_turn(self.db, "session-123", actor_user_id="user-xyz", is_gm=True)
            # Should skip index 1 (defeated goblin) and go to 2
            self.assertEqual(state.current_turn_index, 2)
