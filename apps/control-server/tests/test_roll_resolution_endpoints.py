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
from app.api.routes.sessions.activity import get_session_activity
from app.services.combat_service.condition_effects_predicates import resolve_actor_participant
from app.services.combat import CombatService


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
            "savingThrowProficiencies": {"strength": True},
            "skillProficiencies": {"athletics": 1},
        }

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.first.return_value = state
        db.exec.return_value = result_mock

        stats = _build_player_stats(db, "session-1", "user-1")
        self.assertEqual(stats.display_name, "Hero")
        self.assertEqual(stats.abilities["strength"], 16)
        self.assertEqual(stats.proficiency_bonus, 3)
        self.assertEqual(stats.saving_throws["strength"], 6)
        self.assertEqual(stats.saving_throws["dexterity"], 2)
        self.assertEqual(stats.skills["athletics"], 6)
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
            "abilities": {
                "strength": 10,
                "dexterity": 10,
                "constitution": 10,
                "intelligence": 10,
                "wisdom": 10,
                "charisma": 10,
            },
        }

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.first.return_value = state
        db.exec.return_value = result_mock

        stats = _build_player_stats(db, "session-1", "user-1")
        self.assertEqual(stats.display_name, "Player")
        self.assertIsNotNone(stats.saving_throws)
        self.assertEqual(stats.saving_throws["strength"], 0)
        self.assertIsNotNone(stats.skills)
        self.assertEqual(stats.proficiency_bonus, 2)


