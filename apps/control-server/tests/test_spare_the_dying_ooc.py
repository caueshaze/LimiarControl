from __future__ import annotations

import json
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.schemas.session_state import OutOfCombatCastRequest
from app.services.out_of_combat_cast import (
    _is_ooc_utility_spell,
    build_persisted_effects,
    check_out_of_combat_cast_eligibility,
    has_castable_effects,
)
from app.services.ooc_spell_cast_service import (
    cast_spell_out_of_combat_for_player as _cast_spell_out_of_combat_for_player,
)
from app.api.routes.sessions.state import cast_spell_out_of_combat


_SEED_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
)


def _load_seed_entry():
    with open(_SEED_PATH, encoding="utf-8") as f:
        payload = json.load(f)
    spells = payload["spells"] if isinstance(payload, dict) else payload
    return next(
        (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "spare_the_dying"),
        None,
    )


def _make_user(user_id: str = "user-1"):
    user = MagicMock()
    user.id = user_id
    return user


def _make_entry():
    return MagicMock(party_id="party-1", campaign_id="camp-1")


def _make_campaign_spell():
    spell = MagicMock()
    spell.canonical_key = "spare_the_dying"
    spell.level = 0
    spell.concentration = False
    spell.out_of_combat_castable = True
    spell.out_of_combat_target = "self_or_ally"
    spell.effects_json = []
    spell.variants_json = []
    spell.name_pt = "Poupar os Moribundos"
    spell.name_en = "Spare the Dying"
    spell.is_enabled = True
    spell.campaign_id = "camp-1"
    return spell


def _make_caster_state(
    *,
    current_hp: int = 10,
    max_hp: int = 14,
    death_saves: dict | None = None,
    player_user_id: str = "caster-1",
):
    state = MagicMock()
    state.state_json = {
        "currentHP": current_hp,
        "maxHP": max_hp,
        "deathSaves": death_saves if death_saves is not None else {"successes": 0, "failures": 0},
        "spellcasting": {
            "slots": {},
            "spells": [
                {"id": "spell-std-1", "canonicalKey": "spare_the_dying", "level": 0, "prepared": True},
            ],
        },
    }
    state.id = "ss-caster"
    state.session_id = "session-1"
    state.player_user_id = player_user_id
    state.created_at = "2026-01-01T00:00:00+00:00"
    state.updated_at = None
    return state


def _make_target_state(
    *,
    current_hp: int = 0,
    max_hp: int = 12,
    death_saves: dict | None = None,
    player_user_id: str = "target-2",
):
    state = MagicMock()
    state.state_json = {
        "currentHP": current_hp,
        "maxHP": max_hp,
        "deathSaves": death_saves if death_saves is not None else {"successes": 1, "failures": 1},
    }
    state.id = "ss-target"
    state.session_id = "session-1"
    state.player_user_id = player_user_id
    state.created_at = "2026-01-01T00:00:00+00:00"
    state.updated_at = None
    return state


def _make_db(caster_state, campaign_spell, target_state=None):
    db = MagicMock()
    results = [caster_state]
    if target_state is not None:
        results.append(target_state)
    results.append(campaign_spell)
    call_count = [0]

    def exec_side(*args, **kwargs):
        r = MagicMock()
        idx = call_count[0]
        if idx < len(results):
            r.first.return_value = results[idx]
        else:
            r.first.return_value = None
        r.all.return_value = []
        call_count[0] += 1
        return r

    db.exec.side_effect = exec_side
    return db


def _make_injected(caster_state, *, resolve_actor=("member-1", "Caster One")):
    """Build the dependency overrides that the OOC cast reads.

    Issue #396: instead of patching `app.api.routes.sessions.state.X`, tests inject
    these fakes by keyword into `_cast_spell_out_of_combat_for_player`. Returned as a
    dict so tests can assert on individual mocks (e.g. ``record_session_activity``).
    """
    return {
        "ensure_session_state": MagicMock(return_value=caster_state),
        "finalize_session_state_data": lambda d, **kwargs: d,
        "publish_state_update": AsyncMock(),
        "to_state_read": MagicMock(return_value=MagicMock()),
        "record_session_activity": MagicMock(),
        "_prune_out_of_combat_session_activity": MagicMock(),
        "_resolve_ooc_activity_actor": MagicMock(return_value=resolve_actor),
        "get_game_time_seconds": MagicMock(return_value=100),
    }


