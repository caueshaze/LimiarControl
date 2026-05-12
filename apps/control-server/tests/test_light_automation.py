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
from app.models.session_state import SessionState
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
            },
            {
                "id": "p2",
                "ref_id": "player-2",
                "kind": "player",
                "display_name": "Theo",
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "u2",
                "position": {"x": 2, "y": 1},
                "active_effects": [],
                "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
            },
        ],
    )


def _ctx() -> dict:
    return {
        "spell_canonical_key": "light",
        "spell_name": "Luz",
        "slot_level": 0,
        "spell_level": 0,
        "spell_mode": "utility",
    }


class _ExecResult:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value


class TestLightCatalog(unittest.TestCase):
    def test_seed_entry(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        self.assertIn("light", spells)
        s = spells["light"]
        self.assertEqual(s["level"], 0)
        self.assertEqual(s["school"], "evocation")
        self.assertEqual(s["rangeMeters"], 1.5)
        self.assertEqual(s["duration"], "1 hour")
        self.assertEqual(s["resolutionType"], "narrative_item_effect")
        self.assertNotIn("damageDice", s)
        self.assertNotIn("saveAbility", s)


class TestLightAutomation(unittest.IsolatedAsyncioTestCase):
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

    def _item(self, *, item_id: str = "inv-1", tags: list[str] | None = None) -> InventoryItem:
        now = datetime.now(timezone.utc)
        return InventoryItem(
            id=item_id,
            campaign_id="c1",
            party_id="party-1",
            member_id="m1",
            item_id="it-1",
            quantity=1,
            is_equipped=False,
            notes="old",
            condition_tags=tags or [],
            created_at=now,
            updated_at=now,
        )

    async def test_xor_validation(self):
        model = SessionState(id="st1", session_id="s1", player_user_id="player-1", state_json={})
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_light_automation(
                MagicMock(), "s1",
                attacker=_state().participants[0], attacker_model=model,
                actor_user_id="u1", is_gm=False, req=SimpleNamespace(),
                state=_state(), spell_context=_ctx(), target_participant=None,
            )
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_light_automation(
                MagicMock(), "s1",
                attacker=_state().participants[0], attacker_model=model,
                actor_user_id="u1", is_gm=False,
                req=SimpleNamespace(inventory_item_id="inv-1", description="x"),
                state=_state(), spell_context=_ctx(), target_participant=None,
            )

    async def test_description_validation(self):
        model = SessionState(id="st1", session_id="s1", player_user_id="player-1", state_json={})
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_light_automation(
                MagicMock(), "s1",
                attacker=_state().participants[0], attacker_model=model,
                actor_user_id="u1", is_gm=False, req=SimpleNamespace(description="   "),
                state=_state(), spell_context=_ctx(), target_participant=None,
            )
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_light_automation(
                MagicMock(), "s1",
                attacker=_state().participants[0], attacker_model=model,
                actor_user_id="u1", is_gm=False, req=SimpleNamespace(description="x" * 301),
                state=_state(), spell_context=_ctx(), target_participant=None,
            )

    async def test_item_not_found_and_forbidden(self):
        model = SessionState(id="st1", session_id="s1", player_user_id="player-1", state_json={})
        db = MagicMock()
        db.exec.side_effect = [_ExecResult(self._session()), _ExecResult(None)]
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_light_automation(
                db, "s1",
                attacker=_state().participants[0], attacker_model=model,
                actor_user_id="u1", is_gm=False, req=SimpleNamespace(inventory_item_id="inv-1"),
                state=_state(), spell_context=_ctx(), target_participant=None,
            )
        self.assertEqual(ctx.exception.status_code, 404)

        db = MagicMock()
        db.exec.side_effect = [
            _ExecResult(self._session()),
            _ExecResult(self._item()),
            _ExecResult(None),
        ]
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_light_automation(
                db, "s1",
                attacker=_state().participants[0], attacker_model=model,
                actor_user_id="u1", is_gm=False, req=SimpleNamespace(inventory_item_id="inv-1"),
                state=_state(), spell_context=_ctx(), target_participant=None,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_cast_with_item_creates_visual_effect(self):
        model = SessionState(id="st1", session_id="s1", player_user_id="player-1", state_json={})
        db = MagicMock()
        db.exec.side_effect = [
            _ExecResult(self._session()),
            _ExecResult(self._item(item_id="inv-1", tags=["broken"])),
            _ExecResult(SimpleNamespace(id="m1")),
            _ExecResult(None),
        ]
        result = await CombatService._cast_light_automation(
            db, "s1",
            attacker=_state().participants[0], attacker_model=model,
            actor_user_id="u1", is_gm=False, req=SimpleNamespace(inventory_item_id="inv-1"),
            state=_state(), spell_context=_ctx(), target_participant=None,
        )
        effects = model.state_json.get("active_spell_effects", [])
        self.assertEqual(len(effects), 1)
        meta = effects[0]["metadata"]
        self.assertEqual(meta["source_spell_key"], "light")
        self.assertFalse(meta["mechanical"])
        self.assertTrue(meta["narrative"])
        self.assertTrue(meta["visual"])
        self.assertTrue(meta["visible_to_all"])
        self.assertEqual(meta["inventory_item_id"], "inv-1")
        self.assertEqual(meta["bright_light_meters"], 6)
        self.assertEqual(meta["dim_light_meters"], 6)
        self.assertIn("created_effect_id", result)

    async def test_recast_same_item_is_deduped_even_across_casters(self):
        model = SessionState(id="st1", session_id="s1", player_user_id="player-1", state_json={})
        db = MagicMock()
        db.exec.side_effect = [
            _ExecResult(self._session()),
            _ExecResult(self._item(item_id="inv-1")),
            _ExecResult(SimpleNamespace(id="m1")),
            _ExecResult(None),
            _ExecResult(self._session()),
            _ExecResult(self._item(item_id="inv-1")),
            _ExecResult(SimpleNamespace(id="m2")),
            _ExecResult(None),
        ]
        await CombatService._cast_light_automation(
            db, "s1",
            attacker=_state().participants[0], attacker_model=model,
            actor_user_id="u1", is_gm=False, req=SimpleNamespace(inventory_item_id="inv-1"),
            state=_state(), spell_context=_ctx(), target_participant=None,
        )
        await CombatService._cast_light_automation(
            db, "s1",
            attacker=_state().participants[1], attacker_model=model,
            actor_user_id="u2", is_gm=True, req=SimpleNamespace(inventory_item_id="inv-1"),
            state=_state(), spell_context=_ctx(), target_participant=None,
        )
        effects = model.state_json.get("active_spell_effects", [])
        on_item = [
            e for e in effects
            if isinstance(e, dict)
            and isinstance(e.get("metadata"), dict)
            and e["metadata"].get("source_spell_key") == "light"
            and e["metadata"].get("inventory_item_id") == "inv-1"
        ]
        self.assertEqual(len(on_item), 1)

    async def test_item_recast_does_not_remove_description_effect(self):
        model = SessionState(id="st1", session_id="s1", player_user_id="player-1", state_json={})
        db = MagicMock()
        await CombatService._cast_light_automation(
            db, "s1",
            attacker=_state().participants[0], attacker_model=model,
            actor_user_id="u1", is_gm=False, req=SimpleNamespace(description="pedra no chao"),
            state=_state(), spell_context=_ctx(), target_participant=None,
        )
        db.exec.side_effect = [
            _ExecResult(self._session()),
            _ExecResult(self._item(item_id="inv-1")),
            _ExecResult(SimpleNamespace(id="m1")),
            _ExecResult(None),
        ]
        await CombatService._cast_light_automation(
            db, "s1",
            attacker=_state().participants[0], attacker_model=model,
            actor_user_id="u1", is_gm=False, req=SimpleNamespace(inventory_item_id="inv-1"),
            state=_state(), spell_context=_ctx(), target_participant=None,
        )
        effects = model.state_json.get("active_spell_effects", [])
        desc = [e for e in effects if e.get("metadata", {}).get("inventory_item_id") is None]
        item = [e for e in effects if e.get("metadata", {}).get("inventory_item_id") == "inv-1"]
        self.assertEqual(len(desc), 1)
        self.assertEqual(len(item), 1)