class TestBuildEntityStats(unittest.TestCase):
    def test_builds_stats_from_session_entity_and_campaign_entity(self):
        se = MagicMock()
        se.campaign_entity_id = "ce-1"
        se.label = "Goblin A"
        se.overrides = {"abilities": {"strength": 20}}

        ce = MagicMock()
        ce.name = "Goblin"
        ce.abilities = {
            "strength": 8,
            "dexterity": 14,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 8,
            "charisma": 8,
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


class TestContextualCheckAdvantageLookup(unittest.TestCase):
    def _make_state(self, effects, *, ref_id="player-123", actor_user_id="user-1", character_id=None):
        state = MagicMock()
        participant = {
            "id": "participant-1",
            "ref_id": ref_id,
            "kind": "player",
            "display_name": "Hero",
            "actor_user_id": actor_user_id,
            "active_effects": effects,
        }
        if character_id is not None:
            participant["character_id"] = character_id
        state.participants = [participant]
        return state

    def _owls_wisdom_effect(self):
        return [
            {
                "kind": "spell_effect",
                "metadata": {
                    "source_spell_name": "Sabedoria da Coruja",
                    "declarative_effect": {
                        "type": "advantage_on_checks",
                        "params": {"ability": "wisdom", "against": "any"},
                    },
                },
            }
        ]

    def _passive_perception_effect(self):
        return [
            {
                "kind": "spell_effect",
                "metadata": {
                    "source_spell_name": "Sabedoria da Coruja",
                    "declarative_effect": {
                        "type": "passive_skill_bonus",
                        "params": {"skill": "perception", "bonus": 5},
                    },
                },
            }
        ]

    def test_resolve_actor_participant_prefers_ref_id_actor_user_id_then_character_id(self):
        state = self._make_state([], ref_id="combat-ref", character_id="char-9")

        found = resolve_actor_participant(state, "combat-ref")
        self.assertIsNotNone(found)
        self.assertEqual(found["ref_id"], "combat-ref")

        found = resolve_actor_participant(state, "user-1")
        self.assertIsNotNone(found)
        self.assertEqual(found["actor_user_id"], "user-1")

        found = resolve_actor_participant(state, "char-9")
        self.assertIsNotNone(found)
        self.assertEqual(found["character_id"], "char-9")

    @patch("app.services.combat_service.service.CombatService.get_state")
    def test_wisdom_ability_uses_actor_user_id_and_applies_advantage(self, mock_get_state):
        mock_get_state.return_value = self._make_state(self._owls_wisdom_effect())

        mode = CombatService._resolve_check_advantage_mode_for_actor(
            MagicMock(),
            "session-1",
            actor_kind="player",
            actor_ref_id="user-1",
            ability="wisdom",
        )

        self.assertEqual(mode, "advantage")

    @patch("app.services.combat_service.service.CombatService.get_state")
    def test_manual_disadvantage_cancels_wisdom_advantage(self, mock_get_state):
        mock_get_state.return_value = self._make_state(self._owls_wisdom_effect())

        mode = CombatService._resolve_check_advantage_mode_for_actor(
            MagicMock(),
            "session-1",
            actor_kind="player",
            actor_ref_id="user-1",
            ability="wisdom",
            manual_mode="disadvantage",
        )

        self.assertEqual(mode, "normal")

    @patch("app.services.combat_service.service.CombatService.get_state")
    def test_wisdom_skill_uses_same_effect(self, mock_get_state):
        mock_get_state.return_value = self._make_state(self._owls_wisdom_effect())

        mode = CombatService._resolve_skill_check_advantage_mode_for_actor(
            MagicMock(),
            "session-1",
            actor_kind="player",
            actor_ref_id="user-1",
            skill="perception",
        )

        self.assertEqual(mode, "advantage")

    @patch("app.services.combat_service.service.CombatService.get_state")
    def test_unrelated_skill_is_not_affected(self, mock_get_state):
        mock_get_state.return_value = self._make_state(self._owls_wisdom_effect())

        mode = CombatService._resolve_skill_check_advantage_mode_for_actor(
            MagicMock(),
            "session-1",
            actor_kind="player",
            actor_ref_id="user-1",
            skill="athletics",
        )

        self.assertEqual(mode, "normal")

    @patch("app.services.combat_service.service.CombatService.get_state")
    def test_removing_effect_clears_advantage(self, mock_get_state):
        mock_get_state.return_value = self._make_state([])

        mode = CombatService._resolve_check_advantage_mode_for_actor(
            MagicMock(),
            "session-1",
            actor_kind="player",
            actor_ref_id="user-1",
            ability="wisdom",
        )

        self.assertEqual(mode, "normal")

    @patch("app.services.combat_service.service.CombatService.get_state")
    def test_passive_bonus_effect_does_not_count_as_active_check_bonus(self, mock_get_state):
        mock_get_state.return_value = self._make_state(self._passive_perception_effect())

        mode = CombatService._resolve_skill_check_advantage_mode_for_actor(
            MagicMock(),
            "session-1",
            actor_kind="player",
            actor_ref_id="user-1",
            skill="perception",
        )

        self.assertEqual(mode, "normal")


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
                "strength": 16,
                "dexterity": 14,
                "constitution": 12,
                "intelligence": 10,
                "wisdom": 13,
                "charisma": 8,
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

        with (
            patch(
                "app.api.routes.sessions.rolls_resolution._get_session_and_member",
                return_value=(session_entry, member),
            ),
            patch(
                "app.api.routes.sessions.rolls_resolution._build_actor_stats",
            ) as mock_build,
            patch(
                "app.api.routes.sessions.rolls_resolution._publish_and_log",
                new_callable=AsyncMock,
            ) as mock_publish,
        ):
            from app.schemas.roll import RollActorStats

            mock_build.return_value = RollActorStats(
                display_name="Hero",
                abilities=state.state_json["abilities"],
                actor_kind="player",
                actor_ref_id="user-1",
            )

            result = await roll_ability(
                session_id="session-1", body=body, user=user, db=db
            )

            self.assertEqual(result.roll_type, "ability")
            self.assertEqual(result.total, 18)  # 15 + 3 (STR mod)
            self.assertTrue(result.success)  # 18 >= 15
            self.assertFalse(result.is_gm_roll)
            mock_publish.assert_called_once()

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(10, 14))
    async def test_ability_roll_attaches_check_modifier_sources(self, _mock_d20):
        from app.api.routes.sessions.rolls_resolution import roll_ability
        from app.schemas.roll import AbilityRollRequest, RollActorStats

        user = MagicMock()
        user.id = "user-1"

        session_entry = MagicMock()
        session_entry.id = "session-1"
        session_entry.campaign_id = "campaign-1"
        session_entry.party_id = "party-1"
        session_entry.status = "ACTIVE"

        member = _make_member(RoleMode.PLAYER, user_id="user-1")

        state = MagicMock()
        state.participants = [
            {
                "id": "participant-1",
                "ref_id": "player-123",
                "kind": "player",
                "display_name": "Hero",
                "actor_user_id": "user-1",
                "active_effects": [
                    {
                        "kind": "spell_effect",
                        "metadata": {
                            "source_spell_name": "Sabedoria da Coruja",
                            "declarative_effect": {
                                "type": "advantage_on_checks",
                                "params": {"ability": "wisdom", "against": "any"},
                            },
                        },
                    }
                ],
            }
        ]

        db = MagicMock()
        body = AbilityRollRequest(
            actor_kind="player",
            actor_ref_id="user-1",
            ability="wisdom",
            advantage_mode="normal",
            dc=10,
        )

        with (
            patch(
                "app.api.routes.sessions.rolls_resolution._get_session_and_member",
                return_value=(session_entry, member),
            ),
            patch(
                "app.api.routes.sessions.rolls_resolution._build_actor_stats",
            ) as mock_build,
            patch(
                "app.api.routes.sessions.rolls_resolution.CombatService.get_state",
                return_value=state,
            ),
            patch(
                "app.api.routes.sessions.rolls_resolution._publish_and_log",
                new_callable=AsyncMock,
            ),
        ):
            mock_build.return_value = RollActorStats(
                display_name="Hero",
                abilities={"wisdom": 10},
                actor_kind="player",
                actor_ref_id="user-1",
            )

            result = await roll_ability(
                session_id="session-1", body=body, user=user, db=db
            )

            self.assertEqual(result.advantage_mode, "advantage")
            self.assertIsInstance(result.check_modifier_sources, list)
            self.assertEqual(result.check_modifier_sources[0]["source_label"], "Sabedoria da Coruja")
            self.assertTrue(result.check_modifier_sources[0]["applied"])

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

        with (
            patch(
                "app.api.routes.sessions.rolls_resolution._get_session_and_member",
                return_value=(session_entry, member),
            ),
            patch(
                "app.api.routes.sessions.rolls_resolution._build_actor_stats",
            ) as mock_build,
            patch(
                "app.api.routes.sessions.rolls_resolution._publish_and_log",
                new_callable=AsyncMock,
            ) as mock_publish,
            patch(
                "app.api.routes.sessions.rolls_resolution.CombatService.apply_initiative_roll",
                new_callable=AsyncMock,
            ) as mock_apply_initiative,
        ):
            mock_build.return_value = RollActorStats(
                display_name="Hero",
                abilities={"dexterity": 14},
                actor_kind="player",
                actor_ref_id="user-1",
            )

            result = await roll_initiative(
                session_id="session-1", body=body, user=user, db=db
            )

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


