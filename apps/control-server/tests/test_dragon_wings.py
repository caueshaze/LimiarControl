import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.services.combat import CombatService, CombatServiceError
from app.services.dragon_wings import (
    apply_dragon_wings_canonical_state,
    is_dragon_wings_active,
    is_dragon_wings_eligible,
    resolve_dragon_wings_state,
)
from app.services.session_state_finalize import finalize_session_state_data
from app.services.sorcerer_progression import build_sorcerer_class_features


def _wings_sorcerer(level=14, active=None, speed=9):
    data = {
        "class": "sorcerer",
        "subclass": "draconic_bloodline",
        "level": level,
        "subclassConfig": {"draconicAncestry": "red"},
        "abilities": {"charisma": 16, "constitution": 12},
        "speedMeters": speed,
        "currentHP": 60,
        "maxHP": 60,
        "deathSaves": {"successes": 0, "failures": 0},
    }
    if active is not None:
        data["dragonWings"] = {"active": active}
    return data


class TestDragonWingsLogic(unittest.TestCase):
    def test_eligibility_requires_level_14_draconic_sorcerer(self):
        self.assertTrue(is_dragon_wings_eligible(_wings_sorcerer(level=14)))
        self.assertFalse(is_dragon_wings_eligible(_wings_sorcerer(level=13)))
        self.assertFalse(is_dragon_wings_eligible({"class": "fighter", "level": 20}))

    def test_active_requires_eligibility(self):
        self.assertTrue(is_dragon_wings_active(_wings_sorcerer(level=14, active=True)))
        # active flag below level 14 is ignored
        self.assertFalse(is_dragon_wings_active(_wings_sorcerer(level=13, active=True)))

    def test_resolve_state_fly_speed_equals_walk_when_active(self):
        state = resolve_dragon_wings_state(_wings_sorcerer(level=14, active=True, speed=12))
        self.assertEqual(state, {"eligible": True, "active": True, "flySpeedMeters": 12})

    def test_resolve_state_zero_fly_speed_when_inactive(self):
        state = resolve_dragon_wings_state(_wings_sorcerer(level=14, active=False, speed=12))
        self.assertEqual(state, {"eligible": True, "active": False, "flySpeedMeters": 0})

    def test_canonical_state_sets_flight_fields_when_active(self):
        out = apply_dragon_wings_canonical_state(_wings_sorcerer(level=14, active=True, speed=9))
        self.assertEqual(out["dragonWings"], {"active": True})
        self.assertTrue(out["flying"])
        self.assertEqual(out["flySpeedMeters"], 9)

    def test_canonical_state_clears_flight_fields_when_inactive(self):
        out = apply_dragon_wings_canonical_state(_wings_sorcerer(level=14, active=False))
        self.assertEqual(out["dragonWings"], {"active": False})
        self.assertNotIn("flying", out)
        self.assertNotIn("flySpeedMeters", out)

    def test_canonical_state_drops_wings_when_ineligible(self):
        out = apply_dragon_wings_canonical_state(_wings_sorcerer(level=13, active=True))
        self.assertNotIn("dragonWings", out)
        self.assertNotIn("flying", out)

    def test_feature_present_only_from_level_14(self):
        ids_13 = [f["id"] for f in build_sorcerer_class_features(_wings_sorcerer(level=13))]
        ids_14 = [f["id"] for f in build_sorcerer_class_features(_wings_sorcerer(level=14))]
        self.assertNotIn("dragon_wings", ids_13)
        self.assertIn("dragon_wings", ids_14)

    def test_finalize_canonicalizes_flight_end_to_end(self):
        out = finalize_session_state_data(_wings_sorcerer(level=14, active=True, speed=9))
        self.assertTrue(out.get("flying"))
        self.assertEqual(out.get("flySpeedMeters"), 9)


