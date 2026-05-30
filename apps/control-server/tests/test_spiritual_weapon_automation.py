"""Integration tests for Spiritual Weapon spell automation.

Tests the automation handler and follow-up action directly,
verifying that the mechanic is actually implemented — not just registered.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.combat_spells import CombatGridCell
from app.services.combat import CombatService
from app.services.combat_service.exceptions import CombatServiceError
from app.services.combat_service.spell_anchors import (
    get_spell_anchor_by_id,
    get_spell_anchors_for_owner,
    create_spell_anchor,
)
from app.services.combat_service.spells.automation._spiritual_weapon import resolve_spiritual_weapon_damage_dice


_FAKE_BATTLE_MAP = {
    "gridWidth": 20,
    "gridHeight": 20,
    "blockedCells": [],
    "obstacles": [],
}


def _make_state() -> CombatState:
    return CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        use_map=True,
        map_selection=_FAKE_BATTLE_MAP,
        participants=[
            {
                "id": "p1",
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Cleric",
                "initiative": 20,
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-1",
                "active_effects": [],
                "turn_resources": {
                    "action_used": False,
                    "bonus_action_used": False,
                    "reaction_used": False,
                },
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
                "active_effects": [],
                "turn_resources": {},
            },
        ],
    )


def _make_spell_context(
    *,
    slot_level: int = 2,
    attack_bonus: int = 7,
    spell_mod: int = 4,
) -> dict:
    return {
        "spell_canonical_key": "spiritual_weapon",
        "spell_name": "Arma Espiritual",
        "slot_level": slot_level,
        "spell_level": 2,
        "attack_bonus": attack_bonus,
        "spell_mod": spell_mod,
        "spell_mode": "spell_attack",
        "effect_dice": resolve_spiritual_weapon_damage_dice(slot_level),
        "effect_bonus": 0,
        "effect_kind": "damage",
        "damage_type": "force",
        "save_ability": None,
        "save_dc": None,
        "save_success_outcome": None,
        "source_kind": "spell",
    }


def _make_req(
    *,
    anchor_x: int = 5,
    anchor_y: int = 5,
    target_ref_id: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        actor_participant_id="p1",
        target_ref_id=target_ref_id,
        anchor_cell=CombatGridCell(x=anchor_x, y=anchor_y),
        roll_source="system",
        manual_roll=None,
        manual_rolls=None,
        has_advantage=False,
        has_disadvantage=False,
        spell_attack_bonus=None,
        override_resource_limit=False,
    )


def _make_attacker_state() -> SessionState:
    return SessionState(
        id="state-1",
        session_id="session-1",
        player_user_id="player-1",
        state_json={
            "spellcasting": {
                "ability": "wisdom",
                "spells": [
                    {"id": "s1", "canonicalKey": "spiritual_weapon", "level": 2, "prepared": True}
                ],
                "slots": {"2": {"used": 0, "max": 3}},
            }
        },
    )


class TestSpiritualWeaponInitialCast(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = MagicMock()
        self.state = _make_state()

    async def _call_handler(
        self,
        *,
        target_ref_id: str | None = None,
        slot_level: int = 2,
        anchor_x: int = 5,
        anchor_y: int = 5,
        target_ac: int = 12,
        hit_roll: int = 15,
    ) -> dict:
        attacker = self.state.participants[0]
        target_p = (
            next((p for p in self.state.participants if p["ref_id"] == target_ref_id), None)
            if target_ref_id
            else None
        )
        req = _make_req(anchor_x=anchor_x, anchor_y=anchor_y, target_ref_id=target_ref_id)
        spell_context = _make_spell_context(slot_level=slot_level)

        with (
            patch.object(
                CombatService,
                "_get_stats",
                return_value=(MagicMock(), target_ac, 10, 10, 2, 4),
            ),
            patch("random.randint", return_value=hit_roll),
        ):
            return await CombatService._cast_spiritual_weapon_automation(
                self.db,
                "session-1",
                attacker=attacker,
                attacker_model=_make_attacker_state(),
                actor_user_id="user-1",
                is_gm=False,
                req=req,
                state=self.state,
                spell_context=spell_context,
                target_participant=target_p,
            )

    async def test_initial_cast_creates_anchor(self):
        await self._call_handler()
        anchors = get_spell_anchors_for_owner(self.state, "p1")
        self.assertEqual(len(anchors), 1)
        self.assertEqual(anchors[0]["source_spell_key"], "spiritual_weapon")
        self.assertEqual(anchors[0]["position"], {"x": 5, "y": 5})

    async def test_initial_cast_anchor_has_10_rounds(self):
        await self._call_handler()
        anchor = get_spell_anchors_for_owner(self.state, "p1")[0]
        self.assertEqual(anchor["remaining_rounds"], 10)
        self.assertEqual(anchor["expires_on"], "turn_start")
        self.assertEqual(anchor["expires_at_participant_id"], "p1")

    async def test_initial_cast_stores_metadata(self):
        await self._call_handler(slot_level=2)
        anchor = get_spell_anchors_for_owner(self.state, "p1")[0]
        meta = anchor["metadata"]
        self.assertEqual(meta["damage_dice"], "1d8")
        self.assertEqual(meta["spell_mod"], 4)
        self.assertIn("attack_bonus", meta)

    async def test_initial_cast_without_target_still_creates_anchor(self):
        result = await self._call_handler(target_ref_id=None)
        anchors = get_spell_anchors_for_owner(self.state, "p1")
        self.assertEqual(len(anchors), 1)
        self.assertIsNone(result["is_hit"])
        self.assertEqual(result["damage"], 0)

    async def test_initial_attack_hits_and_applies_force_damage(self):
        with patch.object(CombatService, "_apply_spell_effect", return_value=(50, "50 force damage", 60, None)) as mock_apply:
            await self._call_handler(target_ref_id="enemy-1", hit_roll=15, target_ac=12)
            mock_apply.assert_called_once()
            call_kwargs = mock_apply.call_args
            self.assertEqual(call_kwargs.kwargs.get("damage_type") or call_kwargs.args[6], "force")

    async def test_initial_attack_hit_result_is_recorded(self):
        with patch.object(CombatService, "_apply_spell_effect", return_value=(50, "msg", 60, None)):
            result = await self._call_handler(target_ref_id="enemy-1", hit_roll=15, target_ac=12)
        self.assertTrue(result["is_hit"])
        self.assertGreater(result["damage"], 0)

    async def test_initial_attack_miss_does_not_apply_damage(self):
        with patch.object(CombatService, "_apply_spell_effect") as mock_apply:
            result = await self._call_handler(target_ref_id="enemy-1", hit_roll=1, target_ac=30)
        mock_apply.assert_not_called()
        self.assertFalse(result["is_hit"])
        self.assertEqual(result["damage"], 0)

    async def test_initial_attack_miss_still_creates_anchor(self):
        result = await self._call_handler(target_ref_id="enemy-1", hit_roll=1, target_ac=30)
        anchors = get_spell_anchors_for_owner(self.state, "p1")
        self.assertEqual(len(anchors), 1)

    async def test_recast_replaces_existing_anchor(self):
        await self._call_handler(anchor_x=5, anchor_y=5)
        await self._call_handler(anchor_x=8, anchor_y=3)
        anchors = get_spell_anchors_for_owner(self.state, "p1")
        self.assertEqual(len(anchors), 1)
        self.assertEqual(anchors[0]["position"], {"x": 8, "y": 3})

    async def test_missing_anchor_cell_raises(self):
        attacker = self.state.participants[0]
        req = SimpleNamespace(
            anchor_cell=None,
            target_ref_id=None,
            roll_source="system",
            manual_roll=None,
            manual_rolls=None,
            has_advantage=False,
            has_disadvantage=False,
            spell_attack_bonus=None,
        )
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_spiritual_weapon_automation(
                self.db, "session-1",
                attacker=attacker,
                attacker_model=_make_attacker_state(),
                actor_user_id="user-1",
                is_gm=False,
                req=req,
                state=self.state,
                spell_context=_make_spell_context(),
                target_participant=None,
            )


class TestSpiritualWeaponUpcasting(unittest.TestCase):
    def test_slot_2_damage_dice_is_1d8(self):
        self.assertEqual(resolve_spiritual_weapon_damage_dice(2), "1d8")

    def test_slot_3_damage_dice_is_1d8(self):
        self.assertEqual(resolve_spiritual_weapon_damage_dice(3), "1d8")

    def test_slot_4_damage_dice_is_2d8(self):
        self.assertEqual(resolve_spiritual_weapon_damage_dice(4), "2d8")

    def test_slot_5_damage_dice_is_2d8(self):
        self.assertEqual(resolve_spiritual_weapon_damage_dice(5), "2d8")

    def test_slot_6_damage_dice_is_3d8(self):
        self.assertEqual(resolve_spiritual_weapon_damage_dice(6), "3d8")


class TestSpiritualWeaponResolveContextPreview(unittest.TestCase):
    """Verify that preview / resolve-context returns correct upcast dice via levelStep."""

    def _apply_upcast(self, slot_level: int) -> dict:
        from app.services.combat import CombatService
        return CombatService._apply_structured_spell_upcast(
            spell_level=2,
            slot_level=slot_level,
            effect_kind="damage",
            effect_dice="1d8",
            effect_bonus=0,
            upcast={"mode": "extra_damage_dice", "dice": "1d8", "levelStep": 2},
        )

    def test_slot_2_preview_is_1d8(self):
        result = self._apply_upcast(2)
        self.assertEqual(result["effect_dice"], "1d8")

    def test_slot_3_preview_is_1d8(self):
        result = self._apply_upcast(3)
        self.assertEqual(result["effect_dice"], "1d8")

    def test_slot_4_preview_is_2d8(self):
        result = self._apply_upcast(4)
        self.assertEqual(result["effect_dice"], "2d8")

    def test_slot_6_preview_is_3d8(self):
        result = self._apply_upcast(6)
        self.assertEqual(result["effect_dice"], "3d8")

    def test_slot_8_preview_is_4d8(self):
        result = self._apply_upcast(8)
        self.assertEqual(result["effect_dice"], "4d8")


class TestSpiritualWeaponFollowUp(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = MagicMock()
        self.state = _make_state()

    def _seed_anchor(self, *, position: dict | None = None) -> str:
        position = position or {"x": 5, "y": 5}
        anchor = create_spell_anchor(
            self.state,
            anchor={
                "source_spell_key": "spiritual_weapon",
                "source_spell_name": "Arma Espiritual",
                "owner_participant_id": "p1",
                "created_by_participant_id": "p1",
                "position": position,
                "duration_type": "rounds",
                "remaining_rounds": 9,
                "expires_on": "turn_start",
                "expires_at_participant_id": "p1",
                "render_kind": "spiritual_weapon",
                "movement": {"max_meters_per_follow_up": 6.0},
                "metadata": {
                    "damage_dice": "1d8",
                    "spell_mod": 4,
                    "attack_bonus": 7,
                    "slot_level": 2,
                },
            },
        )
        return anchor["id"]

    def _make_follow_up_req(
        self,
        *,
        anchor_id: str,
        destination: dict | None = None,
        target_ref_id: str | None = None,
        target_kind: str | None = None,
    ):
        return SimpleNamespace(
            actor_participant_id="p1",
            anchor_id=anchor_id,
            destination=destination,
            target_ref_id=target_ref_id,
            target_kind=target_kind,
            manual_roll=None,
        )

    async def _run_follow_up(self, req, *, target_ac: int = 12, hit_roll: int = 15) -> dict:
        with (
            patch.object(CombatService, "get_state", return_value=self.state),
            patch.object(CombatService, "_get_stats", return_value=(MagicMock(), target_ac, 10, 10, 2, 4)),
            patch.object(CombatService, "_emit_state", new=AsyncMock()),
            patch.object(CombatService, "_emit_log", new=AsyncMock()),
            patch.object(CombatService, "_require_active", return_value=None),
            patch.object(CombatService, "_require_actor_status", return_value=None),
            patch("random.randint", return_value=hit_roll),
        ):
            return await CombatService.use_spiritual_weapon_action(
                self.db, "session-1", req, "user-1", is_gm=False
            )

    async def test_follow_up_moves_anchor(self):
        anchor_id = self._seed_anchor(position={"x": 5, "y": 5})
        req = self._make_follow_up_req(anchor_id=anchor_id, destination={"x": 7, "y": 5})
        with patch.object(CombatService, "get_state", return_value=self.state), \
             patch.object(CombatService, "_emit_state", new=AsyncMock()), \
             patch.object(CombatService, "_emit_log", new=AsyncMock()), \
             patch.object(CombatService, "_require_active", return_value=None), \
             patch.object(CombatService, "_require_actor_status", return_value=None):
            await CombatService.use_spiritual_weapon_action(
                self.db, "session-1", req, "user-1", is_gm=False
            )
        anchor = get_spell_anchor_by_id(self.state, anchor_id)
        self.assertEqual(anchor["position"], {"x": 7, "y": 5})

    async def test_follow_up_rejects_move_over_6m(self):
        anchor_id = self._seed_anchor(position={"x": 5, "y": 5})
        req = self._make_follow_up_req(anchor_id=anchor_id, destination={"x": 20, "y": 5})
        with patch.object(CombatService, "get_state", return_value=self.state), \
             patch.object(CombatService, "_require_active", return_value=None), \
             patch.object(CombatService, "_require_actor_status", return_value=None):
            with self.assertRaises(CombatServiceError):
                await CombatService.use_spiritual_weapon_action(
                    self.db, "session-1", req, "user-1", is_gm=False
                )

    async def test_follow_up_attacks_target(self):
        anchor_id = self._seed_anchor()
        req = self._make_follow_up_req(anchor_id=anchor_id, target_ref_id="enemy-1", target_kind="session_entity")
        with patch.object(CombatService, "_apply_spell_effect", return_value=(50, "msg", 60, None)) as mock_apply:
            await self._run_follow_up(req, hit_roll=15, target_ac=12)
        mock_apply.assert_called_once()

    async def test_follow_up_miss_does_not_apply_damage(self):
        anchor_id = self._seed_anchor()
        req = self._make_follow_up_req(anchor_id=anchor_id, target_ref_id="enemy-1", target_kind="session_entity")
        with patch.object(CombatService, "_apply_spell_effect") as mock_apply:
            result = await self._run_follow_up(req, hit_roll=1, target_ac=30)
        mock_apply.assert_not_called()
        self.assertFalse(result["isHit"])

    async def test_follow_up_consumes_bonus_action(self):
        anchor_id = self._seed_anchor()
        req = self._make_follow_up_req(anchor_id=anchor_id, destination={"x": 6, "y": 5})
        await self._run_follow_up(req)
        attacker = self.state.participants[0]
        self.assertTrue(attacker["turn_resources"]["bonus_action_used"])

    async def test_follow_up_fails_if_bonus_action_used(self):
        anchor_id = self._seed_anchor()
        self.state.participants[0]["turn_resources"]["bonus_action_used"] = True
        req = self._make_follow_up_req(anchor_id=anchor_id, destination={"x": 6, "y": 5})
        with patch.object(CombatService, "get_state", return_value=self.state), \
             patch.object(CombatService, "_require_active", return_value=None), \
             patch.object(CombatService, "_require_actor_status", return_value=None):
            with self.assertRaises(CombatServiceError):
                await CombatService.use_spiritual_weapon_action(
                    self.db, "session-1", req, "user-1", is_gm=False
                )

    async def test_follow_up_requires_active_anchor(self):
        req = self._make_follow_up_req(anchor_id="nonexistent-anchor-id", destination={"x": 6, "y": 5})
        with patch.object(CombatService, "get_state", return_value=self.state), \
             patch.object(CombatService, "_require_active", return_value=None), \
             patch.object(CombatService, "_require_actor_status", return_value=None):
            with self.assertRaises(CombatServiceError):
                await CombatService.use_spiritual_weapon_action(
                    self.db, "session-1", req, "user-1", is_gm=False
                )

    async def test_follow_up_rejects_wrong_owner(self):
        anchor_id = self._seed_anchor()
        req = self._make_follow_up_req(anchor_id=anchor_id, destination={"x": 6, "y": 5})
        req.actor_participant_id = "e1"  # enemy trying to use cleric's anchor
        with patch.object(CombatService, "get_state", return_value=self.state), \
             patch.object(CombatService, "_require_active", return_value=None), \
             patch.object(CombatService, "_require_actor_status", return_value=None):
            with self.assertRaises(CombatServiceError):
                await CombatService.use_spiritual_weapon_action(
                    self.db, "session-1", req, "enemy-user", is_gm=False
                )

    async def test_follow_up_rejects_noop_request(self):
        anchor_id = self._seed_anchor()
        req = self._make_follow_up_req(anchor_id=anchor_id)  # no destination, no target
        with patch.object(CombatService, "get_state", return_value=self.state), \
             patch.object(CombatService, "_require_active", return_value=None), \
             patch.object(CombatService, "_require_actor_status", return_value=None):
            with self.assertRaises(CombatServiceError):
                await CombatService.use_spiritual_weapon_action(
                    self.db, "session-1", req, "user-1", is_gm=False
                )

    async def test_follow_up_uses_persisted_attack_bonus_and_dice(self):
        create_spell_anchor(
            self.state,
            anchor={
                "source_spell_key": "spiritual_weapon",
                "source_spell_name": "Arma Espiritual",
                "owner_participant_id": "p1",
                "created_by_participant_id": "p1",
                "position": {"x": 5, "y": 5},
                "duration_type": "rounds",
                "remaining_rounds": 5,
                "expires_on": "turn_start",
                "expires_at_participant_id": "p1",
                "movement": {"max_meters_per_follow_up": 6.0},
                "metadata": {
                    "damage_dice": "2d8",  # upcast slot 4
                    "spell_mod": 5,
                    "attack_bonus": 9,
                    "slot_level": 4,
                },
            },
        )
        anchors = get_spell_anchors_for_owner(self.state, "p1")
        anchor_id = anchors[0]["id"]
        req = self._make_follow_up_req(
            anchor_id=anchor_id,
            target_ref_id="enemy-1",
            target_kind="session_entity",
        )
        with patch.object(CombatService, "_apply_spell_effect", return_value=(40, "msg", 50, None)) as mock_apply, \
             patch.object(CombatService, "_resolve_damage_roll", return_value=([8, 6], 14)) as mock_roll:
            await self._run_follow_up(req, hit_roll=18, target_ac=12)
        mock_roll.assert_called_once_with("2d8", roll_source="system")
        mock_apply.assert_called_once()


class TestSpiritualWeaponLifecycle(unittest.TestCase):
    def test_anchor_expires_after_10_owner_turn_starts(self):
        from app.services.combat_service.spell_anchors import (
            create_spell_anchor,
            tick_spell_anchors_for_turn,
        )
        state = _make_state()
        create_spell_anchor(
            state,
            anchor={
                "source_spell_key": "spiritual_weapon",
                "owner_participant_id": "p1",
                "created_by_participant_id": "p1",
                "position": {"x": 5, "y": 5},
                "duration_type": "rounds",
                "remaining_rounds": 10,
                "expires_on": "turn_start",
                "expires_at_participant_id": "p1",
            },
        )

        for i in range(9):
            expired = tick_spell_anchors_for_turn(state, participant_id="p1", trigger="turn_start")
            self.assertEqual(len(expired), 0, f"Should not expire on tick {i + 1}")

        expired = tick_spell_anchors_for_turn(state, participant_id="p1", trigger="turn_start")
        self.assertEqual(len(expired), 1)
        self.assertEqual(expired[0]["source_spell_key"], "spiritual_weapon")
        self.assertEqual(state.spell_anchors, [])


if __name__ == "__main__":
    unittest.main()
