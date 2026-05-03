import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.routes.sessions.rolls_resolution import (
    AbilityRollRequest,
    roll_ability,
)
from app.models.campaign import RoleMode
from app.schemas.roll import RollActorStats


class TestEnhanceAbilityBugRepro(unittest.IsolatedAsyncioTestCase):
    async def test_repro_bug_with_effect_on_combat_state_participant(self):
        """
        O efeito de Enhance Ability deve estar no participant do CombatState.
        O backend NÃO lê active_effects do SessionState para resolver rolagens.
        """
        session_id = "test-session"
        user_id = "user-123"

        effect = {
            "id": "effect-1",
            "kind": "spell_effect",
            "metadata": {
                "source_spell_name": "Sabedoria da Coruja",
                "declarative_effect": {
                    "type": "advantage_on_checks",
                    "params": {"ability": "wisdom", "against": "any"},
                },
            },
        }

        combat_state = MagicMock()
        combat_state.participants = [
            {
                "id": "p1",
                "kind": "player",
                "ref_id": user_id,
                "actor_user_id": user_id,
                "display_name": "Player 1",
                "status": "active",
                "active_effects": [effect],
            }
        ]

        user = MagicMock()
        user.id = user_id

        session_entry = MagicMock()
        session_entry.id = session_id
        session_entry.campaign_id = "camp-1"
        session_entry.party_id = "party-1"
        session_entry.status = "ACTIVE"

        member = MagicMock()
        member.role_mode = RoleMode.GM
        member.id = "member-gm"
        member.user_id = user_id
        member.display_name = "GM"

        db = MagicMock()

        body = AbilityRollRequest(
            actor_kind="player",
            actor_ref_id=user_id,
            ability="wisdom",
            advantage_mode="normal",
            roll_source="system",
        )

        with (
            patch(
                "app.api.routes.sessions.rolls_resolution._get_session_and_member",
                return_value=(session_entry, member),
            ),
            patch(
                "app.api.routes.sessions.rolls_resolution._build_actor_stats",
                return_value=RollActorStats(
                    display_name="Player 1",
                    abilities={"wisdom": 10},
                    actor_kind="player",
                    actor_ref_id=user_id,
                ),
            ),
            patch(
                "app.api.routes.sessions.rolls_resolution.CombatService.get_state",
                return_value=combat_state,
            ),
            patch(
                "app.api.routes.sessions.rolls_resolution._publish_and_log",
                new_callable=AsyncMock,
            ),
        ):
            result = await roll_ability(
                session_id=session_id, body=body, user=user, db=db
            )

            self.assertEqual(
                result.advantage_mode,
                "advantage",
                "Should have advantage from CombatState participant active_effects",
            )
            self.assertIsInstance(result.check_modifier_sources, list)
            self.assertTrue(
                any(
                    s.get("source_label") == "Sabedoria da Coruja" and s.get("applied")
                    for s in result.check_modifier_sources
                ),
                "Effect source should be present and applied",
            )


if __name__ == "__main__":
    unittest.main()