async def _cast_ooc(
    *,
    db,
    injected,
    caster_user_id: str = "caster-1",
    target_player_user_id: str | None = "target-2",
):
    """Call the OOC cast directly with injected deps (self-cast path)."""
    req = OutOfCombatCastRequest(
        spellId="spell-std-1",
        slotLevel=None,
        targetPlayerUserId=target_player_user_id,
    )
    return await _cast_spell_out_of_combat_for_player(
        entry=_make_entry(),
        session_id="session-1",
        req=req,
        actor_user=_make_user(caster_user_id),
        caster_user_id=caster_user_id,
        session=db,
        cast_by_gm=False,
        **injected,
    )


class OocAvailabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entry = _load_seed_entry()

    def test_out_of_combat_castable_true(self):
        self.assertTrue(self.entry.get("outOfCombatCastable"))

    def test_out_of_combat_target_self_or_ally(self):
        self.assertEqual(self.entry.get("outOfCombatTarget"), "self_or_ally")

    def test_in_special_ooc_utility_spells(self):
        self.assertTrue(_is_ooc_utility_spell("spare_the_dying"))

    def test_has_castable_effects(self):
        spell = _make_campaign_spell()
        self.assertTrue(has_castable_effects(spell))

    def test_build_persisted_effects_returns_empty(self):
        spell = _make_campaign_spell()
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="u1",
            target_user_id="u2",
            variant_key=None,
            game_time_seconds=0,
        )
        self.assertEqual(effects, [])

    def test_eligibility_passes(self):
        spell = _make_campaign_spell()
        caster_state_json = {"spellcasting": {"slots": {}, "spells": []}}
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json=caster_state_json,
            slot_level=None,
            variant_key=None,
            out_of_combat_target="self_or_ally",
            target_user_id="target-2",
            caster_user_id="caster-1",
            target_state_json={"currentHP": 0},
        )
        self.assertTrue(ok)
        self.assertIsNone(reason)


class OocPlayerTargetSuccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_ally_target_stabilized(self):
        caster_state = _make_caster_state(player_user_id="caster-1")
        target_state = _make_target_state(
            current_hp=0,
            death_saves={"successes": 1, "failures": 1},
            player_user_id="target-2",
        )
        db = _make_db(caster_state, _make_campaign_spell(), target_state)
        await _cast_ooc(db=db, injected=_make_injected(caster_state))

        self.assertEqual(target_state.state_json["deathSaves"]["successes"], 3)
        self.assertEqual(target_state.state_json["deathSaves"]["failures"], 0)

    async def test_hp_remains_zero(self):
        caster_state = _make_caster_state(player_user_id="caster-1")
        target_state = _make_target_state(current_hp=0, player_user_id="target-2")
        db = _make_db(caster_state, _make_campaign_spell(), target_state)
        await _cast_ooc(db=db, injected=_make_injected(caster_state))

        self.assertEqual(target_state.state_json["currentHP"], 0)

    async def test_no_active_spell_effects_created(self):
        caster_state = _make_caster_state(player_user_id="caster-1")
        target_state = _make_target_state(current_hp=0, player_user_id="target-2")
        db = _make_db(caster_state, _make_campaign_spell(), target_state)
        await _cast_ooc(db=db, injected=_make_injected(caster_state))

        effects = target_state.state_json.get("active_spell_effects", [])
        self.assertEqual(effects, [])

    async def test_activity_recorded(self):
        caster_state = _make_caster_state(player_user_id="caster-1")
        target_state = _make_target_state(current_hp=0, player_user_id="target-2")
        db = _make_db(caster_state, _make_campaign_spell(), target_state)
        injected = _make_injected(caster_state)
        await _cast_ooc(db=db, injected=injected)

        mock_record = injected["record_session_activity"]
        mock_record.assert_called_once()
        payload = mock_record.call_args.kwargs.get("payload") or mock_record.call_args.args[3]
        self.assertTrue(payload.get("spare_the_dying_stabilized"))

    async def test_target_state_published(self):
        caster_state = _make_caster_state(player_user_id="caster-1")
        target_state = _make_target_state(current_hp=0, player_user_id="target-2")
        db = _make_db(caster_state, _make_campaign_spell(), target_state)
        injected = _make_injected(caster_state)
        await _cast_ooc(db=db, injected=injected)

        published_ids = [call.args[1] for call in injected["publish_state_update"].call_args_list]
        self.assertIn("target-2", published_ids)


