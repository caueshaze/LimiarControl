"""Phase 12 — combat action guards for incapacitated participants.

Tests that action-entry-points raise CombatServiceError when the actor has a
condition that blocks actions (incapacitated / paralyzed / stunned / unconscious).
"""
import unittest
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.schemas.combat import (
    CombatEntityActionRequest,
    CombatApplyEffectRequest,
    CombatStandardActionRequest,
)
from app.services.combat import CombatService, CombatServiceError


def _make_state(actor_condition: str | None = None) -> CombatState:
    effects = []
    if actor_condition:
        effects.append({"kind": "condition", "condition_type": actor_condition})

    return CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=[
            {
                "id": "p1",
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Hero",
                "initiative": 10,
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-1",
                "active_effects": effects,
                "turn_resources": {
                    "action_used": False,
                    "bonus_action_used": False,
                    "reaction_used": False,
                },
            },
            {
                "id": "e1",
                "ref_id": "entity-1",
                "kind": "session_entity",
                "display_name": "Goblin",
                "initiative": 5,
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
                "active_effects": effects,
                "turn_resources": {
                    "action_used": False,
                    "bonus_action_used": False,
                    "reaction_used": False,
                },
            },
        ],
    )


class TestStandardActionBlockedByCondition(unittest.IsolatedAsyncioTestCase):
    """standard_action should raise 403 for incapacitated actors."""

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_incapacitated_blocks_dodge(self, _log, _state):
        state = _make_state("incapacitated")
        with patch("app.services.combat.CombatService.get_state", return_value=state):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.standard_action(
                    MagicMock(),
                    "session-1",
                    CombatStandardActionRequest(action="dodge"),
                    actor_user_id="user-1",
                    is_gm=False,
                )
        self.assertIn("incapacitated", ctx.exception.args[0].lower())

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_paralyzed_blocks_dash(self, _log, _state):
        state = _make_state("paralyzed")
        with patch("app.services.combat.CombatService.get_state", return_value=state):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.standard_action(
                    MagicMock(),
                    "session-1",
                    CombatStandardActionRequest(action="dash"),
                    actor_user_id="user-1",
                    is_gm=False,
                )
        self.assertIn("incapacitated", ctx.exception.args[0].lower())

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_stunned_blocks_standard_action(self, _log, _state):
        state = _make_state("stunned")
        with patch("app.services.combat.CombatService.get_state", return_value=state):
            with self.assertRaises(CombatServiceError):
                await CombatService.standard_action(
                    MagicMock(),
                    "session-1",
                    CombatStandardActionRequest(action="hide"),
                    actor_user_id="user-1",
                    is_gm=False,
                )

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_no_condition_does_not_block(self, _log, _state):
        """Prone actor should NOT be blocked from standard actions (dodge succeeds)."""
        state = _make_state("prone")
        with patch("app.services.combat.CombatService.get_state", return_value=state):
            try:
                result = await CombatService.standard_action(
                    MagicMock(),
                    "session-1",
                    CombatStandardActionRequest(action="dodge"),
                    actor_user_id="user-1",
                    is_gm=False,
                )
                # If it succeeds, the condition guard definitely did not block it
            except CombatServiceError as exc:
                # The error must NOT be the incapacitation guard
                self.assertNotIn(
                    "incapacitated",
                    exc.args[0].lower(),
                    f"Prone actor should not be blocked by incapacitation guard, got: {exc.args[0]}",
                )


class TestNpcActionBlockedByCondition(unittest.IsolatedAsyncioTestCase):
    """entity_action should raise 403 for incapacitated NPCs."""

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_incapacitated_npc_cannot_act(self, _log, _state):
        state = _make_state("incapacitated")
        # Make the NPC the current actor (index 1)
        state.current_turn_index = 1
        with patch("app.services.combat.CombatService.get_state", return_value=state):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.entity_action(
                    MagicMock(),
                    "session-1",
                    CombatEntityActionRequest(combat_action_id="atk-1"),
                    actor_user_id="gm-user",
                    is_gm=True,
                )
        self.assertIn("incapacitated", ctx.exception.args[0].lower())

    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_log")
    async def test_unconscious_npc_cannot_act(self, _log, _state):
        state = _make_state("unconscious")
        state.current_turn_index = 1
        with patch("app.services.combat.CombatService.get_state", return_value=state):
            with self.assertRaises(CombatServiceError):
                await CombatService.entity_action(
                    MagicMock(),
                    "session-1",
                    CombatEntityActionRequest(combat_action_id="atk-1"),
                    actor_user_id="gm-user",
                    is_gm=True,
                )


class TestRequireActionCapableHelper(unittest.TestCase):
    """Unit test the _require_action_capable core helper directly."""

    def test_no_effects_passes(self):
        p = {"active_effects": []}
        CombatService._require_action_capable(p)  # must not raise

    def test_non_condition_effect_passes(self):
        p = {"active_effects": [{"kind": "temp_ac_bonus", "numeric_value": 2}]}
        CombatService._require_action_capable(p)  # must not raise

    def test_poisoned_passes(self):
        p = {"active_effects": [{"kind": "condition", "condition_type": "poisoned"}]}
        CombatService._require_action_capable(p)  # poisoned doesn't block actions

    def test_incapacitated_raises(self):
        p = {"active_effects": [{"kind": "condition", "condition_type": "incapacitated"}]}
        with self.assertRaises(CombatServiceError):
            CombatService._require_action_capable(p)

    def test_stunned_raises(self):
        p = {"active_effects": [{"kind": "condition", "condition_type": "stunned"}]}
        with self.assertRaises(CombatServiceError):
            CombatService._require_action_capable(p)


class TestRequireMovementCapableHelper(unittest.TestCase):
    """Unit test the _require_movement_capable core helper directly."""

    def test_no_effects_passes(self):
        p = {"active_effects": []}
        CombatService._require_movement_capable(p)  # must not raise

    def test_prone_passes(self):
        p = {"active_effects": [{"kind": "condition", "condition_type": "prone"}]}
        CombatService._require_movement_capable(p)  # prone only halves speed, doesn't block

    def test_blinded_passes(self):
        p = {"active_effects": [{"kind": "condition", "condition_type": "blinded"}]}
        CombatService._require_movement_capable(p)  # blinded doesn't block movement

    def test_restrained_raises(self):
        p = {"active_effects": [{"kind": "condition", "condition_type": "restrained"}]}
        with self.assertRaises(CombatServiceError):
            CombatService._require_movement_capable(p)

    def test_grappled_raises(self):
        p = {"active_effects": [{"kind": "condition", "condition_type": "grappled"}]}
        with self.assertRaises(CombatServiceError):
            CombatService._require_movement_capable(p)

    def test_incapacitated_raises(self):
        p = {"active_effects": [{"kind": "condition", "condition_type": "incapacitated"}]}
        with self.assertRaises(CombatServiceError):
            CombatService._require_movement_capable(p)


if __name__ == "__main__":
    unittest.main()
