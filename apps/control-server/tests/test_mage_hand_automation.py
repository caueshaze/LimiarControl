from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.combat_service.exceptions import CombatServiceError
from app.services.combat_service.spell_anchors import (
    get_spell_anchor_by_id,
    get_spell_anchors_for_owner,
)
from app.services.spell_targeting_semantics import (
    explicit_spell_targeting_overrides,
    resolve_spell_targeting_semantics,
)


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
                "display_name": "Wizard A",
                "initiative": 20,
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-1",
                "position": {"x": 2, "y": 2},
                "active_effects": [],
                "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
            },
            {
                "id": "p2",
                "ref_id": "player-2",
                "kind": "player",
                "display_name": "Wizard B",
                "initiative": 10,
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-2",
                "position": {"x": 3, "y": 3},
                "active_effects": [],
                "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
            },
            {
                "id": "e1",
                "ref_id": "enemy-1",
                "kind": "session_entity",
                "display_name": "Goblin",
                "initiative": 5,
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
                "position": {"x": 5, "y": 5},
                "active_effects": [],
                "turn_resources": {},
            },
        ],
    )


def _spell_context() -> dict:
    return {
        "spell_canonical_key": "mage_hand",
        "spell_name": "Mãos Mágicas",
        "slot_level": 0,
        "spell_level": 0,
        "spell_mode": "utility",
    }


class TestMageHandCatalogAndSemantics(unittest.TestCase):
    def _load_seed(self):
        seed_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(seed_path), encoding="utf-8") as f:
            data = json.load(f)
        return {s["canonicalKey"]: s for s in data.get("spells", [])}

    def test_exists_in_seed(self):
        catalog = self._load_seed()
        self.assertIn("mage_hand", catalog)
        self.assertEqual(catalog["mage_hand"]["level"], 0)
        self.assertEqual(catalog["mage_hand"]["selectionType"], "point")

    def test_registered_in_targeting_overrides(self):
        overrides = explicit_spell_targeting_overrides()
        self.assertIn("mage_hand", overrides)
        semantics = resolve_spell_targeting_semantics({"canonicalKey": "mage_hand"})
        self.assertEqual(semantics.selection_type, "point")
        self.assertEqual(semantics.target_anchor, "selected_point")


class TestMageHandAutomation(unittest.IsolatedAsyncioTestCase):
    async def test_cast_in_occupied_cell_creates_anchor(self):
        state = _make_state()
        req = SimpleNamespace(anchor_cell=SimpleNamespace(x=5, y=5))
        await CombatService._cast_mage_hand_automation(
            MagicMock(), "session-1",
            attacker=state.participants[0],
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=req,
            state=state,
            spell_context=_spell_context(),
            target_participant=None,
        )
        anchors = get_spell_anchors_for_owner(state, "p1")
        self.assertEqual(len(anchors), 1)
        self.assertEqual(anchors[0]["source_spell_key"], "mage_hand")
        self.assertEqual(anchors[0]["position"], {"x": 5, "y": 5})
        self.assertEqual(anchors[0]["remaining_rounds"], 10)

    async def test_mage_hand_is_not_added_to_participants(self):
        state = _make_state()
        req = SimpleNamespace(anchor_cell=SimpleNamespace(x=4, y=4))
        before = len(state.participants)
        await CombatService._cast_mage_hand_automation(
            MagicMock(), "session-1",
            attacker=state.participants[0],
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=req,
            state=state,
            spell_context=_spell_context(),
            target_participant=None,
        )
        self.assertEqual(len(state.participants), before)

    async def test_recast_same_caster_does_not_remove_other_caster_anchor(self):
        state = _make_state()
        req_a1 = SimpleNamespace(anchor_cell=SimpleNamespace(x=4, y=4))
        req_b = SimpleNamespace(anchor_cell=SimpleNamespace(x=6, y=6))
        req_a2 = SimpleNamespace(anchor_cell=SimpleNamespace(x=7, y=7))
        db = MagicMock()
        await CombatService._cast_mage_hand_automation(
            db, "session-1", attacker=state.participants[0], attacker_model=MagicMock(),
            actor_user_id="user-1", is_gm=False, req=req_a1, state=state, spell_context=_spell_context(), target_participant=None,
        )
        await CombatService._cast_mage_hand_automation(
            db, "session-1", attacker=state.participants[1], attacker_model=MagicMock(),
            actor_user_id="user-2", is_gm=False, req=req_b, state=state, spell_context=_spell_context(), target_participant=None,
        )
        await CombatService._cast_mage_hand_automation(
            db, "session-1", attacker=state.participants[0], attacker_model=MagicMock(),
            actor_user_id="user-1", is_gm=False, req=req_a2, state=state, spell_context=_spell_context(), target_participant=None,
        )
        anchors_a = get_spell_anchors_for_owner(state, "p1")
        anchors_b = get_spell_anchors_for_owner(state, "p2")
        self.assertEqual(len(anchors_a), 1)
        self.assertEqual(len(anchors_b), 1)
        self.assertEqual(anchors_a[0]["position"], {"x": 7, "y": 7})
        self.assertEqual(anchors_b[0]["position"], {"x": 6, "y": 6})

    async def test_move_to_occupied_cell_works(self):
        state = _make_state()
        req = SimpleNamespace(anchor_cell=SimpleNamespace(x=4, y=4))
        await CombatService._cast_mage_hand_automation(
            MagicMock(), "session-1",
            attacker=state.participants[0],
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=req,
            state=state,
            spell_context=_spell_context(),
            target_participant=None,
        )
        anchor = get_spell_anchors_for_owner(state, "p1")[0]

        action_req = SimpleNamespace(
            actor_participant_id="p1",
            anchor_id=anchor["id"],
            destination={"x": 5, "y": 5},
        )
        with (
            patch.object(CombatService, "get_state", return_value=state),
            patch.object(CombatService, "_emit_state", new=AsyncMock()),
            patch.object(CombatService, "_emit_log", new=AsyncMock()),
        ):
            result = await CombatService.use_mage_hand_action(
                MagicMock(), "session-1", action_req, actor_user_id="user-1", is_gm=False
            )
        self.assertEqual(result["position"], {"x": 5, "y": 5})
        moved = get_spell_anchor_by_id(state, anchor["id"])
        self.assertEqual(moved["position"], {"x": 5, "y": 5})

    async def test_move_by_non_owner_fails(self):
        state = _make_state()
        req = SimpleNamespace(anchor_cell=SimpleNamespace(x=4, y=4))
        await CombatService._cast_mage_hand_automation(
            MagicMock(), "session-1",
            attacker=state.participants[0],
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=req,
            state=state,
            spell_context=_spell_context(),
            target_participant=None,
        )
        anchor = get_spell_anchors_for_owner(state, "p1")[0]
        action_req = SimpleNamespace(
            actor_participant_id="p2",
            anchor_id=anchor["id"],
            destination={"x": 5, "y": 5},
        )
        with patch.object(CombatService, "get_state", return_value=state):
            with self.assertRaises(CombatServiceError):
                await CombatService.use_mage_hand_action(
                    MagicMock(), "session-1", action_req, actor_user_id="user-2", is_gm=False
                )

