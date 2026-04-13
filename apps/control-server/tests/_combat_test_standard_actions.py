import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.combat import CombatAttackRequest, CombatStandardActionRequest
from app.schemas.roll import RollActorStats
from app.services.combat import CombatService, CombatServiceError
from app.services.healing_consumables import HealingConsumableError


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

    def _make_healing_consumable_context(self, *, item_name="Healing Potion"):
        session_entry = SimpleNamespace(
            id="session-123",
            campaign_id="campaign-123",
            party_id="party-123",
        )
        actor_member = SimpleNamespace(
            id="member-1",
            user_id="user-1",
            display_name="Hero",
        )
        inventory_item = SimpleNamespace(id="inv-1", quantity=1)
        item = SimpleNamespace(
            id="item-1",
            name=item_name,
            heal_dice="2d4",
            heal_bonus=2,
        )
        return SimpleNamespace(
            session_entry=session_entry,
            actor_member=actor_member,
            inventory_item=inventory_item,
            item=item,
        )

    def _make_healing_roll(
        self,
        *,
        total_healing=7,
        effect_rolls=None,
        roll_source="system",
        effect_dice="2d4",
        effect_bonus=2,
        base_effect=5,
    ):
        return SimpleNamespace(
            total_healing=total_healing,
            effect_dice=effect_dice,
            effect_rolls=effect_rolls or [3, 2],
            roll_source=roll_source,
            effect_bonus=effect_bonus,
            base_effect=base_effect,
        )

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

    # ---- dragonborn breath weapon ----

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_dragonborn_breath_weapon_requires_ancestry(self, mock_emit_log, mock_emit_state):
        self._make_active_state()
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "race": "dragonborn",
                "raceConfig": {},
                "abilities": {"constitution": 14},
                "level": 3,
            },
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(attacker_state, 0, 0, 0, 2, 0),
        ):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.standard_action(
                    self.db,
                    "session-123",
                    CombatStandardActionRequest(
                        action="dragonborn_breath_weapon",
                        target_participant_id="e1",
                    ),
                    "user-1",
                    False,
                )

        self.assertIn("not available", str(ctx.exception).lower())
        self.assertFalse(self.state.participants[0]["turn_resources"]["action_used"])

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_dragonborn_breath_weapon_applies_save_damage_and_consumes_use(
        self,
        mock_emit_log,
        mock_emit_state,
        mock_emit_player_state_update,
    ):
        self._make_active_state()
        self.state.participants[1].update(
            {
                "ref_id": "target-123",
                "kind": "player",
                "display_name": "Target",
                "team": "enemies",
                "actor_user_id": "user-2",
            }
        )
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "race": "dragonborn",
                "raceConfig": {"draconicAncestry": "blue"},
                "level": 7,
                "abilities": {"constitution": 14},
                "classResources": {
                    "dragonbornBreathWeapon": {"usesMax": 1, "usesRemaining": 1},
                },
                "currentHP": 22,
                "maxHP": 22,
                "deathSaves": {"successes": 0, "failures": 0},
            },
        )
        target_state = SessionState(
            id="state-target",
            session_id="session-123",
            player_user_id="target-123",
            state_json={
                "race": "dragonborn",
                "raceConfig": {"draconicAncestry": "bronze"},
                "currentHP": 20,
                "maxHP": 20,
                "abilities": {"constitution": 12},
                "deathSaves": {"successes": 0, "failures": 0},
            },
        )
        save_stats = RollActorStats(
            display_name="Target",
            abilities={"dexterity": 12},
            proficiency_bonus=2,
            actor_kind="player",
            actor_ref_id="target-123",
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_stats",
            side_effect=[
                (attacker_state, 0, 0, 0, 3, 0),
                (attacker_state, 0, 0, 0, 3, 0),
                (target_state, 0, 0, 0, 2, 0),
                (target_state, 0, 0, 0, 2, 0),
            ],
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=save_stats,
        ), patch(
            "app.services.combat_service.standard_actions.resolve_saving_throw",
            return_value=MagicMock(total=12, success=True),
        ), patch(
            "app.services.combat.CombatService._resolve_damage_roll",
            return_value=([5, 3, 1], 9),
        ):
            result = await CombatService.standard_action(
                self.db,
                "session-123",
                CombatStandardActionRequest(
                    action="dragonborn_breath_weapon",
                    target_participant_id="e1",
                ),
                "user-1",
                False,
            )

        self.assertEqual(result["action"], "dragonborn_breath_weapon")
        self.assertEqual(result["damage_type"], "lightning")
        self.assertEqual(result["save_ability"], "dexterity")
        self.assertEqual(result["save_dc"], 13)
        self.assertTrue(result["is_saved"])
        self.assertEqual(result["effect_dice"], "3d6")
        self.assertEqual(result["damage"], 2)
        self.assertEqual(result["new_hp"], 18)
        self.assertEqual(result["uses_remaining"], 0)
        self.assertTrue(self.state.participants[0]["turn_resources"]["action_used"])
        self.assertEqual(
            attacker_state.state_json["classResources"]["dragonbornBreathWeapon"]["usesRemaining"],
            0,
        )
        self.assertEqual(target_state.state_json["currentHP"], 18)
        self.assertEqual(mock_emit_player_state_update.await_count, 2)

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_dragonborn_breath_weapon_cannot_be_used_without_remaining_uses(
        self,
        mock_emit_log,
        mock_emit_state,
    ):
        self._make_active_state()
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "race": "dragonborn",
                "raceConfig": {"draconicAncestry": "red"},
                "abilities": {"constitution": 14},
                "level": 3,
                "classResources": {
                    "dragonbornBreathWeapon": {"usesMax": 1, "usesRemaining": 0},
                },
            },
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(attacker_state, 0, 0, 0, 2, 0),
        ):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.standard_action(
                    self.db,
                    "session-123",
                    CombatStandardActionRequest(
                        action="dragonborn_breath_weapon",
                        target_participant_id="e1",
                    ),
                    "user-1",
                    False,
                )

        self.assertIn("no dragonborn breath weapon uses remaining", str(ctx.exception).lower())
        self.assertFalse(self.state.participants[0]["turn_resources"]["action_used"])

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

    async def test_use_object_structured_heals_self_and_consumes_item(self):
        self._make_active_state()
        context = self._make_healing_consumable_context()
        healing_roll = self._make_healing_roll()
        target_state = MagicMock()
        target_state.state_json = {"maxHP": 12}

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_session_entry",
            return_value=context.session_entry,
        ), patch(
            "app.services.combat_service.standard_actions.resolve_healing_consumable",
            return_value=context,
        ), patch(
            "app.services.combat_service.standard_actions.roll_healing_consumable",
            return_value=healing_roll,
        ) as mock_roll, patch(
            "app.services.combat.CombatService._apply_healing_to_target",
            return_value=(7, "", 0),
        ), patch(
            "app.services.combat_service.standard_actions.consume_inventory_item",
            return_value=0,
        ) as mock_consume, patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(target_state, 0, 0, 0, 0, 0),
        ), patch(
            "app.services.combat_service.standard_actions.build_consumable_used_payload",
            return_value={"type": "consumable_used"},
        ), patch(
            "app.services.combat_service.standard_actions.record_consumable_used_activity",
        ), patch("app.services.combat.CombatService._emit_player_state_update") as mock_emit_player_state, patch(
            "app.services.combat.CombatService._emit_state",
        ), patch(
            "app.services.combat.CombatService._emit_log",
        ), patch(
            "app.services.combat_service.standard_actions.publish_consumable_used_realtime",
        ) as mock_publish:
            result = await CombatService.standard_action(
                self.db,
                "session-123",
                CombatStandardActionRequest(
                    action="use_object",
                    inventory_item_id="inv-1",
                ),
                "user-1",
                False,
            )

        self.assertTrue(result["effect_applied"])
        self.assertEqual(result["target_display_name"], "Hero")
        self.assertEqual(result["target_kind"], "player")
        self.assertEqual(result["healing"], 7)
        self.assertEqual(result["new_hp"], 7)
        self.assertEqual(result["effect_rolls"], [3, 2])
        self.assertEqual(result["effect_roll_source"], "system")
        self.assertIn("Healing Potion", result["message"])
        self.assertTrue(self.state.participants[0]["turn_resources"]["action_used"])
        mock_roll.assert_called_once_with(
            context.item,
            roll_source="system",
            manual_rolls=None,
        )
        mock_consume.assert_called_once_with(self.db, context.inventory_item)
        mock_emit_player_state.assert_awaited_once()
        mock_publish.assert_awaited_once()

    async def test_use_object_structured_heals_allied_player(self):
        self._make_active_state()
        self.state.participants.append(
            {
                "id": "p2",
                "ref_id": "ally-123",
                "kind": "player",
                "display_name": "Cleric",
                "initiative": None,
                "status": "downed",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-2",
                "turn_resources": {
                    "action_used": False,
                    "bonus_action_used": False,
                    "reaction_used": False,
                },
                "active_effects": [],
            }
        )
        context = self._make_healing_consumable_context()
        healing_roll = self._make_healing_roll(total_healing=9, effect_rolls=[4, 3], base_effect=7)
        target_state = MagicMock()
        target_state.state_json = {"maxHP": 15}

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_session_entry",
            return_value=context.session_entry,
        ), patch(
            "app.services.combat_service.standard_actions.resolve_healing_consumable",
            return_value=context,
        ), patch(
            "app.services.combat_service.standard_actions.roll_healing_consumable",
            return_value=healing_roll,
        ), patch(
            "app.services.combat.CombatService._apply_healing_to_target",
            return_value=(11, " (Revived!)", 2),
        ), patch(
            "app.services.combat_service.standard_actions.consume_inventory_item",
            return_value=1,
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(target_state, 0, 0, 0, 0, 0),
        ), patch(
            "app.services.combat_service.standard_actions.build_consumable_used_payload",
            return_value={"type": "consumable_used"},
        ), patch(
            "app.services.combat_service.standard_actions.record_consumable_used_activity",
        ), patch("app.services.combat.CombatService._emit_player_state_update") as mock_emit_player_state, patch(
            "app.services.combat.CombatService._emit_state",
        ), patch(
            "app.services.combat.CombatService._emit_log",
        ), patch(
            "app.services.combat_service.standard_actions.publish_consumable_used_realtime",
        ):
            result = await CombatService.standard_action(
                self.db,
                "session-123",
                CombatStandardActionRequest(
                    action="use_object",
                    inventory_item_id="inv-1",
                    target_participant_id="p2",
                ),
                "user-1",
                False,
            )

        self.assertEqual(result["target_display_name"], "Cleric")
        self.assertEqual(result["target_kind"], "player")
        self.assertEqual(result["new_hp"], 11)
        self.assertIn("Revived", result["message"])
        mock_emit_player_state.assert_awaited_once_with(
            self.db,
            "session-123",
            "ally-123",
            target_state,
        )

    async def test_use_object_structured_heals_allied_session_entity(self):
        self._make_active_state()
        self.state.participants.append(
            {
                "id": "a1",
                "ref_id": "ally-entity-123",
                "kind": "session_entity",
                "display_name": "Wolf",
                "initiative": None,
                "status": "downed",
                "team": "allies",
                "visible": True,
                "actor_user_id": None,
                "turn_resources": {
                    "action_used": False,
                    "bonus_action_used": False,
                    "reaction_used": False,
                },
                "active_effects": [],
            }
        )
        context = self._make_healing_consumable_context()
        healing_roll = self._make_healing_roll(total_healing=6, effect_rolls=[2, 2], base_effect=4)

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_session_entry",
            return_value=context.session_entry,
        ), patch(
            "app.services.combat_service.standard_actions.resolve_healing_consumable",
            return_value=context,
        ), patch(
            "app.services.combat_service.standard_actions.roll_healing_consumable",
            return_value=healing_roll,
        ), patch(
            "app.services.combat.CombatService._apply_healing_to_target",
            return_value=(5, "", 0),
        ), patch(
            "app.services.combat_service.standard_actions.consume_inventory_item",
            return_value=0,
        ), patch(
            "app.services.combat.CombatService._get_session_entity_and_campaign_entity",
            return_value=(SimpleNamespace(current_hp=0), SimpleNamespace(max_hp=12)),
        ), patch(
            "app.services.combat_service.standard_actions.build_consumable_used_payload",
            return_value={"type": "consumable_used"},
        ), patch(
            "app.services.combat_service.standard_actions.record_consumable_used_activity",
        ), patch("app.services.combat.CombatService._emit_entity_hp_update") as mock_emit_entity_hp, patch(
            "app.services.combat.CombatService._emit_state",
        ), patch(
            "app.services.combat.CombatService._emit_log",
        ), patch(
            "app.services.combat_service.standard_actions.publish_consumable_used_realtime",
        ):
            result = await CombatService.standard_action(
                self.db,
                "session-123",
                CombatStandardActionRequest(
                    action="use_object",
                    inventory_item_id="inv-1",
                    target_participant_id="a1",
                ),
                "user-1",
                False,
            )

        self.assertEqual(result["target_display_name"], "Wolf")
        self.assertEqual(result["target_kind"], "session_entity")
        self.assertEqual(result["new_hp"], 5)
        mock_emit_entity_hp.assert_awaited_once_with(
            self.db,
            "session-123",
            "ally-entity-123",
            0,
        )

    async def test_use_object_structured_manual_roll_applies_selected_values(self):
        self._make_active_state()
        context = self._make_healing_consumable_context()
        target_state = MagicMock()
        target_state.state_json = {"maxHP": 12}

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_session_entry",
            return_value=context.session_entry,
        ), patch(
            "app.services.combat_service.standard_actions.resolve_healing_consumable",
            return_value=context,
        ), patch(
            "app.services.combat.CombatService._apply_healing_to_target",
            return_value=(7, "", 3),
        ), patch(
            "app.services.combat_service.standard_actions.consume_inventory_item",
            return_value=0,
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(target_state, 0, 0, 0, 0, 0),
        ), patch(
            "app.services.combat_service.standard_actions.build_consumable_used_payload",
            return_value={"type": "consumable_used"},
        ), patch(
            "app.services.combat_service.standard_actions.record_consumable_used_activity",
        ), patch(
            "app.services.combat.CombatService._emit_player_state_update",
        ), patch(
            "app.services.combat.CombatService._emit_state",
        ), patch(
            "app.services.combat.CombatService._emit_log",
        ), patch(
            "app.services.combat_service.standard_actions.publish_consumable_used_realtime",
        ):
            result = await CombatService.standard_action(
                self.db,
                "session-123",
                CombatStandardActionRequest(
                    action="use_object",
                    inventory_item_id="inv-1",
                    roll_source="manual",
                    manual_rolls=[4, 1],
                ),
                "user-1",
                False,
            )

        self.assertEqual(result["effect_rolls"], [4, 1])
        self.assertEqual(result["effect_roll_source"], "manual")
        self.assertEqual(result["healing"], 7)

    async def test_use_object_structured_manual_roll_requires_exact_count(self):
        self._make_active_state()
        context = self._make_healing_consumable_context()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_session_entry",
            return_value=context.session_entry,
        ), patch(
            "app.services.combat_service.standard_actions.resolve_healing_consumable",
            return_value=context,
        ):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.standard_action(
                    self.db,
                    "session-123",
                    CombatStandardActionRequest(
                        action="use_object",
                        inventory_item_id="inv-1",
                        roll_source="manual",
                        manual_rolls=[4],
                    ),
                    "user-1",
                    False,
                )

        self.assertIn("exactly 2 result", str(ctx.exception))

    async def test_use_object_structured_rejects_enemy_target(self):
        self._make_active_state()
        context = self._make_healing_consumable_context()
        healing_roll = self._make_healing_roll()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_session_entry",
            return_value=context.session_entry,
        ), patch(
            "app.services.combat_service.standard_actions.resolve_healing_consumable",
            return_value=context,
        ), patch(
            "app.services.combat_service.standard_actions.roll_healing_consumable",
            return_value=healing_roll,
        ):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.standard_action(
                    self.db,
                    "session-123",
                    CombatStandardActionRequest(
                        action="use_object",
                        inventory_item_id="inv-1",
                        target_participant_id="e1",
                    ),
                    "user-1",
                    False,
                )

        self.assertIn("allied participant", str(ctx.exception))

    async def test_use_object_structured_rejects_out_of_stock_consumable(self):
        self._make_active_state()
        context = self._make_healing_consumable_context()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_session_entry",
            return_value=context.session_entry,
        ), patch(
            "app.services.combat_service.standard_actions.resolve_healing_consumable",
            side_effect=HealingConsumableError("Consumable is out of stock", 400),
        ):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.standard_action(
                    self.db,
                    "session-123",
                    CombatStandardActionRequest(
                        action="use_object",
                        inventory_item_id="inv-1",
                    ),
                    "user-1",
                    False,
                )

        self.assertIn("out of stock", str(ctx.exception))

    async def test_use_object_structured_rejects_non_healing_consumable(self):
        self._make_active_state()
        context = self._make_healing_consumable_context()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_session_entry",
            return_value=context.session_entry,
        ), patch(
            "app.services.combat_service.standard_actions.resolve_healing_consumable",
            side_effect=HealingConsumableError(
                "Consumable has no structured healing effect",
                400,
            ),
        ):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.standard_action(
                    self.db,
                    "session-123",
                    CombatStandardActionRequest(
                        action="use_object",
                        inventory_item_id="inv-1",
                    ),
                    "user-1",
                    False,
                )

        self.assertIn("structured healing effect", str(ctx.exception))

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
                CombatStandardActionRequest(
                    action="dodge",
                    override_resource_limit=True,
                ),
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