class TestToggleDragonWings(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = MagicMock()
        self.state = CombatState(
            id="combat-123",
            session_id="session-123",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "player-123",
                    "kind": "player",
                    "display_name": "Hero",
                    "initiative": 10,
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "user-1",
                    "turn_resources": {
                        "action_used": False,
                        "bonus_action_used": False,
                        "reaction_used": False,
                    },
                }
            ],
        )

    async def _toggle(self, state_json, *, activate):
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json=state_json,
        )
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
            patch("app.services.combat.CombatService._get_stats", return_value=(session_state, 10, 10, 10, 5, 0)), \
            patch("app.services.combat.CombatService._emit_player_state_update", new=AsyncMock()), \
            patch("app.services.combat.CombatService._emit_state", new=AsyncMock()), \
            patch("app.services.combat.CombatService._emit_and_persist_log", new=AsyncMock()):
            result = await CombatService.toggle_dragon_wings(
                self.db,
                "session-123",
                activate=activate,
                actor_participant_id="p1",
                actor_user_id="user-1",
                is_gm=False,
            )
        return result, session_state

    async def test_activate_grants_flight_and_spends_bonus_action(self):
        result, session_state = await self._toggle(_wings_sorcerer(level=14, speed=9), activate=True)
        self.assertTrue(result["active"])
        self.assertEqual(result["fly_speed_meters"], 9)
        self.assertEqual(session_state.state_json["dragonWings"], {"active": True})
        self.assertEqual(session_state.state_json["flySpeedMeters"], 9)
        self.assertTrue(self.state.participants[0]["turn_resources"]["bonus_action_used"])

    async def test_deactivate_clears_flight(self):
        result, session_state = await self._toggle(
            _wings_sorcerer(level=14, active=True, speed=9), activate=False
        )
        self.assertFalse(result["active"])
        self.assertEqual(session_state.state_json["dragonWings"], {"active": False})
        self.assertNotIn("flySpeedMeters", session_state.state_json)

    async def test_below_level_14_is_rejected(self):
        with self.assertRaises(CombatServiceError) as ctx:
            await self._toggle(_wings_sorcerer(level=13), activate=True)
        self.assertIn("not available", str(ctx.exception).lower())

    async def test_double_activation_is_rejected(self):
        with self.assertRaises(CombatServiceError) as ctx:
            await self._toggle(_wings_sorcerer(level=14, active=True), activate=True)
        self.assertIn("already active", str(ctx.exception).lower())

    async def test_deactivate_when_inactive_is_rejected(self):
        with self.assertRaises(CombatServiceError) as ctx:
            await self._toggle(_wings_sorcerer(level=14, active=False), activate=False)
        self.assertIn("not active", str(ctx.exception).lower())

    async def test_bonus_action_already_used_is_rejected(self):
        self.state.participants[0]["turn_resources"]["bonus_action_used"] = True
        with self.assertRaises(CombatServiceError) as ctx:
            await self._toggle(_wings_sorcerer(level=14), activate=True)
        self.assertIn("bonus action", str(ctx.exception).lower())


class TestFlyingSuppressesFall(unittest.TestCase):
    def test_actor_is_flying_true_when_wings_active(self):
        session_state = SessionState(
            id="s", session_id="session-123", player_user_id="player-123",
            state_json=_wings_sorcerer(level=14, active=True),
        )
        with patch("app.services.combat.CombatService._get_stats", return_value=(session_state, 10, 10, 10, 5, 0)):
            self.assertTrue(
                CombatService._actor_is_flying(
                    MagicMock(), "session-123",
                    {"kind": "player", "ref_id": "player-123"},
                )
            )

    def test_actor_is_flying_false_when_wings_inactive(self):
        session_state = SessionState(
            id="s", session_id="session-123", player_user_id="player-123",
            state_json=_wings_sorcerer(level=14, active=False),
        )
        with patch("app.services.combat.CombatService._get_stats", return_value=(session_state, 10, 10, 10, 5, 0)):
            self.assertFalse(
                CombatService._actor_is_flying(
                    MagicMock(), "session-123",
                    {"kind": "player", "ref_id": "player-123"},
                )
            )

    def test_actor_is_flying_false_for_non_player(self):
        self.assertFalse(
            CombatService._actor_is_flying(
                MagicMock(), "session-123",
                {"kind": "session_entity", "ref_id": "enemy-1"},
            )
        )


if __name__ == "__main__":
    unittest.main()