class OocMissingDeathSavesTests(unittest.IsolatedAsyncioTestCase):
    async def _stabilize_with_target_json(self, target_json):
        caster_state = _make_caster_state(player_user_id="caster-1")
        target_state = _make_target_state(current_hp=0, player_user_id="target-2")
        target_state.state_json = target_json
        db = _make_db(caster_state, _make_campaign_spell(), target_state)
        await _cast_ooc(db=db, injected=_make_injected(caster_state))
        return target_state

    async def test_missing_death_saves_stabilized(self):
        target_state = await self._stabilize_with_target_json({"currentHP": 0, "maxHP": 12})
        self.assertEqual(target_state.state_json["deathSaves"]["successes"], 3)
        self.assertEqual(target_state.state_json["deathSaves"]["failures"], 0)

    async def test_none_death_saves_stabilized(self):
        target_state = await self._stabilize_with_target_json(
            {"currentHP": 0, "maxHP": 12, "deathSaves": None}
        )
        self.assertEqual(target_state.state_json["deathSaves"]["successes"], 3)
        self.assertEqual(target_state.state_json["deathSaves"]["failures"], 0)

    async def test_empty_dict_death_saves_stabilized(self):
        target_state = await self._stabilize_with_target_json(
            {"currentHP": 0, "maxHP": 12, "deathSaves": {}}
        )
        self.assertEqual(target_state.state_json["deathSaves"]["successes"], 3)
        self.assertEqual(target_state.state_json["deathSaves"]["failures"], 0)


class OocSelfTargetTests(unittest.IsolatedAsyncioTestCase):
    async def test_caster_at_zero_hp_stabilizes_self(self):
        caster_state = _make_caster_state(
            current_hp=0,
            death_saves={"successes": 0, "failures": 2},
            player_user_id="caster-1",
        )
        db = _make_db(caster_state, _make_campaign_spell())
        await _cast_ooc(
            db=db,
            injected=_make_injected(caster_state),
            target_player_user_id=None,
        )

        self.assertEqual(caster_state.state_json["deathSaves"]["successes"], 3)
        self.assertEqual(caster_state.state_json["deathSaves"]["failures"], 0)
        self.assertEqual(caster_state.state_json["currentHP"], 0)


class OocInvalidTargetTests(unittest.IsolatedAsyncioTestCase):
    async def test_hp_above_zero_rejected(self):
        caster_state = _make_caster_state(player_user_id="caster-1")
        target_state = _make_target_state(
            current_hp=5,
            death_saves={"successes": 0, "failures": 0},
            player_user_id="target-2",
        )
        target_json_before = dict(target_state.state_json)
        db = _make_db(caster_state, _make_campaign_spell(), target_state)

        with self.assertRaises(HTTPException) as ctx:
            await _cast_ooc(db=db, injected=_make_injected(caster_state))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("0 HP", ctx.exception.detail)
        self.assertEqual(target_state.state_json, target_json_before)

    async def test_dead_target_rejected(self):
        caster_state = _make_caster_state(player_user_id="caster-1")
        target_state = _make_target_state(
            current_hp=0,
            death_saves={"successes": 0, "failures": 3},
            player_user_id="target-2",
        )
        target_json_before = dict(target_state.state_json)
        db = _make_db(caster_state, _make_campaign_spell(), target_state)

        with self.assertRaises(HTTPException) as ctx:
            await _cast_ooc(db=db, injected=_make_injected(caster_state))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("mortas", ctx.exception.detail)
        self.assertEqual(target_state.state_json, target_json_before)

    async def test_invalid_cast_no_activity_log(self):
        caster_state = _make_caster_state(player_user_id="caster-1")
        target_state = _make_target_state(
            current_hp=5,
            death_saves={"successes": 0, "failures": 0},
            player_user_id="target-2",
        )
        db = _make_db(caster_state, _make_campaign_spell(), target_state)
        injected = _make_injected(caster_state)

        with self.assertRaises(HTTPException):
            await _cast_ooc(db=db, injected=injected)

        injected["record_session_activity"].assert_not_called()


class OocResourceSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_cantrip_does_not_consume_slot(self):
        caster_state = _make_caster_state(player_user_id="caster-1")
        target_state = _make_target_state(current_hp=0, player_user_id="target-2")
        db = _make_db(caster_state, _make_campaign_spell(), target_state)
        await _cast_ooc(db=db, injected=_make_injected(caster_state))

        slots = caster_state.state_json.get("spellcasting", {}).get("slots", {})
        self.assertEqual(slots, {})

    async def test_no_concentration_group(self):
        caster_state = _make_caster_state(player_user_id="caster-1")
        target_state = _make_target_state(current_hp=0, player_user_id="target-2")
        db = _make_db(caster_state, _make_campaign_spell(), target_state)
        injected = _make_injected(caster_state)
        await _cast_ooc(db=db, injected=injected)

        mock_record = injected["record_session_activity"]
        mock_record.assert_called_once()
        payload = mock_record.call_args.kwargs.get("payload") or mock_record.call_args.args[3]
        self.assertIsNone(payload.get("concentration_group"))


class OocEndpointSmokeTests(unittest.IsolatedAsyncioTestCase):
    """Smoke test exercising the real endpoint → wrapper → heavy-fn wiring.

    This is the one place still patching `state.X`: it confirms the route resolves
    the injectable dependencies from the module at call time (defaults preserved),
    so the thin endpoint keeps working after issue #396.
    """

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.services.ooc_spell_cast_service.ensure_session_state")
    @patch("app.services.ooc_spell_cast_service._resolve_ooc_activity_actor", return_value=("member-1", "Caster One"))
    @patch("app.services.ooc_spell_cast_service.finalize_session_state_data", side_effect=lambda d, **kwargs: d)
    @patch("app.services.ooc_spell_cast_service.publish_state_update", new_callable=AsyncMock)
    @patch("app.services.ooc_spell_cast_service.to_state_read")
    @patch("app.services.ooc_spell_cast_service._prune_out_of_combat_session_activity")
    @patch("app.services.ooc_spell_cast_service.record_session_activity")
    @patch("app.services.ooc_spell_cast_service.get_game_time_seconds", return_value=100)
    async def test_endpoint_stabilizes_ally(
        self, mock_time, mock_record, mock_prune, mock_to_state,
        mock_publish, mock_finalize, mock_resolve_actor, mock_ensure, mock_require, mock_get_entry,
    ):
        mock_get_entry.return_value = _make_entry()
        caster_state = _make_caster_state(player_user_id="caster-1")
        target_state = _make_target_state(
            current_hp=0,
            death_saves={"successes": 1, "failures": 1},
            player_user_id="target-2",
        )
        db = _make_db(caster_state, _make_campaign_spell(), target_state)
        mock_ensure.return_value = caster_state
        mock_to_state.return_value = MagicMock()

        req = OutOfCombatCastRequest(
            spellId="spell-std-1", slotLevel=None, targetPlayerUserId="target-2",
        )
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=_make_user("caster-1"), session=db,
        )

        self.assertEqual(target_state.state_json["deathSaves"]["successes"], 3)
        mock_record.assert_called_once()


if __name__ == "__main__":
    unittest.main()
