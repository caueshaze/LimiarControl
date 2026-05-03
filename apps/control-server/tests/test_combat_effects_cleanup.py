import unittest
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService


class TestEndCombatClearsEffects(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = MagicMock()

    async def test_end_combat_clears_all_active_effects(self):
        effect_owls_wisdom = {
            "id": "eff-1",
            "kind": "spell_effect",
            "source_participant_id": "p1",
            "condition_type": None,
            "numeric_value": None,
            "duration_type": "manual",
            "remaining_rounds": None,
            "expires_on": None,
            "expires_at_participant_id": None,
            "created_at": "2025-01-01T00:00:00Z",
            "metadata": {
                "concentration": True,
                "concentration_group": "cg-1",
                "declarative_effect": {
                    "type": "passive_skill_bonus",
                    "params": {"skill": "perception", "bonus": 5},
                },
                "source_spell_name": "Owl's Wisdom",
                "source_spell_key": "enhance_ability",
            },
            "display_label": "Owl's Wisdom",
        }
        effect_advantage = {
            "id": "eff-2",
            "kind": "spell_effect",
            "source_participant_id": "p1",
            "condition_type": None,
            "numeric_value": None,
            "duration_type": "manual",
            "remaining_rounds": None,
            "expires_on": None,
            "expires_at_participant_id": None,
            "created_at": "2025-01-01T00:00:00Z",
            "metadata": {
                "concentration": True,
                "concentration_group": "cg-1",
                "declarative_effect": {
                    "type": "advantage_on_checks",
                    "params": {"ability": "wisdom", "against": "any"},
                },
                "source_spell_name": "Owl's Wisdom",
                "source_spell_key": "enhance_ability",
            },
            "display_label": "Owl's Wisdom",
        }
        effect_manual = {
            "id": "eff-3",
            "kind": "condition",
            "source_participant_id": None,
            "condition_type": "prone",
            "numeric_value": None,
            "duration_type": "manual",
            "remaining_rounds": None,
            "expires_on": None,
            "expires_at_participant_id": None,
            "created_at": "2025-01-01T00:00:00Z",
            "metadata": None,
            "display_label": "Prone",
        }

        state = CombatState(
            id="combat-1",
            session_id="session-1",
            phase=CombatPhase.active,
            round=3,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "player-1",
                    "kind": "player",
                    "display_name": "Hero",
                    "initiative": 15,
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "user-1",
                    "active_effects": [effect_owls_wisdom, effect_advantage, effect_manual],
                    "turn_resources": {
                        "action_used": True,
                        "bonus_action_used": False,
                        "reaction_used": False,
                    },
                    "pending_save": {"id": "ps-1", "status": "pending"},
                    "pending_attack": {"id": "pa-1", "damage_dice": "2d6"},
                },
                {
                    "id": "e1",
                    "ref_id": "enemy-1",
                    "kind": "session_entity",
                    "display_name": "Goblin",
                    "initiative": 10,
                    "status": "active",
                    "team": "enemies",
                    "visible": True,
                    "actor_user_id": None,
                    "active_effects": [effect_owls_wisdom.copy()],
                    "turn_resources": {
                        "action_used": False,
                        "bonus_action_used": False,
                        "reaction_used": True,
                    },
                },
            ],
        )
        state.active_area_effects = []

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._emit_state", new_callable=unittest.mock.AsyncMock),
            patch("app.services.combat.CombatService._emit_log", new_callable=unittest.mock.AsyncMock),
        ):
            result = await CombatService.end_combat(self.db, "session-1", is_gm=True)

        self.assertEqual(result.phase, CombatPhase.ended)
        self.assertEqual(result.active_area_effects, [])

        for participant in result.participants:
            self.assertEqual(
                participant.get("active_effects", []),
                [],
                f"Participant {participant['id']} should have no active_effects after end_combat, "
                f"but got {participant.get('active_effects')}",
            )
            self.assertIsNone(
                participant.get("pending_save"),
                f"Participant {participant['id']} should have no pending_save after end_combat",
            )
            self.assertIsNone(
                participant.get("pending_attack"),
                f"Participant {participant['id']} should have no pending_attack after end_combat",
            )
            turn_resources = participant.get("turn_resources", {})
            self.assertFalse(turn_resources.get("action_used", False))
            self.assertFalse(turn_resources.get("bonus_action_used", False))
            self.assertFalse(turn_resources.get("reaction_used", False))

    async def test_end_combat_clears_area_effects(self):
        state = CombatState(
            id="combat-2",
            session_id="session-2",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "player-1",
                    "kind": "player",
                    "display_name": "Hero",
                    "initiative": 15,
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "user-1",
                    "active_effects": [],
                },
            ],
        )
        state.active_area_effects = [
            {
                "id": "area-1",
                "source_spell_name": "Fog Cloud",
                "caster_participant_id": "p1",
                "concentration_group": "cg-fog",
            },
        ]

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._emit_state", new_callable=unittest.mock.AsyncMock),
            patch("app.services.combat.CombatService._emit_log", new_callable=unittest.mock.AsyncMock),
        ):
            result = await CombatService.end_combat(self.db, "session-2", is_gm=True)

        self.assertEqual(result.active_area_effects, [])

    async def test_end_combat_clears_manual_non_concentration_effects(self):
        manual_effect = {
            "id": "eff-manual",
            "kind": "condition",
            "source_participant_id": None,
            "condition_type": "prone",
            "numeric_value": None,
            "duration_type": "manual",
            "remaining_rounds": None,
            "expires_on": None,
            "expires_at_participant_id": None,
            "created_at": "2025-01-01T00:00:00Z",
            "metadata": None,
            "display_label": "Prone",
        }

        state = CombatState(
            id="combat-3",
            session_id="session-3",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "player-1",
                    "kind": "player",
                    "display_name": "Hero",
                    "initiative": 15,
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "user-1",
                    "active_effects": [manual_effect],
                },
            ],
        )
        state.active_area_effects = []

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._emit_state", new_callable=unittest.mock.AsyncMock),
            patch("app.services.combat.CombatService._emit_log", new_callable=unittest.mock.AsyncMock),
        ):
            result = await CombatService.end_combat(self.db, "session-3", is_gm=True)

        self.assertEqual(result.participants[0].get("active_effects", []), [])


