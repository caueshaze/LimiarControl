import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.services.combat import CombatService, CombatServiceError
from app.services.draconic_ancestry import resolve_active_elemental_resistances
from app.services.session_state_finalize import finalize_session_state_data
from app.services.sorcerer_progression import (
    SORCERY_POINTS_RESOURCE_KEY,
    apply_sorcery_points_canonical_state,
    compute_sorcery_points_max,
    get_sorcery_points_remaining,
)


def _draconic_sorcerer_state(level=6, ancestry="red", points_remaining=None, abilities=None):
    state = {
        "class": "sorcerer",
        "subclass": "draconic_bloodline",
        "level": level,
        "subclassConfig": {"draconicAncestry": ancestry},
        "abilities": abilities or {"charisma": 16, "constitution": 10},
        "currentHP": 32,
        "maxHP": 32,
        "deathSaves": {"successes": 0, "failures": 0},
    }
    if points_remaining is not None:
        state["classResources"] = {
            SORCERY_POINTS_RESOURCE_KEY: {
                "usesMax": max(level, points_remaining),
                "usesRemaining": points_remaining,
            }
        }
    return state


class TestSorceryPointProgression(unittest.TestCase):
    def test_max_is_sorcerer_level_from_level_2(self):
        self.assertEqual(compute_sorcery_points_max(1), 0)
        self.assertEqual(compute_sorcery_points_max(2), 2)
        self.assertEqual(compute_sorcery_points_max(6), 6)
        self.assertEqual(compute_sorcery_points_max(20), 20)

    def test_non_positive_or_invalid_level(self):
        self.assertEqual(compute_sorcery_points_max(0), 0)
        self.assertEqual(compute_sorcery_points_max(-3), 0)
        self.assertEqual(compute_sorcery_points_max("abc"), 0)

    def test_canonical_state_populates_pool_for_sorcerer(self):
        data = apply_sorcery_points_canonical_state(_draconic_sorcerer_state(level=6))
        resource = data["classResources"][SORCERY_POINTS_RESOURCE_KEY]
        self.assertEqual(resource["usesMax"], 6)
        self.assertEqual(resource["usesRemaining"], 6)

    def test_canonical_state_preserves_and_clamps_remaining(self):
        data = apply_sorcery_points_canonical_state(_draconic_sorcerer_state(level=6, points_remaining=2))
        self.assertEqual(data["classResources"][SORCERY_POINTS_RESOURCE_KEY]["usesRemaining"], 2)
        # remaining above max is clamped down
        over = _draconic_sorcerer_state(level=6)
        over["classResources"] = {SORCERY_POINTS_RESOURCE_KEY: {"usesMax": 6, "usesRemaining": 99}}
        clamped = apply_sorcery_points_canonical_state(over)
        self.assertEqual(clamped["classResources"][SORCERY_POINTS_RESOURCE_KEY]["usesRemaining"], 6)

    def test_canonical_state_merges_with_sibling_resources(self):
        data = _draconic_sorcerer_state(level=6)
        data["classResources"] = {"dragonbornBreathWeapon": {"usesMax": 1, "usesRemaining": 1}}
        out = apply_sorcery_points_canonical_state(data)
        self.assertIn("dragonbornBreathWeapon", out["classResources"])
        self.assertIn(SORCERY_POINTS_RESOURCE_KEY, out["classResources"])

    def test_canonical_state_removes_pool_for_non_sorcerer(self):
        data = {"class": "fighter", "level": 6, "classResources": {SORCERY_POINTS_RESOURCE_KEY: {"usesMax": 6, "usesRemaining": 3}}}
        out = apply_sorcery_points_canonical_state(data)
        self.assertNotIn("classResources", out)

    def test_finalize_populates_pool_end_to_end(self):
        data = finalize_session_state_data(_draconic_sorcerer_state(level=6))
        self.assertEqual(get_sorcery_points_remaining(data), 6)


