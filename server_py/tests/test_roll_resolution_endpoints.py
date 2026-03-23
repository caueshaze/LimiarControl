"""Integration tests for roll resolution endpoints — auth, realtime, activity."""

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.campaign import RoleMode
from app.api.routes.sessions.rolls_resolution import (
    _authorize_roll,
    _build_player_stats,
    _build_entity_stats,
)


def _make_member(role_mode=RoleMode.GM, user_id="user-1", member_id="member-1"):
    m = MagicMock()
    m.role_mode = role_mode
    m.id = member_id
    m.user_id = user_id
    m.display_name = "TestUser"
    return m


class TestAuthorizeRoll(unittest.TestCase):
    def test_gm_can_roll_for_player(self):
        member = _make_member(RoleMode.GM)
        result = _authorize_roll(member, "player", "other-user", "user-1")
        self.assertTrue(result)  # is_gm = True

    def test_gm_can_roll_for_entity(self):
        member = _make_member(RoleMode.GM)
        result = _authorize_roll(member, "session_entity", "se-1", "user-1")
        self.assertTrue(result)

    def test_player_can_roll_for_self(self):
        member = _make_member(RoleMode.PLAYER, user_id="user-1")
        result = _authorize_roll(member, "player", "user-1", "user-1")
        self.assertFalse(result)  # is_gm = False

    def test_player_cannot_roll_for_other_player(self):
        member = _make_member(RoleMode.PLAYER, user_id="user-1")
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            _authorize_roll(member, "player", "user-2", "user-1")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_player_cannot_roll_for_entity(self):
        member = _make_member(RoleMode.PLAYER, user_id="user-1")
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            _authorize_roll(member, "session_entity", "se-1", "user-1")
        self.assertEqual(ctx.exception.status_code, 403)


class TestBuildPlayerStats(unittest.TestCase):
    def test_builds_stats_from_session_state(self):
        state = MagicMock()
        state.state_json = {
            "characterName": "Hero",
            "abilities": {
                "strength": 16,
                "dexterity": 14,
                "constitution": 12,
                "intelligence": 10,
                "wisdom": 13,
                "charisma": 8,
            },
            "level": 5,
            "savingThrows": {"strength": 5},
            "skills": {"athletics": 5},
        }

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.first.return_value = state
        db.exec.return_value = result_mock

        stats = _build_player_stats(db, "session-1", "user-1")
        self.assertEqual(stats.display_name, "Hero")
        self.assertEqual(stats.abilities["strength"], 16)
        self.assertEqual(stats.proficiency_bonus, 3)  # level 5: floor((5-1)/4)+2 = 3
        self.assertEqual(stats.saving_throws, {"strength": 5})
        self.assertEqual(stats.skills, {"athletics": 5})
        self.assertEqual(stats.actor_kind, "player")

    def test_raises_404_when_state_not_found(self):
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.first.return_value = None
        db.exec.return_value = result_mock

        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            _build_player_stats(db, "session-1", "user-1")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_handles_missing_optional_fields(self):
        state = MagicMock()
        state.state_json = {
            "abilities": {"strength": 10, "dexterity": 10, "constitution": 10,
                         "intelligence": 10, "wisdom": 10, "charisma": 10},
        }

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.first.return_value = state
        db.exec.return_value = result_mock

        stats = _build_player_stats(db, "session-1", "user-1")
        self.assertEqual(stats.display_name, "Player")
        self.assertIsNone(stats.saving_throws)
        self.assertIsNone(stats.skills)
        self.assertEqual(stats.proficiency_bonus, 2)  # default level 1


class TestBuildEntityStats(unittest.TestCase):
    def test_builds_stats_from_session_entity_and_campaign_entity(self):
        se = MagicMock()
        se.campaign_entity_id = "ce-1"
        se.label = "Goblin A"
        se.overrides = {"abilities": {"strength": 20}}

        ce = MagicMock()
        ce.name = "Goblin"
        ce.abilities = {
            "strength": 8, "dexterity": 14, "constitution": 10,
            "intelligence": 10, "wisdom": 8, "charisma": 8,
        }
        ce.saving_throws = {"dexterity": 4}
        ce.skills = {"stealth": 6}
        ce.initiative_bonus = 3

        db = MagicMock()
        # First call returns SessionEntity, second returns CampaignEntity
        result1 = MagicMock()
        result1.first.return_value = se
        result2 = MagicMock()
        result2.first.return_value = ce
        db.exec.side_effect = [result1, result2]

        stats = _build_entity_stats(db, "se-1")
        self.assertEqual(stats.display_name, "Goblin A")
        self.assertEqual(stats.abilities["strength"], 20)  # override applied
        self.assertEqual(stats.abilities["dexterity"], 14)  # original kept
        self.assertEqual(stats.saving_throws, {"dexterity": 4})
        self.assertEqual(stats.skills, {"stealth": 6})
        self.assertEqual(stats.initiative_bonus, 3)
        self.assertEqual(stats.actor_kind, "session_entity")


