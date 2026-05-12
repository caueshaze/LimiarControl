from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.combat import CombatPhase, CombatState
from app.models.inventory import InventoryItem
from app.models.session import Session as CampaignSession
from app.services.combat import CombatService
from app.services.combat_service.exceptions import CombatServiceError


def _state() -> CombatState:
    return CombatState(
        id="c1",
        session_id="s1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=[
            {
                "id": "p1",
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Lia",
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "u1",
                "position": {"x": 1, "y": 1},
                "active_effects": [],
                "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
            }
        ],
    )


def _ctx() -> dict:
    return {
        "spell_canonical_key": "mending",
        "spell_name": "Consertar",
        "slot_level": 0,
        "spell_level": 0,
        "spell_mode": "utility",
    }


class _ExecResult:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value


class TestMendingCatalog(unittest.TestCase):
    def test_seed_entry(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        self.assertIn("mending", spells)
        s = spells["mending"]
        self.assertEqual(s["level"], 0)
        self.assertEqual(s["resolutionType"], "item_condition_repair")
        self.assertEqual(s["rangeKind"], "touch")
        self.assertEqual(s["rangeMeters"], 1.5)
        self.assertNotIn("damageDice", s)
        self.assertNotIn("saveAbility", s)


class TestMendingAutomation(unittest.IsolatedAsyncioTestCase):
    def _session(self) -> CampaignSession:
        return CampaignSession(
            id="s1",
            campaign_id="c1",
            party_id="party-1",
            number=1,
            sequence_number=1,
            title="S1",
            status="ACTIVE",
        )

    def _item(self, *, tags: list[str]) -> InventoryItem:
        now = datetime.now(timezone.utc)
        return InventoryItem(
            id="inv-1",
            campaign_id="c1",
            party_id="party-1",
            member_id="m1",
            item_id="it-1",
            quantity=1,
            is_equipped=False,
            notes="old",
            condition_tags=tags,
            created_at=now,
            updated_at=now,
        )

    async def test_requires_inventory_item_id(self):
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_mending_automation(
                MagicMock(),
                "s1",
                attacker=_state().participants[0],
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=SimpleNamespace(),
                state=_state(),
                spell_context=_ctx(),
                target_participant=None,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_not_found_and_permission_paths(self):
        db = MagicMock()
        db.exec.side_effect = [_ExecResult(self._session()), _ExecResult(None)]
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_mending_automation(
                db, "s1",
                attacker=_state().participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False,
                req=SimpleNamespace(inventory_item_id="inv-1"),
                state=_state(), spell_context=_ctx(), target_participant=None,
            )
        self.assertEqual(ctx.exception.status_code, 404)

        db = MagicMock()
        db.exec.side_effect = [
            _ExecResult(self._session()),
            _ExecResult(self._item(tags=["broken"])),
            _ExecResult(None),
        ]
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_mending_automation(
                db, "s1",
                attacker=_state().participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False,
                req=SimpleNamespace(inventory_item_id="inv-1"),
                state=_state(), spell_context=_ctx(), target_participant=None,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_removes_broken_and_returns_inventory_with_labels(self):
        db = MagicMock()
        item = self._item(tags=["broken"])
        member = SimpleNamespace(id="m1")
        db.exec.side_effect = [
            _ExecResult(self._session()),
            _ExecResult(item),
            _ExecResult(member),
        ]
        result = await CombatService._cast_mending_automation(
            db, "s1",
            attacker=_state().participants[0], attacker_model=MagicMock(),
            actor_user_id="u1", is_gm=False,
            req=SimpleNamespace(inventory_item_id="inv-1"),
            state=_state(), spell_context=_ctx(), target_participant=None,
        )
        self.assertTrue(result["changed"])
        self.assertEqual(result["removedTags"], ["broken"])
        self.assertEqual(item.condition_tags, [])
        self.assertIn("inventoryItem", result)
        self.assertEqual(result["inventoryItem"]["conditionTags"], [])
        self.assertEqual(result["inventoryItem"]["conditionTagLabels"], [])

    async def test_idempotent_when_broken_absent(self):
        db = MagicMock()
        item = self._item(tags=[])
        member = SimpleNamespace(id="m1")
        db.exec.side_effect = [
            _ExecResult(self._session()),
            _ExecResult(item),
            _ExecResult(member),
        ]
        result = await CombatService._cast_mending_automation(
            db, "s1",
            attacker=_state().participants[0], attacker_model=MagicMock(),
            actor_user_id="u1", is_gm=False,
            req=SimpleNamespace(inventory_item_id="inv-1"),
            state=_state(), spell_context=_ctx(), target_participant=None,
        )
        self.assertFalse(result["changed"])
        self.assertEqual(result["removedTags"], [])
        self.assertEqual(result["inventoryItem"]["conditionTags"], [])
        self.assertEqual(result["inventoryItem"]["conditionTagLabels"], [])

