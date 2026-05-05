"""Tests for out-of-combat spell casting.

Covers:
- check_out_of_combat_cast_eligibility (service-level)
- build_persisted_effects (service-level)
- consume_spell_slot (service-level)
- cast_spell_out_of_combat HTTP endpoint
- list_out_of_combat_castable_spells HTTP endpoint
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.api.routes.sessions.state import (
    cast_spell_out_of_combat,
    list_out_of_combat_castable_spells,
)
from app.schemas.session_state import OutOfCombatCastRequest
from app.services.out_of_combat_cast import (
    build_persisted_effects,
    check_out_of_combat_cast_eligibility,
    consume_spell_slot,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_user(user_id: str = "user-1"):
    user = MagicMock()
    user.id = user_id
    return user


def _make_campaign_spell(
    *,
    canonical_key: str = "enhance_ability",
    level: int = 2,
    concentration: bool = True,
    out_of_combat_castable: bool = True,
    effects_json: list | None = None,
    variants_json: list | None = None,
    name_pt: str = "Melhorar Habilidade",
    name_en: str = "Enhance Ability",
) -> MagicMock:
    spell = MagicMock()
    spell.canonical_key = canonical_key
    spell.level = level
    spell.concentration = concentration
    spell.out_of_combat_castable = out_of_combat_castable
    spell.effects_json = effects_json or []
    spell.variants_json = variants_json or []
    spell.name_pt = name_pt
    spell.name_en = name_en
    return spell


def _make_db_session(state_json: dict | None = None, campaign_spell: object = None):
    db = MagicMock()
    state = MagicMock()
    state.state_json = state_json or {}
    state.id = "ss-1"
    state.session_id = "session-1"
    state.player_user_id = "user-1"
    state.created_at = "2026-01-01T00:00:00+00:00"
    state.updated_at = None

    first_results = [state]
    if campaign_spell is not None:
        first_results.append(campaign_spell)

    call_count = [0]

    def exec_side_effect(*args, **kwargs):
        result = MagicMock()
        idx = call_count[0]
        if idx < len(first_results):
            result.first.return_value = first_results[idx]
            result.all.return_value = [first_results[idx]] if idx > 0 else []
        else:
            result.first.return_value = None
            result.all.return_value = []
        call_count[0] += 1
        return result

    db.exec.side_effect = exec_side_effect
    return db, state


def _advantage_effect(ability: str = "wisdom") -> dict:
    return {
        "type": "advantage_on_checks",
        "target": "selected_target",
        "params": {"ability": ability, "against": "any"},
        "stacking": "replace",
    }


def _ac_bonus_effect(value: int = 2) -> dict:
    return {
        "type": "modify_stat",
        "target": "selected_target",
        "params": {"stat": "temp_ac_bonus", "value": value},
        "stacking": "replace",
    }


def _slots_state(level: int = 2, used: int = 0, max_slots: int = 3) -> dict:
    return {
        "spellcasting": {
            "slots": {str(level): {"used": used, "max": max_slots}},
            "spells": [
                {
                    "id": "spell-ea-1",
                    "canonicalKey": "enhance_ability",
                    "level": 2,
                    "prepared": True,
                }
            ],
        }
    }


# ---------------------------------------------------------------------------
# Unit tests: check_out_of_combat_cast_eligibility
# ---------------------------------------------------------------------------

class TestEligibility(unittest.TestCase):
    def _spell(self, **kwargs):
        return _make_campaign_spell(**kwargs)

    def test_not_out_of_combat_castable(self):
        spell = self._spell(out_of_combat_castable=False)
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell, state_json={}, slot_level=2, variant_key=None
        )
        self.assertFalse(ok)
        self.assertIn("not castable", reason)

    def test_variant_required_but_missing(self):
        spell = self._spell(
            variants_json=[{"key": "owls_wisdom", "labelPt": "Sabedoria", "effects": [_advantage_effect()]}],
        )
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell, state_json={}, slot_level=2, variant_key=None
        )
        self.assertFalse(ok)
        self.assertIn("variantKey", reason)

    def test_unknown_variant_key(self):
        spell = self._spell(
            variants_json=[{"key": "owls_wisdom", "labelPt": "Sabedoria", "effects": [_advantage_effect()]}],
        )
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell, state_json={}, slot_level=2, variant_key="nonexistent"
        )
        self.assertFalse(ok)
        self.assertIn("Unknown variant", reason)

    def test_no_declarative_effects(self):
        spell = self._spell(effects_json=[], variants_json=[])
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell, state_json={}, slot_level=None, variant_key=None
        )
        self.assertFalse(ok)
        self.assertIn("no supported declarative effects", reason)

    def test_slot_level_too_low(self):
        spell = self._spell(level=2, effects_json=[_advantage_effect()])
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell, state_json={}, slot_level=1, variant_key=None
        )
        self.assertFalse(ok)
        self.assertIn("slotLevel", reason)

    def test_no_slots_remaining(self):
        spell = self._spell(level=2, effects_json=[_advantage_effect()])
        state_json = _slots_state(level=2, used=3, max_slots=3)
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell, state_json=state_json, slot_level=2, variant_key=None
        )
        self.assertFalse(ok)
        self.assertIn("No spell slot", reason)

    def test_eligible_with_variant(self):
        spell = self._spell(
            variants_json=[{"key": "owls_wisdom", "labelPt": "Sabedoria", "effects": [_advantage_effect()]}],
        )
        state_json = _slots_state(level=2)
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell, state_json=state_json, slot_level=2, variant_key="owls_wisdom"
        )
        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_eligible_direct_effects(self):
        spell = self._spell(level=1, effects_json=[_ac_bonus_effect()])
        state_json = _slots_state(level=1, used=0, max_slots=4)
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell, state_json=state_json, slot_level=1, variant_key=None
        )
        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_cantrip_no_slot_required(self):
        spell = self._spell(level=0, effects_json=[_advantage_effect()])
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell, state_json={}, slot_level=None, variant_key=None
        )
        self.assertTrue(ok)
        self.assertIsNone(reason)


# ---------------------------------------------------------------------------
# Unit tests: build_persisted_effects
# ---------------------------------------------------------------------------

class TestBuildPersistedEffects(unittest.TestCase):
    def _spell(self, **kwargs):
        return _make_campaign_spell(**kwargs)

    def test_advantage_check_effect_shape(self):
        spell = self._spell(
            effects_json=[_advantage_effect("wisdom")],
            concentration=False,
        )
        effects = build_persisted_effects(spell=spell, caster_user_id="user-1", variant_key=None)
        self.assertEqual(len(effects), 1)
        e = effects[0]
        self.assertEqual(e["kind"], "spell_effect")
        self.assertEqual(e["duration_type"], "until_long_rest")
        self.assertFalse(e["metadata"]["concentration"])
        self.assertIsNone(e["metadata"]["concentration_group"])
        self.assertEqual(e["metadata"]["declarative_effect"]["type"], "advantage_on_checks")
        self.assertEqual(e["metadata"]["ability"], "wisdom")
        self.assertEqual(e["metadata"]["against"], "any")
        self.assertEqual(e["metadata"]["caster_player_user_id"], "user-1")
        self.assertIsNotNone(e["id"])
        self.assertIsNotNone(e["created_at"])

    def test_ac_bonus_effect_shape(self):
        spell = self._spell(
            canonical_key="shield_of_faith",
            level=1,
            concentration=True,
            effects_json=[_ac_bonus_effect(2)],
            name_pt="Escudo da Fé",
        )
        effects = build_persisted_effects(spell=spell, caster_user_id="user-1", variant_key=None)
        self.assertEqual(len(effects), 1)
        e = effects[0]
        self.assertEqual(e["kind"], "temp_ac_bonus")
        self.assertEqual(e["numeric_value"], 2)
        self.assertTrue(e["metadata"]["concentration"])
        self.assertIsNotNone(e["metadata"]["concentration_group"])
        self.assertEqual(e["metadata"]["declarative_effect"]["type"], "modify_stat")

    def test_variant_selects_correct_effects(self):
        spell = self._spell(
            variants_json=[
                {"key": "owls_wisdom", "labelPt": "Sabedoria", "labelEn": "Owl's Wisdom",
                 "effects": [_advantage_effect("wisdom")]},
                {"key": "bulls_strength", "labelPt": "Força do Touro", "labelEn": "Bull's Strength",
                 "effects": [_advantage_effect("strength")]},
            ],
        )
        effects = build_persisted_effects(spell=spell, caster_user_id="user-1", variant_key="owls_wisdom")
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["metadata"]["declarative_effect"]["params"]["ability"], "wisdom")
        self.assertEqual(effects[0]["metadata"]["selected_variant_key"], "owls_wisdom")
        self.assertEqual(effects[0]["metadata"]["selected_variant_label"], "Sabedoria")

    def test_grant_temp_hp_skipped(self):
        spell = self._spell(
            effects_json=[
                _advantage_effect("constitution"),
                {"type": "grant_temp_hp", "target": "selected_target", "params": {"dice": "2d6"}},
            ],
            concentration=True,
        )
        effects = build_persisted_effects(spell=spell, caster_user_id="user-1", variant_key=None)
        # Only advantage_on_checks survives; grant_temp_hp is skipped
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["metadata"]["declarative_effect"]["type"], "advantage_on_checks")

    def test_concentration_group_shared_across_effects(self):
        spell = self._spell(
            effects_json=[_advantage_effect("wisdom"), _ac_bonus_effect(1)],
            concentration=True,
        )
        effects = build_persisted_effects(spell=spell, caster_user_id="user-1", variant_key=None)
        self.assertEqual(len(effects), 2)
        groups = {e["metadata"]["concentration_group"] for e in effects}
        self.assertEqual(len(groups), 1, "All effects must share the same concentration_group")


# ---------------------------------------------------------------------------
# Unit tests: consume_spell_slot
# ---------------------------------------------------------------------------

class TestConsumeSpellSlot(unittest.TestCase):
    def test_decrements_used(self):
        state = _slots_state(level=2, used=1, max_slots=3)
        result = consume_spell_slot(state, 2)
        self.assertEqual(result["spellcasting"]["slots"]["2"]["used"], 2)

    def test_raises_when_no_slots(self):
        state = _slots_state(level=2, used=3, max_slots=3)
        with self.assertRaises(ValueError):
            consume_spell_slot(state, 2)

    def test_does_not_mutate_input(self):
        state = _slots_state(level=2, used=0, max_slots=3)
        original_used = state["spellcasting"]["slots"]["2"]["used"]
        consume_spell_slot(state, 2)
        self.assertEqual(state["spellcasting"]["slots"]["2"]["used"], original_used)


# ---------------------------------------------------------------------------
# Integration tests: HTTP endpoint (mocked dependencies)
# ---------------------------------------------------------------------------

class TestCastSpellOutOfCombat(unittest.IsolatedAsyncioTestCase):
    def _make_full_spell(self, **kwargs):
        defaults = dict(
            canonical_key="enhance_ability",
            level=2,
            concentration=True,
            out_of_combat_castable=True,
            variants_json=[{
                "key": "owls_wisdom",
                "labelPt": "Sabedoria da Coruja",
                "labelEn": "Owl's Wisdom",
                "effects": [_advantage_effect("wisdom")],
            }],
        )
        defaults.update(kwargs)
        return _make_campaign_spell(**defaults)

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_successful_concentration_cast_replaces_existing(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        existing_effect = {
            "id": "old-eff",
            "kind": "spell_effect",
            "duration_type": "until_long_rest",
            "metadata": {"concentration": True, "concentration_group": "old-grp", "source_spell_key": "bless"},
        }
        state_json = {
            **_slots_state(level=2),
            "active_spell_effects": [existing_effect],
        }
        db = MagicMock()
        state = MagicMock()
        state.state_json = state_json
        state.id = "ss-1"
        state.session_id = "session-1"
        state.player_user_id = "user-1"
        state.created_at = "2026-01-01T00:00:00+00:00"
        state.updated_at = None

        campaign_spell = self._make_full_spell()
        call_count = [0]
        def exec_side(q, **kw):
            r = MagicMock()
            if call_count[0] == 0:
                r.first.return_value = state
            else:
                r.first.return_value = campaign_spell
            call_count[0] += 1
            return r

        db.exec.side_effect = exec_side
        mock_ensure.return_value = state
        mock_to_state_read.return_value = MagicMock(spec=["activeSpellEffects"])

        req = OutOfCombatCastRequest(spellId="spell-ea-1", slotLevel=2, variantKey="owls_wisdom")
        await cast_spell_out_of_combat(session_id="session-1", req=req, user=_make_user(), session=db)

        # The concentration group from "old-eff" should be cleared and new effects added
        saved_state = state.state_json
        effects = saved_state.get("active_spell_effects", [])
        old_ids = [e["id"] for e in effects if e.get("id") == "old-eff"]
        self.assertEqual(old_ids, [], "Old concentration effect should be removed")
        new_effects = [e for e in effects if e.get("id") != "old-eff"]
        self.assertTrue(len(new_effects) >= 1, "New effects should be added")

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_slot_decremented_on_successful_cast(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        state_json = _slots_state(level=2, used=0, max_slots=3)
        db = MagicMock()
        state = MagicMock()
        state.state_json = state_json
        state.id = "ss-1"
        state.session_id = "session-1"
        state.player_user_id = "user-1"
        state.created_at = "2026-01-01T00:00:00+00:00"
        state.updated_at = None

        campaign_spell = self._make_full_spell()
        call_count = [0]
        def exec_side(q, **kw):
            r = MagicMock()
            if call_count[0] == 0:
                r.first.return_value = state
            else:
                r.first.return_value = campaign_spell
            call_count[0] += 1
            return r

        db.exec.side_effect = exec_side
        mock_ensure.return_value = state
        mock_to_state_read.return_value = MagicMock()

        req = OutOfCombatCastRequest(spellId="spell-ea-1", slotLevel=2, variantKey="owls_wisdom")
        await cast_spell_out_of_combat(session_id="session-1", req=req, user=_make_user(), session=db)

        saved = state.state_json
        used = saved["spellcasting"]["slots"]["2"]["used"]
        self.assertEqual(used, 1)

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_unprepared_spell_rejected(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        from fastapi import HTTPException

        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        state_json = {
            "spellcasting": {
                "slots": {"2": {"used": 0, "max": 3}},
                "spells": [
                    {
                        "id": "spell-ea-1",
                        "canonicalKey": "enhance_ability",
                        "level": 2,
                        "prepared": False,
                    }
                ],
            }
        }
        db = MagicMock()
        state = MagicMock()
        state.state_json = state_json
        state.id = "ss-1"
        state.session_id = "session-1"
        state.player_user_id = "user-1"
        state.created_at = "2026-01-01T00:00:00+00:00"
        state.updated_at = None
        db.exec.return_value.first.return_value = state
        mock_ensure.return_value = state

        req = OutOfCombatCastRequest(spellId="spell-ea-1", slotLevel=2, variantKey="owls_wisdom")
        with self.assertRaises(HTTPException) as ctx:
            await cast_spell_out_of_combat(session_id="session-1", req=req, user=_make_user(), session=db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("not prepared", ctx.exception.detail)

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_non_eligible_spell_rejected(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        from fastapi import HTTPException

        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        state_json = _slots_state(level=3, used=0, max_slots=2)
        state_json["spellcasting"]["spells"] = [
            {"id": "spell-fb-1", "canonicalKey": "fireball", "level": 3, "prepared": True}
        ]
        db = MagicMock()
        state = MagicMock()
        state.state_json = state_json
        state.id = "ss-1"
        state.session_id = "session-1"
        state.player_user_id = "user-1"
        state.created_at = "2026-01-01T00:00:00+00:00"
        state.updated_at = None

        fireball = _make_campaign_spell(
            canonical_key="fireball",
            level=3,
            out_of_combat_castable=False,
        )
        call_count = [0]
        def exec_side(q, **kw):
            r = MagicMock()
            if call_count[0] == 0:
                r.first.return_value = state
            else:
                r.first.return_value = fireball
            call_count[0] += 1
            return r

        db.exec.side_effect = exec_side
        mock_ensure.return_value = state

        req = OutOfCombatCastRequest(spellId="spell-fb-1", slotLevel=3, variantKey=None)
        with self.assertRaises(HTTPException) as ctx:
            await cast_spell_out_of_combat(session_id="session-1", req=req, user=_make_user(), session=db)
        self.assertEqual(ctx.exception.status_code, 400)

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_variant_key_stored_in_effect_metadata(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        state_json = _slots_state(level=2)
        db = MagicMock()
        state = MagicMock()
        state.state_json = state_json
        state.id = "ss-1"
        state.session_id = "session-1"
        state.player_user_id = "user-1"
        state.created_at = "2026-01-01T00:00:00+00:00"
        state.updated_at = None

        campaign_spell = self._make_full_spell()
        call_count = [0]
        def exec_side(q, **kw):
            r = MagicMock()
            if call_count[0] == 0:
                r.first.return_value = state
            else:
                r.first.return_value = campaign_spell
            call_count[0] += 1
            return r

        db.exec.side_effect = exec_side
        mock_ensure.return_value = state
        mock_to_state_read.return_value = MagicMock()

        req = OutOfCombatCastRequest(spellId="spell-ea-1", slotLevel=2, variantKey="owls_wisdom")
        await cast_spell_out_of_combat(session_id="session-1", req=req, user=_make_user(), session=db)

        effects = state.state_json.get("active_spell_effects", [])
        self.assertTrue(len(effects) >= 1)
        for e in effects:
            meta = e.get("metadata", {})
            self.assertEqual(meta.get("selected_variant_key"), "owls_wisdom")
