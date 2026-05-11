from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.combat_service.exceptions import CombatServiceError
from app.services.combat_service.spell_anchors import (
    get_spell_anchors_for_owner,
    tick_spell_anchors_for_turn,
)
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


_MAP = {"gridWidth": 20, "gridHeight": 20, "blockedCells": [], "obstacles": []}


def _make_state() -> CombatState:
    return CombatState(
        id="c1",
        session_id="s1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        use_map=True,
        map_selection=_MAP,
        participants=[
            {
                "id": "p1",
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Lia",
                "status": "active",
                "initiative": 20,
                "team": "players",
                "visible": True,
                "actor_user_id": "u1",
                "position": {"x": 2, "y": 2},
                "active_effects": [],
                "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
            },
            {
                "id": "p2",
                "ref_id": "player-2",
                "kind": "player",
                "display_name": "Theo",
                "status": "active",
                "initiative": 10,
                "team": "players",
                "visible": True,
                "actor_user_id": "u2",
                "position": {"x": 3, "y": 3},
                "active_effects": [],
                "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
            },
            {
                "id": "e1",
                "ref_id": "enemy-1",
                "kind": "session_entity",
                "display_name": "Goblin",
                "status": "active",
                "initiative": 5,
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
                "position": {"x": 5, "y": 5},
                "active_effects": [],
                "turn_resources": {},
            },
        ],
    )


def _ctx(variant: str = "image") -> dict:
    return {
        "spell_canonical_key": "minor_illusion",
        "spell_name": "Ilusão Menor",
        "slot_level": 0,
        "spell_level": 0,
        "spell_mode": "utility",
        "selected_variant_key": variant,
    }


class TestMinorIllusionCatalogAndSemantics(unittest.TestCase):
    def _seed(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        return {s["canonicalKey"]: s for s in data.get("spells", [])}

    def test_seed_has_minor_illusion_as_utility_anchor_point(self):
        s = self._seed()["minor_illusion"]
        self.assertEqual(s["level"], 0)
        self.assertEqual(s["selectionType"], "point")
        self.assertEqual(s["targetAnchor"], "selected_point")
        self.assertEqual(s["resolutionType"], "utility_anchor")
        self.assertFalse(s["concentration"])
        self.assertNotIn("damageDice", s)

    def test_targeting_semantics_use_caster_origin(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "minor_illusion"})
        self.assertEqual(sem.selection_type, "point")
        self.assertEqual(sem.origin_type, "caster")
        self.assertEqual(sem.target_anchor, "selected_point")


class TestMinorIllusionAutomation(unittest.IsolatedAsyncioTestCase):
    async def _cast(self, state: CombatState, *, variant: str = "image", description: str = "caixa", x: int = 4, y: int = 4, req_variant: str | None = None):
        if req_variant is None:
            req_variant = variant
        req = SimpleNamespace(
            anchor_cell=SimpleNamespace(x=x, y=y),
            variant_key=req_variant,
            description=description,
        )
        return await CombatService._cast_minor_illusion_automation(
            MagicMock(),
            "s1",
            attacker=state.participants[0],
            attacker_model=MagicMock(),
            actor_user_id="u1",
            is_gm=False,
            req=req,
            state=state,
            spell_context=_ctx(variant),
            target_participant=None,
        )

    async def test_cast_image_creates_anchor_with_metadata(self):
        state = _make_state()
        await self._cast(state, variant="image", description="  caixa ilusoria  ")
        anchors = get_spell_anchors_for_owner(state, "p1")
        self.assertEqual(len(anchors), 1)
        a = anchors[0]
        self.assertEqual(a["source_spell_key"], "minor_illusion")
        self.assertEqual(a["render_kind"], "minor_illusion")
        self.assertEqual(a["remaining_rounds"], 10)
        self.assertEqual(a["metadata"]["illusion_kind"], "image")
        self.assertEqual(a["metadata"]["description"], "caixa ilusoria")
        self.assertFalse(a["metadata"]["blocks_movement"])
        self.assertFalse(a["metadata"]["blocks_los"])
        self.assertFalse(a["metadata"]["blocks_loe"])

    async def test_cast_sound_creates_anchor(self):
        state = _make_state()
        await self._cast(state, variant="sound", description="som de passos")
        anchor = get_spell_anchors_for_owner(state, "p1")[0]
        self.assertEqual(anchor["metadata"]["illusion_kind"], "sound")

    async def test_cast_accepts_occupied_cell(self):
        state = _make_state()
        await self._cast(state, variant="image", description="pedra", x=5, y=5)
        anchor = get_spell_anchors_for_owner(state, "p1")[0]
        self.assertEqual(anchor["position"], {"x": 5, "y": 5})

    async def test_variant_is_required_and_strict(self):
        state = _make_state()
        with self.assertRaises(CombatServiceError):
            req = SimpleNamespace(anchor_cell=SimpleNamespace(x=4, y=4), description="ok")
            await CombatService._cast_minor_illusion_automation(
                MagicMock(),
                "s1",
                attacker=state.participants[0],
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=_ctx("image"),
                target_participant=None,
            )
        state = _make_state()
        with self.assertRaises(CombatServiceError):
            await self._cast(state, variant="image", req_variant="Sound", description="ok")

    async def test_description_is_trimmed_and_validated(self):
        state = _make_state()
        with self.assertRaises(CombatServiceError):
            await self._cast(state, description="   ")
        state = _make_state()
        with self.assertRaises(CombatServiceError):
            await self._cast(state, description=("x" * 301))

    async def test_out_of_range_fails(self):
        state = _make_state()
        with self.assertRaises(CombatServiceError):
            await self._cast(state, x=19, y=19, description="distante")

    async def test_recast_same_caster_replaces_only_own_anchor(self):
        state = _make_state()
        await self._cast(state, variant="image", description="a", x=4, y=4)
        req_p2 = SimpleNamespace(anchor_cell=SimpleNamespace(x=6, y=6), variant_key="sound", description="b")
        await CombatService._cast_minor_illusion_automation(
            MagicMock(),
            "s1",
            attacker=state.participants[1],
            attacker_model=MagicMock(),
            actor_user_id="u2",
            is_gm=False,
            req=req_p2,
            state=state,
            spell_context=_ctx("sound"),
            target_participant=None,
        )
        await self._cast(state, variant="sound", description="novo", x=7, y=7)
        self.assertEqual(len(get_spell_anchors_for_owner(state, "p1")), 1)
        self.assertEqual(len(get_spell_anchors_for_owner(state, "p2")), 1)
        self.assertEqual(get_spell_anchors_for_owner(state, "p1")[0]["position"], {"x": 7, "y": 7})
        self.assertEqual(get_spell_anchors_for_owner(state, "p2")[0]["position"], {"x": 6, "y": 6})

    async def test_does_not_add_participant(self):
        state = _make_state()
        before = len(state.participants)
        await self._cast(state, description="objeto")
        self.assertEqual(len(state.participants), before)

    async def test_expires_in_ten_turn_starts(self):
        state = _make_state()
        await self._cast(state, description="objeto")
        for _ in range(9):
            expired = tick_spell_anchors_for_turn(state, participant_id="p1", trigger="turn_start")
            self.assertEqual(expired, [])
        expired = tick_spell_anchors_for_turn(state, participant_id="p1", trigger="turn_start")
        self.assertEqual(len(expired), 1)
        self.assertEqual(expired[0]["source_spell_key"], "minor_illusion")
        self.assertEqual(get_spell_anchors_for_owner(state, "p1"), [])