class TestSessionActivityRollResolvedEvent(unittest.TestCase):
    def test_session_activity_includes_check_modifier_sources(self):
        user = MagicMock()
        user.id = "user-1"

        session_entry = MagicMock()
        session_entry.id = "session-1"
        session_entry.campaign_id = "campaign-1"
        session_entry.started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        session_entry.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

        member = _make_member(RoleMode.PLAYER, user_id="user-1")
        command_user = MagicMock()
        command_user.username = "player"
        command_user.display_name = "Player"
        command = MagicMock()
        command.command_type = "roll_resolved"
        command.user_id = "user-1"
        command.actor_name = "Player"
        command.created_at = datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc)
        command.payload_json = {
            "roll_type": "ability",
            "actor_display_name": "Player",
            "actor_kind": "player",
            "ability": "wisdom",
            "rolls": [14, 7],
            "selected_roll": 14,
            "total": 14,
            "modifier_used": 0,
            "advantage_mode": "advantage",
            "dc": 12,
            "success": True,
            "check_modifier_sources": [
                {
                    "source_label": "Sabedoria da Coruja",
                    "modifier_type": "advantage",
                    "roll_type": "ability",
                    "ability": "wisdom",
                    "against": "any",
                    "applied": True,
                }
            ],
            "is_gm_roll": False,
        }

        session = MagicMock()
        session.exec.side_effect = [
            MagicMock(first=MagicMock(return_value=session_entry)),
            MagicMock(first=MagicMock(return_value=member)),
            MagicMock(all=MagicMock(return_value=[])),
            MagicMock(all=MagicMock(return_value=[])),
            MagicMock(all=MagicMock(return_value=[(command, command_user)])),
        ]

        events = get_session_activity("session-1", user=user, session=session)

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.type, "roll_resolved")
        self.assertEqual(event.advantageMode, "advantage")
        self.assertIsNotNone(event.check_modifier_sources)
        self.assertEqual(event.check_modifier_sources[0]["source_label"], "Sabedoria da Coruja")
        self.assertTrue(event.check_modifier_sources[0]["applied"])