class TestEndToEndRoll(unittest.IsolatedAsyncioTestCase):
    """Test the full endpoint flow with mocked dependencies."""

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(15, 8))
    async def test_ability_roll_publishes_event(self, _mock_d20):
        from app.api.routes.sessions.rolls_resolution import roll_ability
        from app.schemas.roll import AbilityRollRequest

        # Mock dependencies
        user = MagicMock()
        user.id = "user-1"

        session_entry = MagicMock()
        session_entry.id = "session-1"
        session_entry.campaign_id = "campaign-1"
        session_entry.party_id = "party-1"
        session_entry.status = "ACTIVE"

        member = _make_member(RoleMode.PLAYER, user_id="user-1")

        state = MagicMock()
        state.state_json = {
            "characterName": "Hero",
            "abilities": {
                "strength": 16, "dexterity": 14, "constitution": 12,
                "intelligence": 10, "wisdom": 13, "charisma": 8,
            },
            "level": 1,
        }

        db = MagicMock()

        body = AbilityRollRequest(
            actor_kind="player",
            actor_ref_id="user-1",
            ability="strength",
            advantage_mode="normal",
            dc=15,
        )

        with patch(
            "app.api.routes.sessions.rolls_resolution._get_session_and_member",
            return_value=(session_entry, member),
        ), patch(
            "app.api.routes.sessions.rolls_resolution._build_actor_stats",
        ) as mock_build, patch(
            "app.api.routes.sessions.rolls_resolution._publish_and_log",
            new_callable=AsyncMock,
        ) as mock_publish:
            from app.schemas.roll import RollActorStats
            mock_build.return_value = RollActorStats(
                display_name="Hero",
                abilities=state.state_json["abilities"],
                actor_kind="player",
                actor_ref_id="user-1",
            )

            result = await roll_ability(session_id="session-1", body=body, user=user, db=db)

            self.assertEqual(result.roll_type, "ability")
            self.assertEqual(result.total, 18)  # 15 + 3 (STR mod)
            self.assertTrue(result.success)  # 18 >= 15
            self.assertFalse(result.is_gm_roll)
            mock_publish.assert_called_once()

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(14, 5))
    async def test_initiative_roll_updates_combat_state(self, _mock_d20):
        from app.api.routes.sessions.rolls_resolution import roll_initiative
        from app.schemas.roll import InitiativeRollRequest, RollActorStats

        user = MagicMock()
        user.id = "user-1"

        session_entry = MagicMock()
        session_entry.id = "session-1"
        session_entry.campaign_id = "campaign-1"
        session_entry.party_id = "party-1"
        session_entry.status = "ACTIVE"

        member = _make_member(RoleMode.PLAYER, user_id="user-1")

        db = MagicMock()

        body = InitiativeRollRequest(
            actor_kind="player",
            actor_ref_id="user-1",
            advantage_mode="normal",
        )

        with patch(
            "app.api.routes.sessions.rolls_resolution._get_session_and_member",
            return_value=(session_entry, member),
        ), patch(
            "app.api.routes.sessions.rolls_resolution._build_actor_stats",
        ) as mock_build, patch(
            "app.api.routes.sessions.rolls_resolution._publish_and_log",
            new_callable=AsyncMock,
        ) as mock_publish, patch(
            "app.api.routes.sessions.rolls_resolution.CombatService.apply_initiative_roll",
            new_callable=AsyncMock,
        ) as mock_apply_initiative:
            mock_build.return_value = RollActorStats(
                display_name="Hero",
                abilities={"dexterity": 14},
                actor_kind="player",
                actor_ref_id="user-1",
            )

            result = await roll_initiative(session_id="session-1", body=body, user=user, db=db)

            self.assertEqual(result.roll_type, "initiative")
            self.assertEqual(result.total, 16)
            mock_publish.assert_called_once()
            mock_apply_initiative.assert_awaited_once_with(
                db,
                "session-1",
                "player",
                "user-1",
                16,
            )


if __name__ == "__main__":
    unittest.main()
