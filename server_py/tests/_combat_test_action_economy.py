import unittest
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.schemas.roll import RollActorStats
from app.schemas.combat import (
    CombatAttackRequest,
    CombatCastSpellRequest,
    CombatConsumeReactionRequest,
    CombatEntityActionRequest,
    CombatApplyDamageRequest,
    CombatApplyHealingRequest,
    CombatResolveDamageRequest,
    CombatSetInitiativeParticipant,
    CombatSetInitiativeRequest,
    CombatStartRequest,
    CombatParticipant,
)
from app.schemas.campaign_entity import CombatAction
from app.services.combat import CombatService, CombatServiceError


class CombatActionEconomyTestsMixin:

    def _make_active_state(self):
        """Set up state for active combat with turn_resources on p1."""
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.state.participants[0]["turn_resources"] = {
            "action_used": False,
            "bonus_action_used": False,
            "reaction_used": False,
        }
        self.state.participants[1]["turn_resources"] = {
            "action_used": False,
            "bonus_action_used": False,
            "reaction_used": False,
        }

    # ---- turn resource reset ----

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_turn_resources_reset_on_next_turn(self, mock_emit_log, mock_emit_state):
        self._make_active_state()
        # Mark p1's action as used
        self.state.participants[0]["turn_resources"]["action_used"] = True
        self.state.participants[0]["turn_resources"]["reaction_used"] = True

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            # Advance turn: p1 -> p2
            await CombatService.next_turn(self.db, "session-123", "user-1", True)

            # p2 (now active) should have fresh resources
            p2 = self.state.participants[1]
            self.assertFalse(p2["turn_resources"]["action_used"])
            self.assertFalse(p2["turn_resources"]["bonus_action_used"])
            self.assertFalse(p2["turn_resources"]["reaction_used"])

            # Advance turn again: p2 -> p1 (round 2)
            await CombatService.next_turn(self.db, "session-123", "user-1", True)

            # p1 should have fresh resources now
            p1 = self.state.participants[0]
            self.assertFalse(p1["turn_resources"]["action_used"])
            self.assertFalse(p1["turn_resources"]["reaction_used"])

    # ---- attack consumes action ----

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_attack_consumes_action(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update):
        self._make_active_state()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(), 10, 16, 14, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0),
            ]):
                with patch("random.randint", return_value=15):
                    await CombatService.attack(
                        self.db, "session-123",
                        CombatAttackRequest(target_ref_id="enemy-123"),
                        "user-1", False,
                    )

        self.assertTrue(self.state.participants[0]["turn_resources"]["action_used"])

    # ---- cannot attack twice ----

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_cannot_attack_twice_in_same_turn(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update):
        self._make_active_state()
        # Mark action as already used
        self.state.participants[0]["turn_resources"]["action_used"] = True

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.attack(
                    self.db, "session-123",
                    CombatAttackRequest(target_ref_id="enemy-123"),
                    "user-1", False,
                )
            self.assertIn("action", str(ctx.exception).lower())

    # ---- cast spell consumes action ----

    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_cast_spell_consumes_action(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update, mock_emit_player_state_update):
        self._make_active_state()

        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "spellcasting": {
                    "spells": [{"name": "Fire Bolt", "canonicalKey": "fire_bolt", "level": 0, "prepared": True}]
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
                with patch("app.services.combat.CombatService._get_stats", side_effect=[
                    (attacker_state, 10, 16, 14, 2, 0),
                    (MagicMock(), 12, 10, 10, 2, 0),
                ]):
                    with patch("random.randint", return_value=10):
                        await CombatService.cast_spell(
                            self.db, "session-123",
                            CombatCastSpellRequest(
                                target_ref_id="enemy-123",
                                spell_canonical_key="fire_bolt",
                                spell_mode="direct_damage",
                                damage_dice="1d10",
                                damage_type="fire",
                            ),
                            "user-1", False,
                        )

        self.assertTrue(self.state.participants[0]["turn_resources"]["action_used"])

    # ---- cannot cast twice ----

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_cannot_cast_twice_in_same_turn(self, mock_emit_log, mock_emit_state):
        self._make_active_state()
        self.state.participants[0]["turn_resources"]["action_used"] = True

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.cast_spell(
                    self.db, "session-123",
                    CombatCastSpellRequest(
                        target_ref_id="enemy-123",
                        spell_canonical_key="fire_bolt",
                        spell_mode="direct_damage",
                        damage_dice="1d10",
                        damage_type="fire",
                    ),
                    "user-1", False,
                )
            self.assertIn("action", str(ctx.exception).lower())

    # ---- GM bypass ----

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_gm_bypass_action_economy(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update):
        self._make_active_state()
        self.state.participants[0]["turn_resources"]["action_used"] = True

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(), 10, 16, 14, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0),
            ]):
                with patch("random.randint", return_value=15):
                    # GM can attack even with action used
                    res = await CombatService.attack(
                        self.db, "session-123",
                        CombatAttackRequest(target_ref_id="enemy-123"),
                        "user-1", True,
                    )
                    self.assertIn("roll", res)

    # ---- NPC entity_action consumes correct resource ----

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_entity_action_consumes_correct_resource(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update):
        self._make_active_state()
        self.state.current_turn_index = 1  # NPC's turn

        npc = SessionEntity(
            id="enemy-123",
            session_id="session-123",
            name="Goblin",
            campaign_entity_id="ce-1",
        )
        action = CombatAction(
            id="a1",
            name="Nimble Escape",
            kind="utility",
            actionCost="bonus_action",
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch(
                "app.services.combat.CombatService._get_combat_action_for_entity",
                return_value=("ce-1", npc, action),
            ):
                with patch(
                    "app.services.combat.CombatService._resolve_entity_combat_action",
                    return_value=action.model_dump(),
                ):
                    result = await CombatService.entity_action(
                        self.db, "session-123",
                        CombatEntityActionRequest(
                            actor_participant_id="e1",
                            combat_action_id="a1",
                        ),
                        "user-gm", True,
                    )

        self.assertTrue(self.state.participants[1]["turn_resources"]["bonus_action_used"])
        self.assertFalse(self.state.participants[1]["turn_resources"]["action_used"])

    # ---- consume reaction endpoint ----

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_consume_reaction_endpoint(self, mock_emit_log, mock_emit_state):
        self._make_active_state()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            await CombatService.consume_reaction(
                self.db, "session-123",
                CombatConsumeReactionRequest(participant_id="p1"),
                "user-gm",
                True,
            )

        self.assertTrue(self.state.participants[0]["turn_resources"]["reaction_used"])
        mock_emit_state.assert_called_once()
        mock_emit_log.assert_called_once()

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_player_can_consume_own_reaction(self, mock_emit_log, mock_emit_state):
        self._make_active_state()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            await CombatService.consume_reaction(
                self.db, "session-123",
                CombatConsumeReactionRequest(participant_id="p1"),
                "user-1",
                False,
            )

        self.assertTrue(self.state.participants[0]["turn_resources"]["reaction_used"])
        mock_emit_state.assert_called_once()
        mock_emit_log.assert_called_once()

    async def test_player_cannot_consume_other_participant_reaction(self):
        self._make_active_state()

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.consume_reaction(
                    self.db, "session-123",
                    CombatConsumeReactionRequest(participant_id="e1"),
                    "user-1",
                    False,
                )

        self.assertIn("own reaction", str(ctx.exception).lower())

    # ---- damage resolution does NOT consume ----

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_damage_resolution_does_not_consume(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update):
        self._make_active_state()
        # Set up a pending attack on p1
        self.state.participants[0]["pending_attack"] = {
            "id": "pa-1",
            "type": "player_attack",
            "target_ref_id": "enemy-123",
            "damage_dice": "1d8",
            "damage_bonus": 3,
            "damage_type": "slashing",
            "is_critical": False,
            "weapon_name": "Longsword",
            "attack_bonus": 5,
            "roll": 18,
            "target_ac": 15,
            "target_display_name": "Goblin",
            "target_kind": "session_entity",
        }
        # Mark action as used (from the attack that created the pending)
        self.state.participants[0]["turn_resources"]["action_used"] = True

        target_model = MagicMock()
        target_model.current_hp = 20
        target_model.max_hp = 20

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat.CombatService._get_stats", return_value=(
                target_model, 15, 10, 10, 2, 0,
            )):
                with patch("random.randint", return_value=5):
                    result = await CombatService.attack_damage(
                        self.db, "session-123",
                        CombatResolveDamageRequest(
                            pending_attack_id="pa-1",
                        ),
                        "user-1", False,
                    )

        # action_used should remain True — not consumed again
        self.assertTrue(self.state.participants[0]["turn_resources"]["action_used"])
        # bonus_action should still be unused
        self.assertFalse(self.state.participants[0]["turn_resources"]["bonus_action_used"])

    # ---- admin actions do NOT consume ----

    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_admin_actions_do_not_consume(self, mock_emit_log, mock_emit_state, mock_emit_entity_hp_update):
        self._make_active_state()

        target_model = MagicMock()
        target_model.current_hp = 20
        target_model.max_hp = 20

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with patch("app.services.combat.CombatService._get_stats", return_value=(
                target_model, 15, 10, 10, 2, 0,
            )):
                await CombatService.apply_damage(
                    self.db, "session-123",
                    CombatApplyDamageRequest(
                        target_ref_id="enemy-123",
                        amount=10,
                        kind="session_entity",
                    ),
                    "user-gm", True,
                )

        # Resources untouched
        self.assertFalse(self.state.participants[0]["turn_resources"]["action_used"])
        self.assertFalse(self.state.participants[0]["turn_resources"]["bonus_action_used"])
        self.assertFalse(self.state.participants[0]["turn_resources"]["reaction_used"])

    # ---- initiative transition resets first participant ----

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_initiative_transition_resets_first_participant(self, mock_emit_log, mock_emit_state):
        # Start in initiative phase
        self.state.phase = CombatPhase.initiative
        self.state.participants[0]["initiative"] = 15

        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            await CombatService.set_initiative(
                self.db, "session-123",
                CombatSetInitiativeRequest(
                    initiatives=[
                        CombatSetInitiativeParticipant(id="e1", initiative=10),
                    ]
                ),
            )

        # Should have transitioned to active
        self.assertEqual(self.state.phase, CombatPhase.active)
        # First participant (p1 with init 15) should have fresh resources
        first_p = self.state.participants[0]
        self.assertIn("turn_resources", first_p)
        self.assertFalse(first_p["turn_resources"]["action_used"])
        self.assertFalse(first_p["turn_resources"]["bonus_action_used"])
        self.assertFalse(first_p["turn_resources"]["reaction_used"])