class TestEndedCombatNoAdvantage(unittest.TestCase):
    def test_ended_combat_advantage_mode_returns_normal(self):
        from app.services.combat_service.condition_effects_predicates import resolve_check_advantage_mode

        participant = {
            "id": "p1",
            "kind": "player",
            "ref_id": "user-1",
            "active_effects": [
                {
                    "id": "eff-1",
                    "kind": "spell_effect",
                    "metadata": {
                        "concentration": True,
                        "concentration_group": "cg-1",
                        "declarative_effect": {
                            "type": "advantage_on_checks",
                            "params": {"ability": "wisdom", "against": "any"},
                        },
                        "source_spell_name": "Owl's Wisdom",
                        "source_spell_key": "enhance_ability",
                    },
                },
            ],
        }

        result = resolve_check_advantage_mode(
            participant,
            "wisdom",
            manual_mode="normal",
        )
        self.assertEqual(result, "advantage")

    def test_resolve_check_advantage_mode_with_no_effects_returns_normal(self):
        from app.services.combat_service.condition_effects_predicates import resolve_check_advantage_mode

        participant = {
            "id": "p1",
            "kind": "player",
            "ref_id": "user-1",
            "active_effects": [],
        }

        result = resolve_check_advantage_mode(
            participant,
            "wisdom",
            manual_mode="normal",
        )
        self.assertEqual(result, "normal")

    @patch("app.services.combat.CombatService.get_state")
    def test_resolve_check_advantage_for_actor_returns_normal_on_ended_combat(self, mock_get_state):
        from app.models.combat import CombatPhase

        ended_state = CombatState(
            id="combat-ended",
            session_id="session-1",
            phase=CombatPhase.ended,
            round=5,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "kind": "player",
                    "ref_id": "user-1",
                    "display_name": "Hero",
                    "active_effects": [
                        {
                            "id": "eff-1",
                            "kind": "spell_effect",
                            "metadata": {
                                "concentration": True,
                                "concentration_group": "cg-1",
                                "declarative_effect": {
                                    "type": "advantage_on_checks",
                                    "params": {"ability": "wisdom", "against": "any"},
                                },
                                "source_spell_name": "Owl's Wisdom",
                            },
                        },
                    ],
                },
            ],
        )
        mock_get_state.return_value = ended_state

        result = CombatService._resolve_check_advantage_mode_for_actor(
            MagicMock(),
            "session-1",
            actor_kind="player",
            actor_ref_id="user-1",
            ability="wisdom",
            manual_mode="normal",
        )
        self.assertEqual(result, "normal")

    @patch("app.services.combat.CombatService.get_state")
    def test_explain_check_modifier_sources_returns_empty_on_ended_combat(self, mock_get_state):
        from app.models.combat import CombatPhase

        ended_state = CombatState(
            id="combat-ended",
            session_id="session-1",
            phase=CombatPhase.ended,
            round=5,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "kind": "player",
                    "ref_id": "user-1",
                    "display_name": "Hero",
                    "active_effects": [
                        {
                            "id": "eff-1",
                            "kind": "spell_effect",
                            "metadata": {
                                "concentration": True,
                                "concentration_group": "cg-1",
                                "declarative_effect": {
                                    "type": "advantage_on_checks",
                                    "params": {"ability": "wisdom", "against": "any"},
                                },
                                "source_spell_name": "Owl's Wisdom",
                            },
                        },
                    ],
                },
            ],
        )
        mock_get_state.return_value = ended_state

        result = CombatService._explain_check_modifier_sources_for_actor(
            MagicMock(),
            "session-1",
            actor_kind="player",
            actor_ref_id="user-1",
            ability="wisdom",
            roll_type="ability",
        )
        self.assertEqual(result, [])


class TestEndCombatPreservesNewCombat(unittest.IsolatedAsyncioTestCase):
    async def test_new_combat_starts_without_inherited_effects(self):
        db = MagicMock()
        db.delete = MagicMock()
        db.flush = MagicMock()

        with (
            patch("app.services.combat.CombatService.get_state", return_value=None),
            patch("app.services.combat.CombatService._emit_state", new_callable=unittest.mock.AsyncMock),
            patch("app.services.combat.CombatService._emit_log", new_callable=unittest.mock.AsyncMock),
            patch("app.services.combat.CombatService._sync_all_participant_statuses"),
            patch("app.services.combat.CombatService._resolve_map_selection", return_value={}),
        ):
            from app.schemas.combat import CombatParticipant, CombatStartRequest

            req = CombatStartRequest(
                participants=[
                    CombatParticipant(
                        id="p1",
                        ref_id="player-1",
                        kind="player",
                        display_name="Hero",
                        team="players",
                        visible=True,
                        actor_user_id="user-1",
                    ),
                ]
            )
            result = await CombatService.start_combat(db, "session-1", req)

        for participant in result.participants:
            self.assertEqual(participant.get("active_effects", []), [])


if __name__ == "__main__":
    unittest.main()