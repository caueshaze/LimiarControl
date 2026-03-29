import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.models.base_item import BaseItemWeaponRangeType
from app.models.campaign import SystemType
from app.models.campaign_entity import CampaignEntity
from app.models.combat import CombatPhase, CombatState
from app.models.inventory import InventoryItem
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
from app.schemas.roll import RollResult


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
                    self.state.participants[0]["turn_resources"]["action_used"] = False

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

    def test_build_player_attack_context_applies_archery_to_ranged_weapon(self):
        item = Item(
            id="item-longbow",
            campaign_id="camp-1",
            name="Longbow",
            description="",
            type=ItemType.WEAPON,
            damage_dice="1d8",
            damage_type="piercing",
            weapon_range_type=BaseItemWeaponRangeType.RANGED,
        )
        inventory_item = MagicMock()
        inventory_item.id = "inv-1"

        with patch(
            "app.services.combat.CombatService._resolve_player_weapon_item",
            return_value=(inventory_item, item),
        ), patch(
            "app.services.combat.CombatService._get_player_legacy_weapon_profile",
            return_value=None,
        ), patch(
            "app.services.combat.CombatService._choose_player_weapon_ability",
            return_value="dexterity",
        ), patch(
            "app.services.combat.CombatService._is_player_weapon_proficient",
            return_value=True,
        ):
            context = CombatService._build_player_attack_context(
                self.db,
                "session-123",
                "player-123",
                {
                    "class": "guardian",
                    "level": 2,
                    "abilities": {"strength": 10, "dexterity": 14},
                    "currentWeaponId": "inv-1",
                    "fightingStyle": "archery",
                },
            )

        self.assertEqual(context["attack_bonus"], 6)
        self.assertTrue(context["is_ranged_weapon"])

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
                return_value=(5, "", 12, None),
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
            damage_type="slashing",
            is_crit=False,
            state=self.state,
        )

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_attack_damage_applies_colossus_slayer_only_once_per_turn(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.db.exec.return_value.first.return_value = MagicMock(max_hp=12)

        pending_attack = {
            "type": "player_attack",
            "target_ref_id": "enemy-123",
            "target_kind": "session_entity",
            "target_display_name": "Goblin",
            "target_ac": 12,
            "weapon_name": "Longbow",
            "damage_dice": "1d8",
            "damage_bonus": 0,
            "attack_bonus": 6,
            "damage_type": "piercing",
            "is_critical": False,
            "roll": 18,
        }
        self.state.participants[0]["pending_attack"] = {"id": "pending-1", **pending_attack}

        attacker_state = MagicMock()
        attacker_state.state_json = {"class": "guardian", "subclass": "hunter", "level": 3}
        target_state = MagicMock()
        target_state.campaign_entity_id = "npc-1"
        target_state.current_hp = 9

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_stats",
            side_effect=[
                (attacker_state, 12, 10, 14, 2, 0),
                (target_state, 12, 10, 10, 2, 0),
                (attacker_state, 12, 10, 14, 2, 0),
                (target_state, 12, 10, 10, 2, 0),
            ],
        ), patch(
            "app.services.combat.CombatService._apply_damage_to_target",
            return_value=(0, "", 9, None),
        ), patch(
            "app.services.combat.CombatService._resolve_damage_roll",
            side_effect=[([4], 4), ([6], 6), ([4], 4)],
        ):
            first = await CombatService.attack_damage(
                self.db,
                "session-123",
                CombatResolveDamageRequest(pending_attack_id="pending-1"),
                "user-xyz",
                True,
            )

            self.state.participants[0]["pending_attack"] = {"id": "pending-2", **pending_attack}
            second = await CombatService.attack_damage(
                self.db,
                "session-123",
                CombatResolveDamageRequest(pending_attack_id="pending-2"),
                "user-xyz",
                True,
            )

        self.assertEqual(first["damage"], 10)
        self.assertEqual(first["extra_damage"], 6)
        self.assertEqual(first["extra_damage_rolls"], [6])
        self.assertEqual(second["damage"], 4)
        self.assertEqual(second["extra_damage"], 0)
        self.assertTrue(self.state.participants[0]["turn_resources"]["colossus_slayer_used"])

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
                    # Reset action economy for second cast in same test
                    self.state.participants[0]["turn_resources"] = {"action_used": False, "bonus_action_used": False, "reaction_used": False}
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
                    save_success_outcome="none",
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
                        # Reset action economy for second cast in same test
                        self.state.participants[0]["turn_resources"] = {"action_used": False, "bonus_action_used": False, "reaction_used": False}
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
        self.assertEqual(failed_result["save_success_outcome"], "none")
        self.assertEqual(failed_result["roll_result"].roll_type, "save")
        self.assertTrue(failed_result["effect_roll_required"])
        self.assertIsNotNone(failed_result["pending_spell_id"])

        self.assertTrue(saved_result["is_saved"])
        self.assertEqual(saved_result["save_success_outcome"], "none")
        self.assertFalse(saved_result["effect_roll_required"])
        self.assertIsNone(saved_result["pending_spell_id"])

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_player_saving_throw_spell_can_apply_half_damage_on_success(
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
                            "name": "Raio de Gelo",
                            "canonicalKey": "ray_of_frost_save",
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
                    canonical_key="ray_of_frost_save",
                    name_en="Raio de Gelo",
                    name_pt=None,
                    level=0,
                    damage_type="cold",
                    saving_throw="dexterity",
                    save_success_outcome="half_damage",
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
                        with patch("random.randint", return_value=18):
                            first_result = await CombatService.cast_spell(
                                self.db,
                                "session-123",
                                CombatCastSpellRequest(
                                    actor_participant_id="p1",
                                    target_ref_id="enemy-123",
                                    spell_canonical_key="ray_of_frost_save",
                                    spell_mode="saving_throw",
                                    damage_dice="1d8",
                                    damage_bonus=1,
                                    damage_type="cold",
                                    save_ability="dexterity",
                                ),
                                "user-1",
                                False,
                            )

                    self.assertTrue(first_result["is_saved"])
                    self.assertEqual(first_result["save_success_outcome"], "half_damage")
                    self.assertTrue(first_result["effect_roll_required"])
                    self.assertIsNotNone(first_result["pending_spell_id"])

                    with patch(
                        "app.services.combat.CombatService._apply_damage_to_target",
                        return_value=(5, "", 9, None),
                    ) as mock_apply_damage:
                        with patch("random.randint", return_value=8):
                            second_result = await CombatService.cast_spell_effect(
                                self.db,
                                "session-123",
                                CombatResolveSpellEffectRequest(
                                    actor_participant_id="p1",
                                    pending_spell_id=first_result["pending_spell_id"],
                                    roll_source="system",
                                ),
                                "user-1",
                                False,
                            )

        self.assertTrue(second_result["is_saved"])
        self.assertEqual(second_result["save_success_outcome"], "half_damage")
        self.assertEqual(second_result["effect_rolls"], [8])
        self.assertEqual(second_result["base_effect"], 8)
        self.assertEqual(second_result["effect_bonus"], 1)
        self.assertEqual(second_result["damage"], 4)
        self.assertEqual(second_result["effect_roll_source"], "system")
        self.assertNotIn("pending_attack", self.state.participants[0])
        mock_apply_damage.assert_called_once_with(
            self.db,
            "enemy-123",
            "session_entity",
            4,
            damage_type="cold",
            is_crit=False,
            state=self.state,
        )
        final_log = mock_emit_log.await_args_list[-1].args[1]["message"]
        self.assertIn("Dano rolado 9", final_log)
        self.assertIn("dano aplicado 4", final_log)
        mock_emit_state.assert_awaited()

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
    async def test_player_heal_spell_upcast_scales_effect_dice_with_higher_slot(
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
                            "name": "Cure Wounds",
                            "canonicalKey": "cure_wounds",
                            "level": 1,
                            "prepared": True,
                        }
                    ],
                    "slots": {
                        "1": {"used": 0, "max": 2},
                        "3": {"used": 0, "max": 1},
                    },
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
                    heal_dice="1d8",
                    upcast_json={"mode": "add_heal", "dice": "1d8", "perLevel": 1},
                ),
            ):
                with patch(
                    "app.services.combat.CombatService._get_stats",
                    return_value=(attacker_state, 12, 10, 10, 2, 3),
                ):
                    first_result = await CombatService.cast_spell(
                        self.db,
                        "session-123",
                        CombatCastSpellRequest(
                            actor_participant_id="p1",
                            target_ref_id="player-123",
                            spell_canonical_key="cure_wounds",
                            spell_mode="heal",
                            slot_level=3,
                        ),
                        "user-1",
                        False,
                    )

                    self.assertTrue(first_result["effect_roll_required"])
                    self.assertEqual(first_result["effect_dice"], "3d8")
                    self.assertEqual(
                        attacker_state.state_json["spellcasting"]["slots"]["3"]["used"],
                        1,
                    )
                    self.assertEqual(
                        attacker_state.state_json["spellcasting"]["slots"]["1"]["used"],
                        0,
                    )

                    with patch(
                        "app.services.combat.CombatService._apply_healing_to_target",
                        return_value=(12, "", 0),
                    ) as mock_apply_healing:
                        second_result = await CombatService.cast_spell_effect(
                            self.db,
                            "session-123",
                            CombatResolveSpellEffectRequest(
                                actor_participant_id="p1",
                                pending_spell_id=first_result["pending_spell_id"],
                                roll_source="manual",
                                manual_rolls=[5, 4, 3],
                            ),
                            "user-1",
                            False,
                        )

        self.assertEqual(second_result["healing"], 12)
        self.assertEqual(second_result["effect_rolls"], [5, 4, 3])
        mock_apply_healing.assert_called_once_with(
            self.db,
            "player-123",
            "player",
            12,
            self.state,
        )

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_player_damage_spell_upcast_scales_effect_dice_with_higher_slot(
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
                            "name": "Magic Missile",
                            "canonicalKey": "magic_missile",
                            "level": 1,
                            "prepared": True,
                        }
                    ],
                    "slots": {
                        "1": {"used": 0, "max": 2},
                        "3": {"used": 0, "max": 1},
                    },
                }
            },
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                return_value=MagicMock(
                    canonical_key="magic_missile",
                    name_en="Magic Missile",
                    name_pt=None,
                    level=1,
                    damage_type="Force",
                    saving_throw=None,
                    damage_dice="3d4+3",
                    upcast_json={
                        "mode": "increase_targets",
                        "dice": "1d4+1",
                        "perLevel": 1,
                    },
                ),
            ):
                with patch(
                    "app.services.combat.CombatService._get_stats",
                    return_value=(attacker_state, 12, 10, 10, 2, 3),
                ):
                    first_result = await CombatService.cast_spell(
                        self.db,
                        "session-123",
                        CombatCastSpellRequest(
                            actor_participant_id="p1",
                            target_ref_id="enemy-123",
                            spell_canonical_key="magic_missile",
                            spell_mode="direct_damage",
                            slot_level=3,
                            damage_type="Force",
                        ),
                        "user-1",
                        False,
                    )

                    self.assertTrue(first_result["effect_roll_required"])
                    self.assertEqual(first_result["effect_dice"], "5d4+5")
                    self.assertEqual(
                        attacker_state.state_json["spellcasting"]["slots"]["3"]["used"],
                        1,
                    )
                    self.assertEqual(
                        attacker_state.state_json["spellcasting"]["slots"]["1"]["used"],
                        0,
                    )

                    with patch(
                        "app.services.combat.CombatService._apply_damage_to_target",
                        return_value=(7, "", 20, None),
                    ) as mock_apply_damage:
                        second_result = await CombatService.cast_spell_effect(
                            self.db,
                            "session-123",
                            CombatResolveSpellEffectRequest(
                                actor_participant_id="p1",
                                pending_spell_id=first_result["pending_spell_id"],
                                roll_source="manual",
                                manual_rolls=[4, 3, 2, 1, 1],
                            ),
                            "user-1",
                            False,
                        )

        self.assertEqual(second_result["damage"], 16)
        self.assertEqual(second_result["effect_rolls"], [4, 3, 2, 1, 1])
        mock_apply_damage.assert_called_once_with(
            self.db,
            "enemy-123",
            "session_entity",
            16,
            damage_type="force",
            is_crit=False,
            state=self.state,
        )

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
                return_value=(9, "", 16, None),
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
            damage_type="fire",
            is_crit=False,
            state=self.state,
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

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    @patch("app.services.combat_service.player_actions.resolve_saving_throw")
    async def test_draconic_bloodline_spell_marks_elemental_affinity_eligibility(
        self,
        mock_resolve_saving_throw,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        mock_resolve_saving_throw.return_value = MagicMock(total=9, success=False)
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "class": "sorcerer",
                "subclass": "draconic_bloodline",
                "level": 6,
                "subclassConfig": {"draconicAncestry": "red"},
                "abilities": {"charisma": 18},
                "spellcasting": {
                    "spells": [
                        {
                            "name": "Fireball",
                            "canonicalKey": "fireball",
                            "level": 3,
                            "prepared": True,
                        }
                    ],
                    "slots": {"3": {"used": 0, "max": 2}},
                },
            },
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
            return_value=MagicMock(
                canonical_key="fireball",
                name_en="Fireball",
                name_pt="Bola de Fogo",
                level=3,
                resolution_type="saving_throw",
                saving_throw="dexterity",
                save_success_outcome="half_damage",
                damage_type="fire",
                damage_dice="8d6",
                heal_dice=None,
                upcast_json=None,
                casting_time_type="action",
            ),
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(attacker_state, 12, 10, 10, 3, 4),
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=RollActorStats(
                display_name="Goblin",
                abilities={"dexterity": 10},
                actor_kind="session_entity",
                actor_ref_id="enemy-123",
            ),
        ):
            result = await CombatService.cast_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id="p1",
                    target_ref_id="enemy-123",
                    spell_canonical_key="fireball",
                ),
                "user-1",
                False,
            )

        self.assertTrue(result["elemental_affinity_eligible"])
        self.assertEqual(result["elemental_affinity_damage_type"], "fire")
        self.assertEqual(result["elemental_affinity_bonus"], 4)
        self.assertTrue(result["effect_roll_required"])

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_hunters_mark_cast_creates_concentration_effects(
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
                            "name": "Marca do Caçador",
                            "canonicalKey": "hunters_mark",
                            "level": 1,
                            "prepared": True,
                        }
                    ],
                    "slots": {"1": {"used": 0, "max": 2}},
                }
            },
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
            return_value=MagicMock(
                canonical_key="hunters_mark",
                name_en="Hunter's Mark",
                name_pt="Marca do Caçador",
                level=1,
                resolution_type="automatic",
                saving_throw=None,
                damage_type=None,
            ),
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(attacker_state, 12, 10, 10, 2, 3),
        ):
            result = await CombatService.cast_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id="p1",
                    target_ref_id="enemy-123",
                    spell_canonical_key="hunters_mark",
                ),
                "user-1",
                False,
            )

        self.assertEqual(result["action_kind"], "utility")
        self.assertIn("aplicada", result["summary_text"])
        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["1"]["used"], 1)
        self.assertEqual(self.state.participants[0]["active_effects"][0]["kind"], "spell_effect")
        self.assertEqual(
            self.state.participants[0]["active_effects"][0]["metadata"]["marked_target_participant_id"],
            "e1",
        )
        self.assertEqual(self.state.participants[1]["active_effects"][0]["kind"], "spell_effect")

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_hunters_mark_adds_bonus_damage_only_to_marked_target(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.participants[0]["active_effects"] = [
            {
                "id": "hm-1",
                "kind": "spell_effect",
                "source_participant_id": "p1",
                "duration_type": "manual",
                "created_at": "2026-03-28T00:00:00Z",
                "metadata": {
                    "source_spell_key": "hunters_mark",
                    "marked_target_participant_id": "e1",
                },
            }
        ]
        self.state.participants[0]["pending_attack"] = {
            "id": "pending-hm",
            "type": "player_attack",
            "target_ref_id": "enemy-123",
            "target_kind": "session_entity",
            "target_display_name": "Goblin",
            "target_ac": 12,
            "weapon_name": "Longbow",
            "damage_dice": "1d8",
            "damage_bonus": 2,
            "attack_bonus": 5,
            "damage_type": "piercing",
            "is_critical": False,
            "roll": 17,
            "is_weapon_attack": True,
        }
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={"spellcasting": {"spells": []}},
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(attacker_state, 12, 10, 10, 2, 3),
        ), patch(
            "app.services.combat.CombatService._get_target_hp_snapshot",
            return_value=(10, 10),
        ), patch(
            "app.services.combat.CombatService._apply_damage_to_target",
            return_value=(3, "", 15, None),
        ) as mock_apply_damage, patch(
            "app.services.combat.CombatService._resolve_damage_roll",
            side_effect=[([4], 4), ([6], 6)],
        ):
            result = await CombatService.attack_damage(
                self.db,
                "session-123",
                CombatResolveDamageRequest(
                    actor_participant_id="p1",
                    pending_attack_id="pending-hm",
                    roll_source="system",
                ),
                "user-1",
                False,
            )

        self.assertEqual(result["extra_damage"], 6)
        self.assertEqual(result["extra_damage_rolls"], [6])
        self.assertEqual(result["damage"], 12)
        mock_apply_damage.assert_called_once_with(
            self.db,
            "enemy-123",
            "session_entity",
            12,
            damage_type="piercing",
            is_crit=False,
            state=self.state,
        )

    async def test_attack_is_blocked_when_attacker_is_charmed_by_target(self):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.participants[0]["active_effects"] = [
            {
                "id": "charm-1",
                "kind": "condition",
                "condition_type": "charmed",
                "source_participant_id": "e1",
                "duration_type": "manual",
                "created_at": "2026-03-28T00:00:00Z",
                "metadata": {"charmer_participant_id": "e1"},
            }
        ]

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError) as context:
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

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("charmed", str(context.exception.detail).lower())

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_animal_friendship_rejects_non_beast_targets_before_spending_slot(
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
                            "name": "Amizade Animal",
                            "canonicalKey": "animal_friendship",
                            "level": 1,
                            "prepared": True,
                        }
                    ],
                    "slots": {"1": {"used": 0, "max": 2}},
                }
            },
        )
        session_entity_result = MagicMock()
        session_entity_result.first.return_value = SessionEntity(
            id="enemy-123",
            session_id="session-123",
            campaign_entity_id="ce-goblin",
            overrides={},
        )
        campaign_entity_result = MagicMock()
        campaign_entity_result.first.return_value = CampaignEntity(
            id="ce-goblin",
            campaign_id="camp-1",
            name="Goblin",
            creature_type="humanoid",
        )
        self.db.exec.side_effect = [session_entity_result, campaign_entity_result]

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
            return_value=MagicMock(
                canonical_key="animal_friendship",
                name_en="Animal Friendship",
                name_pt="Amizade Animal",
                level=1,
                resolution_type="saving_throw",
                saving_throw="wisdom",
                save_success_outcome="none",
                damage_type=None,
            ),
        ), patch(
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
                        spell_canonical_key="animal_friendship",
                    ),
                    "user-1",
                    False,
                )

        self.assertIn("beasts", str(context.exception.detail))
        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["1"]["used"], 0)

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_animal_friendship_applies_charmed_on_failed_save_only(
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
                            "name": "Amizade Animal",
                            "canonicalKey": "animal_friendship",
                            "level": 1,
                            "prepared": True,
                        }
                    ],
                    "slots": {"1": {"used": 0, "max": 3}},
                }
            },
        )
        session_entity_result = MagicMock()
        session_entity_result.first.return_value = SessionEntity(
            id="enemy-123",
            session_id="session-123",
            campaign_entity_id="ce-wolf",
            overrides={},
        )
        campaign_entity_result = MagicMock()
        campaign_entity_result.first.return_value = CampaignEntity(
            id="ce-wolf",
            campaign_id="camp-1",
            name="Wolf",
            creature_type="beast",
        )
        target_stats = RollActorStats(
            display_name="Wolf",
            abilities={"wisdom": 10},
            actor_kind="session_entity",
            actor_ref_id="enemy-123",
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
            return_value=MagicMock(
                canonical_key="animal_friendship",
                name_en="Animal Friendship",
                name_pt="Amizade Animal",
                level=1,
                resolution_type="saving_throw",
                saving_throw="wisdom",
                save_success_outcome="none",
                damage_type=None,
            ),
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(attacker_state, 12, 10, 10, 2, 3),
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=target_stats,
        ):
            self.db.exec.side_effect = [
                session_entity_result,
                campaign_entity_result,
                session_entity_result,
                campaign_entity_result,
            ]
            with patch("random.randint", return_value=5):
                failed_result = await CombatService.cast_spell(
                    self.db,
                    "session-123",
                    CombatCastSpellRequest(
                        actor_participant_id="p1",
                        target_ref_id="enemy-123",
                        spell_canonical_key="animal_friendship",
                    ),
                    "user-1",
                    False,
                )
            failed_effects = list(self.state.participants[1]["active_effects"])

            self.state.participants[0]["turn_resources"] = {
                "action_used": False,
                "bonus_action_used": False,
                "reaction_used": False,
            }
            self.state.participants[1]["active_effects"] = []
            with patch("random.randint", return_value=18):
                saved_result = await CombatService.cast_spell(
                    self.db,
                    "session-123",
                    CombatCastSpellRequest(
                        actor_participant_id="p1",
                        target_ref_id="enemy-123",
                        spell_canonical_key="animal_friendship",
                    ),
                    "user-1",
                    False,
                )

        self.assertFalse(failed_result["is_saved"])
        self.assertEqual(failed_effects[0]["condition_type"], "charmed")
        self.assertEqual(self.state.participants[1]["active_effects"], [])
        self.assertTrue(saved_result["is_saved"])

    @patch("app.services.combat_service.spell_automation.grant_catalog_item_to_player_inventory")
    @patch("app.services.combat.CombatService._get_campaign_system_for_session", return_value=SystemType.DND5E)
    @patch("app.services.combat.CombatService._get_session_entry", return_value=MagicMock(campaign_id="camp-1", party_id="party-1"))
    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_goodberry_cast_marks_inventory_refresh_and_grants_item(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
        mock_session_entry,
        mock_campaign_system,
        mock_grant_item,
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
                            "name": "Bom Fruto",
                            "canonicalKey": "goodberry",
                            "level": 1,
                            "prepared": True,
                        }
                    ],
                    "slots": {"1": {"used": 0, "max": 2}},
                }
            },
        )
        mock_grant_item.return_value = MagicMock(id="inv-goodberry")

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
            return_value=MagicMock(
                canonical_key="goodberry",
                name_en="Goodberry",
                name_pt="Bom Fruto",
                level=1,
                resolution_type="automatic",
                saving_throw=None,
                damage_type=None,
            ),
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(attacker_state, 12, 10, 10, 2, 3),
        ):
            result = await CombatService.cast_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id="p1",
                    target_ref_id="player-123",
                    spell_canonical_key="goodberry",
                ),
                "user-1",
                False,
            )

        self.assertEqual(result["action_kind"], "utility")
        self.assertTrue(result["inventory_refresh_required"])
        self.assertIn("Bom Fruto", result["summary_text"])
        mock_grant_item.assert_called_once()
        self.assertEqual(
            mock_grant_item.call_args.kwargs["source_spell_canonical_key"],
            "goodberry",
        )
        expires_at = mock_grant_item.call_args.kwargs["expires_at"]
        self.assertIsNotNone(expires_at)
        self.assertIsNotNone(expires_at.tzinfo)
        self.assertGreater(expires_at, datetime.now(timezone.utc))
        self.assertLess(expires_at - datetime.now(timezone.utc), timedelta(hours=24, minutes=1))

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_magic_item_spell_cast_consumes_charge_without_requiring_sheet_spell(
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
            state_json={},
        )
        inventory_entry = InventoryItem(
            id="inv-bracelet",
            campaign_id="camp-1",
            member_id="member-1",
            item_id="item-bracelet",
            quantity=1,
            charges_current=1,
            is_equipped=False,
        )
        bracelet_item = Item(
            id="item-bracelet",
            campaign_id="camp-1",
            name="Bracelete de Phantyr: Mãos Flamejantes",
            type=ItemType.MAGIC,
            description="Bracelete de uso único.",
            charges_max=1,
            recharge_type="none",
            magic_effect_json={
                "type": "cast_spell",
                "spellCanonicalKey": "burning_hands",
                "castLevel": 1,
                "ignoreComponents": True,
                "noFreeHandRequired": True,
            },
        )
        save_roll = RollResult(
            event_id="roll-1",
            roll_type="save",
            actor_kind="session_entity",
            actor_ref_id="enemy-123",
            actor_display_name="Goblin",
            rolls=[4, 4],
            selected_roll=4,
            advantage_mode="normal",
            modifier_used=1,
            override_used=False,
            formula="1d20 + 1",
            total=5,
            ability="dexterity",
            dc=10,
            success=False,
            timestamp=datetime.now(timezone.utc),
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._resolve_player_inventory_spell_item",
            return_value=(inventory_entry, bracelet_item, bracelet_item.magic_effect_json),
        ), patch(
            "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
            return_value=MagicMock(
                canonical_key="burning_hands",
                name_en="Burning Hands",
                name_pt="Mãos Flamejantes",
                level=1,
                resolution_type="damage",
                saving_throw="DEX",
                save_success_outcome="half_damage",
                damage_dice="3d6",
                damage_type="Fire",
                heal_dice=None,
                upcast_json=None,
                casting_time_type="action",
            ),
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(attacker_state, 12, 10, 10, 2, 0),
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=MagicMock(),
        ), patch(
            "app.services.combat_service.player_actions.resolve_saving_throw",
            return_value=save_roll,
        ):
            result = await CombatService.cast_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id="p1",
                    target_ref_id="enemy-123",
                    inventory_item_id="inv-bracelet",
                ),
                "user-1",
                False,
            )

        self.assertEqual(result["spell_canonical_key"], "burning_hands")
        self.assertEqual(result["action_kind"], "saving_throw")
        self.assertTrue(result["inventory_refresh_required"])
        self.assertIsNotNone(result["pending_spell_id"])
        self.assertEqual(inventory_entry.charges_current, 0)
        self.assertEqual(attacker_state.state_json, {})

    @patch("app.services.combat.CombatService.get_state")
    async def test_magic_item_spell_fails_when_no_charges_remain(self, mock_get_state):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        mock_get_state.return_value = self.state
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={},
        )
        inventory_entry = InventoryItem(
            id="inv-bracelet",
            campaign_id="camp-1",
            member_id="member-1",
            item_id="item-bracelet",
            quantity=1,
            charges_current=0,
            is_equipped=False,
        )
        bracelet_item = Item(
            id="item-bracelet",
            campaign_id="camp-1",
            name="Bracelete de Phantyr: Detectar Magia",
            type=ItemType.MAGIC,
            description="Bracelete de uso único.",
            charges_max=1,
            recharge_type="none",
            magic_effect_json={
                "type": "cast_spell",
                "spellCanonicalKey": "detect_magic",
                "castLevel": 1,
                "ignoreComponents": True,
                "noFreeHandRequired": True,
            },
        )

        with patch(
            "app.services.combat.CombatService._resolve_player_inventory_spell_item",
            return_value=(inventory_entry, bracelet_item, bracelet_item.magic_effect_json),
        ), patch(
            "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
            return_value=MagicMock(
                canonical_key="detect_magic",
                name_en="Detect Magic",
                name_pt="Detectar Magia",
                level=1,
                resolution_type="utility",
                saving_throw=None,
                save_success_outcome=None,
                damage_dice=None,
                damage_type=None,
                heal_dice=None,
                upcast_json=None,
                casting_time_type="action",
            ),
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(attacker_state, 12, 10, 10, 2, 0),
        ):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.cast_spell(
                    self.db,
                    "session-123",
                    CombatCastSpellRequest(
                        actor_participant_id="p1",
                        target_ref_id="player-123",
                        inventory_item_id="inv-bracelet",
                    ),
                    "user-1",
                    False,
                )

        self.assertIn("no charges remaining", str(ctx.exception))
        self.assertFalse(
            CombatService._get_turn_resources(self.state.participants[0])["action_used"]
        )

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