class TestActiveElementalResistanceResolution(unittest.TestCase):
    def test_none_without_effects(self):
        self.assertEqual(resolve_active_elemental_resistances(_draconic_sorcerer_state()), [])

    def test_reads_active_effect_damage_type(self):
        data = _draconic_sorcerer_state()
        data["active_spell_effects"] = [
            {"kind": "elemental_affinity_resistance", "damage_type": "Fire", "duration_type": "timed"}
        ]
        self.assertEqual(resolve_active_elemental_resistances(data), ["fire"])

    def test_ignores_unrelated_effects(self):
        data = _draconic_sorcerer_state()
        data["active_spell_effects"] = [{"kind": "temp_ac_bonus", "numeric_value": 2}]
        self.assertEqual(resolve_active_elemental_resistances(data), [])

    def test_finalize_prunes_expired_activation(self):
        data = _draconic_sorcerer_state()
        data["active_spell_effects"] = [
            {
                "id": "ea-1",
                "kind": "elemental_affinity_resistance",
                "damage_type": "fire",
                "duration_type": "timed",
                "expires_at_game_time_seconds": 100,
            }
        ]
        # Before expiry the activation is preserved.
        still_active = finalize_session_state_data(data, game_time_seconds=50)
        self.assertEqual(resolve_active_elemental_resistances(still_active), ["fire"])
        # After expiry it is pruned -> no resistance.
        expired = finalize_session_state_data(data, game_time_seconds=200)
        self.assertEqual(resolve_active_elemental_resistances(expired), [])


class TestActivateDraconicElementalResistance(unittest.IsolatedAsyncioTestCase):
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
                }
            ],
        )

    def _session_state(self, state_json):
        return SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json=state_json,
        )

    async def _activate(self, state_json):
        session_state = self._session_state(state_json)
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
            patch("app.services.combat.CombatService._get_stats", return_value=(session_state, 10, 10, 10, 3, 0)), \
            patch("app.services.combat_service.draconic_elemental_resistance.get_game_time_seconds", return_value=1000), \
            patch("app.services.combat.CombatService._emit_player_state_update", new=AsyncMock()), \
            patch("app.services.combat.CombatService._emit_state", new=AsyncMock()), \
            patch("app.services.combat.CombatService._emit_and_persist_log", new=AsyncMock()):
            result = await CombatService.activate_draconic_elemental_resistance(
                self.db,
                "session-123",
                actor_participant_id="p1",
                actor_user_id="user-1",
                is_gm=False,
            )
        return result, session_state

    async def test_activation_spends_point_and_grants_timed_resistance(self):
        result, session_state = await self._activate(_draconic_sorcerer_state(level=6, ancestry="red"))
        # 1 of 6 sorcery points spent
        self.assertEqual(result["sorcery_points_remaining"], 5)
        self.assertEqual(get_sorcery_points_remaining(session_state.state_json), 5)
        # damage type comes from the lineage (red -> fire)
        self.assertEqual(result["damage_type"], "fire")
        # timed effect added, expiring 60s after game time (1000 -> 1060)
        self.assertEqual(result["expires_at_game_time_seconds"], 1060)
        self.assertEqual(resolve_active_elemental_resistances(session_state.state_json), ["fire"])

    async def test_reactivation_refreshes_without_stacking(self):
        _, session_state = await self._activate(_draconic_sorcerer_state(level=6, ancestry="white"))
        effects = [
            e for e in session_state.state_json.get("active_spell_effects", [])
            if e.get("kind") == "elemental_affinity_resistance"
        ]
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["damage_type"], "cold")

    async def test_no_points_remaining_is_rejected(self):
        with self.assertRaises(CombatServiceError) as ctx:
            await self._activate(_draconic_sorcerer_state(level=6, points_remaining=0))
        self.assertIn("sorcery point", str(ctx.exception).lower())

    async def test_below_level_6_has_no_elemental_affinity(self):
        with self.assertRaises(CombatServiceError) as ctx:
            await self._activate(_draconic_sorcerer_state(level=5, ancestry="red"))
        self.assertIn("elemental affinity", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