class TestSaveRollEndToEnd(unittest.IsolatedAsyncioTestCase):
    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(15, 8))
    async def test_save_roll_applies_declared_advantage(self, _mock_d20):
        from app.api.routes.sessions.rolls_resolution import roll_save
        from app.schemas.roll import RollActorStats, SaveRollRequest

        user = MagicMock()
        user.id = "user-1"

        session_entry = MagicMock()
        session_entry.id = "session-1"
        session_entry.campaign_id = "campaign-1"
        session_entry.party_id = "party-1"
        session_entry.status = "ACTIVE"

        member = _make_member(RoleMode.PLAYER, user_id="user-1")

        db = MagicMock()

        body = SaveRollRequest(
            actor_kind="player",
            actor_ref_id="user-1",
            ability="strength",
            advantage_mode="normal",
            dc=15,
        )

        with (
            patch(
                "app.api.routes.sessions.rolls_resolution._get_session_and_member",
                return_value=(session_entry, member),
            ),
            patch(
                "app.api.routes.sessions.rolls_resolution._build_actor_stats",
            ) as mock_build,
            patch(
                "app.api.routes.sessions.rolls_resolution._publish_and_log",
                new_callable=AsyncMock,
            ) as mock_publish,
            patch(
                "app.services.combat_service.service.CombatService.get_state",
            ) as mock_get_state,
        ):
            mock_build.return_value = RollActorStats(
                display_name="Hero",
                abilities={"strength": 16},
                actor_kind="player",
                actor_ref_id="user-1",
            )
            mock_get_state.return_value = MagicMock(
                phase="active",
                participants=[
                    {
                        "id": "participant-1",
                        "ref_id": "user-1",
                        "kind": "player",
                        "active_effects": [
                            {
                                "kind": "spell_effect",
                                "metadata": {
                                    "source_spell_name": "Aumentar",
                                    "declarative_effect": {
                                        "type": "advantage_on_saves",
                                        "params": {"abilities": ["strength"]},
                                    },
                                },
                            }
                        ],
                    }
                ],
            )

            result = await roll_save(
                session_id="session-1", body=body, user=user, db=db
            )

            self.assertEqual(result.roll_type, "save")
            self.assertEqual(result.advantage_mode, "advantage")
            self.assertEqual(result.total, 18)  # 15 + 3 (STR mod)
            self.assertIsNotNone(result.check_modifier_sources)
            self.assertEqual(len(result.check_modifier_sources), 1)
            self.assertEqual(
                result.check_modifier_sources[0]["source_label"], "Aumentar"
            )
            self.assertTrue(result.check_modifier_sources[0]["applied"])
            mock_publish.assert_called_once()

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(15, 8))
    async def test_save_roll_manual_disadvantage_cancels_declared_advantage(self, _mock_d20):
        from app.api.routes.sessions.rolls_resolution import roll_save
        from app.schemas.roll import RollActorStats, SaveRollRequest

        user = MagicMock()
        user.id = "user-1"

        session_entry = MagicMock()
        session_entry.id = "session-1"
        session_entry.campaign_id = "campaign-1"
        session_entry.party_id = "party-1"
        session_entry.status = "ACTIVE"

        member = _make_member(RoleMode.PLAYER, user_id="user-1")

        db = MagicMock()

        body = SaveRollRequest(
            actor_kind="player",
            actor_ref_id="user-1",
            ability="strength",
            advantage_mode="disadvantage",
            dc=15,
        )

        with (
            patch(
                "app.api.routes.sessions.rolls_resolution._get_session_and_member",
                return_value=(session_entry, member),
            ),
            patch(
                "app.api.routes.sessions.rolls_resolution._build_actor_stats",
            ) as mock_build,
            patch(
                "app.api.routes.sessions.rolls_resolution._publish_and_log",
                new_callable=AsyncMock,
            ) as mock_publish,
            patch(
                "app.services.combat_service.service.CombatService.get_state",
            ) as mock_get_state,
        ):
            mock_build.return_value = RollActorStats(
                display_name="Hero",
                abilities={"strength": 16},
                actor_kind="player",
                actor_ref_id="user-1",
            )
            mock_get_state.return_value = MagicMock(
                phase="active",
                participants=[
                    {
                        "id": "participant-1",
                        "ref_id": "user-1",
                        "kind": "player",
                        "active_effects": [
                            {
                                "kind": "spell_effect",
                                "metadata": {
                                    "source_spell_name": "Aumentar",
                                    "declarative_effect": {
                                        "type": "advantage_on_saves",
                                        "params": {"abilities": ["strength"]},
                                    },
                                },
                            }
                        ],
                    }
                ],
            )

            result = await roll_save(
                session_id="session-1", body=body, user=user, db=db
            )

            self.assertEqual(result.advantage_mode, "normal")
            mock_publish.assert_called_once()


if __name__ == "__main__":
    unittest.main()
