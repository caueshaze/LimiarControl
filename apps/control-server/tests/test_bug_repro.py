import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.routes.sessions.rolls.resolution import (
    AbilityRollRequest,
    roll_ability,
    roll_skill,
)
from app.models.campaign import RoleMode
from app.schemas.roll import RollActorStats, SkillRollRequest


class TestEnhanceAbilityAdvantageFromCombatStateParticipant(unittest.IsolatedAsyncioTestCase):
    """
    Reproduz o cenário real: efeito de Enhance Ability (Owl's Wisdom)
    está no participant do CombatState, não no SessionState.
    A rolagem de Wisdom deve aplicar vantagem automaticamente.
    """

    async def test_enhance_ability_advantage_from_combat_state_participant(self):
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
        session_entry.campaign_id = "campaign-1"
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
                "app.api.routes.sessions.rolls.resolution._get_session_and_member",
                return_value=(session_entry, member),
            ),
            patch(
                "app.api.routes.sessions.rolls.resolution._build_actor_stats",
            ) as mock_build,
            patch(
                "app.api.routes.sessions.rolls.resolution.CombatService.get_state",
                return_value=combat_state,
            ),
            patch(
                "app.api.routes.sessions.rolls.resolution._publish_and_log",
                new_callable=AsyncMock,
            ),
        ):
            mock_build.return_value = RollActorStats(
                display_name="Player 1",
                abilities={"wisdom": 10},
                actor_kind="player",
                actor_ref_id=user_id,
            )

            result = await roll_ability(
                session_id=session_id, body=body, user=user, db=db
            )

            self.assertEqual(result.advantage_mode, "advantage")
            self.assertIsInstance(result.check_modifier_sources, list)
            self.assertTrue(
                any(
                    s.get("source_label") == "Sabedoria da Coruja" and s.get("applied")
                    for s in result.check_modifier_sources
                )
            )

    async def test_enhance_ability_skill_advantage_from_combat_state_participant(self):
        """
        Perception (WIS skill) também deve receber vantagem de Owl's Wisdom.
        Athletics (STR skill) deve ser normal.
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
        session_entry.campaign_id = "campaign-1"
        session_entry.party_id = "party-1"
        session_entry.status = "ACTIVE"

        member = MagicMock()
        member.role_mode = RoleMode.GM
        member.id = "member-gm"
        member.user_id = user_id
        member.display_name = "GM"

        db = MagicMock()

        with (
            patch(
                "app.api.routes.sessions.rolls.resolution._get_session_and_member",
                return_value=(session_entry, member),
            ),
            patch(
                "app.api.routes.sessions.rolls.resolution._build_actor_stats",
            ) as mock_build,
            patch(
                "app.api.routes.sessions.rolls.resolution.CombatService.get_state",
                return_value=combat_state,
            ),
            patch(
                "app.api.routes.sessions.rolls.resolution._publish_and_log",
                new_callable=AsyncMock,
            ),
        ):
            mock_build.return_value = RollActorStats(
                display_name="Player 1",
                abilities={"wisdom": 10, "strength": 10},
                skills={"perception": 2, "athletics": 2},
                actor_kind="player",
                actor_ref_id=user_id,
            )

            # Perception (WIS) should have advantage
            perception_body = SkillRollRequest(
                actor_kind="player",
                actor_ref_id=user_id,
                skill="perception",
                advantage_mode="normal",
                roll_source="system",
            )
            result_perception = await roll_skill(
                session_id=session_id,
                body=perception_body,
                user=user,
                db=db,
            )
            self.assertEqual(result_perception.advantage_mode, "advantage")
            self.assertIsInstance(result_perception.check_modifier_sources, list)
            self.assertTrue(
                any(
                    s.get("source_label") == "Sabedoria da Coruja" and s.get("applied")
                    for s in result_perception.check_modifier_sources
                )
            )

            # Athletics (STR) should be normal
            athletics_body = SkillRollRequest(
                actor_kind="player",
                actor_ref_id=user_id,
                skill="athletics",
                advantage_mode="normal",
                roll_source="system",
            )
            result_athletics = await roll_skill(
                session_id=session_id,
                body=athletics_body,
                user=user,
                db=db,
            )
            self.assertEqual(result_athletics.advantage_mode, "normal")
            self.assertTrue(
                all(
                    s.get("ability") != "wisdom" or not s.get("applied")
                    for s in result_athletics.check_modifier_sources or []
                )
            )
