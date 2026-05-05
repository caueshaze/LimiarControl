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
    _prune_out_of_combat_session_activity,
    cast_spell_out_of_combat,
    list_out_of_combat_castable_spells,
)
from app.api.serializers.base_spell import (
    to_base_spell_read,
    to_base_spell_seed_entry,
)
from app.schemas.session_state import OutOfCombatCastRequest
from app.services.out_of_combat_cast import (
    build_concentration_marker,
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


def _make_base_spell(**overrides):
    defaults = dict(
        id="spell-1",
        system="DND5E",
        canonical_key="test_spell",
        name_en="Test Spell",
        name_pt="Magia de Teste",
        description_en="A test spell.",
        description_pt="Uma magia de teste.",
        level=1,
        school="evocation",
        classes_json=[],
        casting_time_type="action",
        casting_time="1 action",
        range_meters=30,
        range_text="30 ft",
        target_type="ranged",
        max_targets=1,
        area_shape=None,
        duration="Instantaneous",
        components_json=["V", "S"],
        material_component_text=None,
        concentration=False,
        ritual=False,
        resolution_type="damage",
        saving_throw=None,
        save_success_outcome=None,
        cover_applies_to_save=None,
        damage_dice="1d8",
        damage_type="fire",
        heal_dice=None,
        requires_target_sight=False,
        requires_target_effect=False,
        requires_point_sight=False,
        requires_point_effect=False,
        upcast_json=None,
        upcast_mode=None,
        upcast_value=None,
        cantrip_scaling_json=None,
        source="seed",
        source_ref=None,
        is_srd=True,
        is_active=True,
        out_of_combat_castable=True,
        out_of_combat_target="self",
        effects_json=[],
        on_end_effects_json=[],
        variants_json=[],
        persistent_area_json=None,
        selection_type=None,
        origin_type=None,
        target_anchor=None,
        attack_type=None,
        range_kind=None,
        effect_timing=None,
        radius_meters=None,
        length_meters=None,
        side_meters=None,
    )
    defaults.update(overrides)
    spell = MagicMock()
    for k, v in defaults.items():
        setattr(spell, k, v)
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


def _make_multiplayer_cast_setup(
    mock_get_entry: MagicMock,
    mock_ensure: MagicMock,
    campaign_spell: MagicMock,
    *,
    caster_user_id: str = "caster-1",
    target_user_id: str = "target-2",
    third_user_id: str | None = None,
    slot_level: int = 1,
    caster_active_effects: list[dict] | None = None,
    target_active_effects: list[dict] | None = None,
    third_active_effects: list[dict] | None = None,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock | None]:
    """Create a multiplayer cast setup with 2–3 SessionState mocks.

    Builds caster + target (+ optional third player) with MagicMock
    SessionState objects containing state_json with spell slots and
    optional pre-seeded ``active_spell_effects``.  Handles the full
    ``db.exec`` query sequence from ``cast_spell_out_of_combat``
    **without** patching ``clear_concentration_group_across_session``::

        0. .first()  → caster state  (select … where player_user_id == user.id)
        1. .first()  → target state  (select … where player_user_id == target)
        2. .first()  → campaign spell lookup
        3. .all()    → all session states
                       (used by clear_concentration_group_across_session)

    Pre-seed ``active_spell_effects`` on any player to test concentration
    replacement, dedup, or marker placement scenarios.

    Typical usage (caller provides the standard decorator set)::

        @patch("app.api.routes.sessions.state.get_session_entry")
        @patch("app.api.routes.sessions.state.require_session_view_access")
        @patch("app.api.routes.sessions.state.ensure_session_state")
        @patch("app.api.routes.sessions.state.finalize_session_state_data",
               side_effect=lambda d: d)
        @patch("app.api.routes.sessions.state.publish_state_update")
        @patch("app.api.routes.sessions.state.to_state_read")
        async def test_…(
            self, mock_to_state, mock_pub, mock_fin,
            mock_ensure, mock_req, mock_entry,
        ):
            mock_to_state.return_value = MagicMock()
            db, caster, target, third = _make_multiplayer_cast_setup(
                mock_entry, mock_ensure, spell,
                caster_active_effects=[…],
            )
            …

    .. note::
       When a test exercises real concentration-group clearing (i.e. an
       ``old_group`` exists and ``clear_concentration_group_across_session``
       runs), the caller should also patch
       ``app.services.combat_service.persistent_effects.finalize_session_state_data``
       with ``side_effect=lambda d: d``.

    Returns (db, caster_state, target_state, third_state) where
    ``third_state`` is ``None`` when ``third_user_id`` is not given.
    """
    # --- Session entry mock ---
    entry = MagicMock(party_id="party-1", campaign_id="camp-1")
    mock_get_entry.return_value = entry

    # --- Caster state ---
    caster_json = _slots_state(level=slot_level, used=0, max_slots=3)
    caster_json["spellcasting"]["spells"] = [
        {
            "id": "spell-1",
            "canonicalKey": campaign_spell.canonical_key,
            "level": slot_level,
            "prepared": True,
        }
    ]
    if caster_active_effects:
        caster_json["active_spell_effects"] = list(caster_active_effects)

    caster_state = MagicMock()
    caster_state.state_json = caster_json
    caster_state.id = "ss-caster"
    caster_state.session_id = "session-1"
    caster_state.player_user_id = caster_user_id
    caster_state.created_at = "2026-01-01T00:00:00+00:00"
    caster_state.updated_at = None

    # --- Target state ---
    target_json: dict = {}
    if target_active_effects:
        target_json["active_spell_effects"] = list(target_active_effects)

    target_state = MagicMock()
    target_state.state_json = target_json
    target_state.id = "ss-target"
    target_state.session_id = "session-1"
    target_state.player_user_id = target_user_id
    target_state.created_at = "2026-01-01T00:00:00+00:00"
    target_state.updated_at = None

    # --- Optional third-player state ---
    third_state: MagicMock | None = None
    if third_user_id is not None:
        third_json: dict = {}
        if third_active_effects:
            third_json["active_spell_effects"] = list(third_active_effects)
        third_state = MagicMock()
        third_state.state_json = third_json
        third_state.id = "ss-third"
        third_state.session_id = "session-1"
        third_state.player_user_id = third_user_id
        third_state.created_at = "2026-01-01T00:00:00+00:00"
        third_state.updated_at = None

    # --- Wire mock_ensure ---
    mock_ensure.return_value = caster_state

    # --- All states (for clear_concentration_group_across_session .all()) ---
    all_states = [caster_state, target_state]
    if third_state is not None:
        all_states.append(third_state)

    # --- Wire db.exec with sequential query returns ---
    db = MagicMock()
    call_count = [0]
    first_results = [caster_state, target_state, campaign_spell]

    def exec_side(q, **kw):
        r = MagicMock()
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(first_results):
            r.first.return_value = first_results[idx]
        elif idx == len(first_results):
            # clear_concentration_group_across_session uses .all()
            r.all.return_value = list(all_states)
        else:
            r.first.return_value = None
            r.all.return_value = []
        return r

    db.exec.side_effect = exec_side
    return db, caster_state, target_state, third_state


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
        effects = build_persisted_effects(spell=spell, caster_user_id="user-1", target_user_id="user-1", variant_key=None)
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
        effects = build_persisted_effects(spell=spell, caster_user_id="user-1", target_user_id="user-1", variant_key=None)
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
        effects = build_persisted_effects(spell=spell, caster_user_id="user-1", target_user_id="user-1", variant_key="owls_wisdom")
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
        effects = build_persisted_effects(spell=spell, caster_user_id="user-1", target_user_id="user-1", variant_key=None)
        # Only advantage_on_checks survives; grant_temp_hp is skipped
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["metadata"]["declarative_effect"]["type"], "advantage_on_checks")

    def test_concentration_group_shared_across_effects(self):
        spell = self._spell(
            effects_json=[_advantage_effect("wisdom"), _ac_bonus_effect(1)],
            concentration=True,
        )
        effects = build_persisted_effects(spell=spell, caster_user_id="user-1", target_user_id="user-1", variant_key=None)
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

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_prepared_leveled_spell_accepted(
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

        state_json = _slots_state(level=1, used=0, max_slots=4)
        state_json["spellcasting"]["spells"] = [
            {"id": "spell-sof-1", "canonicalKey": "shield_of_faith", "level": 1, "prepared": True}
        ]
        db = MagicMock()
        state = MagicMock()
        state.state_json = state_json
        state.id = "ss-1"
        state.session_id = "session-1"
        state.player_user_id = "user-1"
        state.created_at = "2026-01-01T00:00:00+00:00"
        state.updated_at = None

        shield = _make_campaign_spell(
            canonical_key="shield_of_faith",
            level=1,
            concentration=True,
            out_of_combat_castable=True,
            effects_json=[_ac_bonus_effect(2)],
        )
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            r.first.return_value = state if call_count[0] == 0 else shield
            call_count[0] += 1
            return r

        db.exec.side_effect = exec_side
        mock_ensure.return_value = state
        mock_to_state_read.return_value = MagicMock()

        req = OutOfCombatCastRequest(spellId="spell-sof-1", slotLevel=1, variantKey=None)
        result = await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=_make_user(), session=db
        )
        self.assertIsNotNone(result)

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_non_concentration_effects_survive_concentration_replacement(
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

        non_conc_effect = {
            "id": "non-conc-eff",
            "kind": "spell_effect",
            "duration_type": "until_long_rest",
            "metadata": {
                "concentration": False,
                "concentration_group": None,
                "source_spell_key": "guidance",
            },
        }
        old_conc_effect = {
            "id": "old-conc-eff",
            "kind": "spell_effect",
            "duration_type": "until_long_rest",
            "metadata": {
                "concentration": True,
                "concentration_group": "old-grp",
                "source_spell_key": "bless",
            },
        }
        state_json = {
            **_slots_state(level=1),
            "active_spell_effects": [non_conc_effect, old_conc_effect],
        }
        state_json["spellcasting"]["spells"] = [
            {"id": "spell-sof-1", "canonicalKey": "shield_of_faith", "level": 1, "prepared": True}
        ]
        db = MagicMock()
        state = MagicMock()
        state.state_json = state_json
        state.id = "ss-1"
        state.session_id = "session-1"
        state.player_user_id = "user-1"
        state.created_at = "2026-01-01T00:00:00+00:00"
        state.updated_at = None

        shield = _make_campaign_spell(
            canonical_key="shield_of_faith",
            level=1,
            concentration=True,
            out_of_combat_castable=True,
            effects_json=[_ac_bonus_effect(2)],
        )
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            r.first.return_value = state if call_count[0] == 0 else shield
            call_count[0] += 1
            return r

        db.exec.side_effect = exec_side
        mock_ensure.return_value = state
        mock_to_state_read.return_value = MagicMock()

        req = OutOfCombatCastRequest(spellId="spell-sof-1", slotLevel=1, variantKey=None)
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=_make_user(), session=db
        )

        remaining = state.state_json.get("active_spell_effects", [])
        ids = [e["id"] for e in remaining]
        self.assertIn("non-conc-eff", ids, "Non-concentration effect must survive concentration replacement")
        self.assertNotIn("old-conc-eff", ids, "Old concentration effect must be cleared")


# ---------------------------------------------------------------------------
# Tests: list_out_of_combat_castable_spells endpoint
# ---------------------------------------------------------------------------

class TestListCastableEndpoint(unittest.TestCase):
    def _make_state_with_spells(self, spells: list) -> MagicMock:
        state = MagicMock()
        state.state_json = {
            "spellcasting": {
                "slots": {},
                "spells": spells,
            }
        }
        return state

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    def test_returns_only_out_of_combat_castable_spells(
        self, mock_ensure, mock_require, mock_get_entry
    ):
        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        state = self._make_state_with_spells([
            {"id": "spell-ea-1", "canonicalKey": "enhance_ability", "level": 2, "prepared": True},
            {"id": "spell-fb-1", "canonicalKey": "fireball", "level": 3, "prepared": True},
        ])
        mock_ensure.return_value = state

        # DB returns only the castable spell (fireball filtered out at DB level)
        enhance_cs = _make_campaign_spell(
            canonical_key="enhance_ability",
            level=2,
            out_of_combat_castable=True,
            variants_json=[{"key": "owls_wisdom", "labelPt": "Sabedoria", "effects": [_advantage_effect()]}],
        )
        db = MagicMock()
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            if call_count[0] == 0:
                r.first.return_value = state
            else:
                r.all.return_value = [enhance_cs]
            call_count[0] += 1
            return r

        db.exec.side_effect = exec_side

        result = list_out_of_combat_castable_spells(
            session_id="session-1", user=_make_user(), session=db
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["canonicalKey"], "enhance_ability")

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    def test_excludes_spells_with_no_effects_or_variants(
        self, mock_ensure, mock_require, mock_get_entry
    ):
        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        state = self._make_state_with_spells([
            {"id": "spell-empty-1", "canonicalKey": "empty_spell", "level": 1, "prepared": True},
        ])
        mock_ensure.return_value = state

        empty_cs = _make_campaign_spell(
            canonical_key="empty_spell",
            level=1,
            out_of_combat_castable=True,
            effects_json=[],
            variants_json=[],
        )
        db = MagicMock()
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            if call_count[0] == 0:
                r.first.return_value = state
            else:
                r.all.return_value = [empty_cs]
            call_count[0] += 1
            return r

        db.exec.side_effect = exec_side

        result = list_out_of_combat_castable_spells(
            session_id="session-1", user=_make_user(), session=db
        )

        self.assertEqual(result, [], "Spells with no effects should be excluded from the eligible list")

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    def test_includes_variant_only_spells(
        self, mock_ensure, mock_require, mock_get_entry
    ):
        """Enhance Ability has no top-level effects but variant effects; it should appear."""
        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        state = self._make_state_with_spells([
            {"id": "spell-ea-1", "canonicalKey": "enhance_ability", "level": 2, "prepared": True},
        ])
        mock_ensure.return_value = state

        enhance_cs = _make_campaign_spell(
            canonical_key="enhance_ability",
            level=2,
            out_of_combat_castable=True,
            effects_json=[],
            variants_json=[{"key": "owls_wisdom", "labelPt": "Sabedoria", "effects": [_advantage_effect()]}],
        )
        db = MagicMock()
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            if call_count[0] == 0:
                r.first.return_value = state
            else:
                r.all.return_value = [enhance_cs]
            call_count[0] += 1
            return r

        db.exec.side_effect = exec_side

        result = list_out_of_combat_castable_spells(
            session_id="session-1", user=_make_user(), session=db
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["canonicalKey"], "enhance_ability")

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    def test_returns_out_of_combat_target_field(
        self, mock_ensure, mock_require, mock_get_entry
    ):
        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        state = self._make_state_with_spells([
            {"id": "spell-sof-1", "canonicalKey": "shield_of_faith", "level": 1, "prepared": True},
        ])
        mock_ensure.return_value = state

        shield_cs = _make_campaign_spell(
            canonical_key="shield_of_faith",
            level=1,
            out_of_combat_castable=True,
            effects_json=[_ac_bonus_effect(2)],
        )
        shield_cs.out_of_combat_target = "ally"
        db = MagicMock()
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            if call_count[0] == 0:
                r.first.return_value = state
            else:
                r.all.return_value = [shield_cs]
            call_count[0] += 1
            return r

        db.exec.side_effect = exec_side

        result = list_out_of_combat_castable_spells(
            session_id="session-1", user=_make_user(), session=db
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["outOfCombatTarget"], "ally")


# ---------------------------------------------------------------------------
# Tests: cast mutation safety (failed cast must not mutate state)
# ---------------------------------------------------------------------------

class TestCastMutationSafety(unittest.IsolatedAsyncioTestCase):
    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    async def test_failed_cast_does_not_spend_slots(
        self, mock_ensure, mock_require_view, mock_get_entry
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
            canonical_key="fireball", level=3, out_of_combat_castable=False
        )
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            r.first.return_value = state if call_count[0] == 0 else fireball
            call_count[0] += 1
            return r

        db.exec.side_effect = exec_side
        mock_ensure.return_value = state

        req = OutOfCombatCastRequest(spellId="spell-fb-1", slotLevel=3, variantKey=None)
        with self.assertRaises(HTTPException):
            await cast_spell_out_of_combat(
                session_id="session-1", req=req, user=_make_user(), session=db
            )

        used = state.state_json["spellcasting"]["slots"]["3"]["used"]
        self.assertEqual(used, 0, "Slots must not be decremented after a failed cast")

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    async def test_failed_cast_does_not_create_active_effects(
        self, mock_ensure, mock_require_view, mock_get_entry
    ):
        from fastapi import HTTPException

        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        state_json = _slots_state(level=3, used=0, max_slots=2)
        state_json["spellcasting"]["spells"] = [
            {"id": "spell-fb-1", "canonicalKey": "fireball", "level": 3, "prepared": True}
        ]
        state_json["active_spell_effects"] = []
        db = MagicMock()
        state = MagicMock()
        state.state_json = state_json
        state.id = "ss-1"
        state.session_id = "session-1"
        state.player_user_id = "user-1"
        state.created_at = "2026-01-01T00:00:00+00:00"
        state.updated_at = None

        fireball = _make_campaign_spell(
            canonical_key="fireball", level=3, out_of_combat_castable=False
        )
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            r.first.return_value = state if call_count[0] == 0 else fireball
            call_count[0] += 1
            return r

        db.exec.side_effect = exec_side
        mock_ensure.return_value = state

        req = OutOfCombatCastRequest(spellId="spell-fb-1", slotLevel=3, variantKey=None)
        with self.assertRaises(HTTPException):
            await cast_spell_out_of_combat(
                session_id="session-1", req=req, user=_make_user(), session=db
            )

        effects = state.state_json.get("active_spell_effects", [])
        self.assertEqual(effects, [], "Active effects must not be modified after a failed cast")


# ---------------------------------------------------------------------------
# Tests: ally-target mutation safety
# ---------------------------------------------------------------------------

class TestAllyMutationSafety(unittest.IsolatedAsyncioTestCase):
    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    async def test_invalid_ally_target_does_not_mutate_state(
        self, mock_ensure, mock_require_view, mock_get_entry
    ):
        from fastapi import HTTPException

        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        state_json = _slots_state(level=1, used=0, max_slots=3)
        state_json["spellcasting"]["spells"] = [
            {"id": "spell-1", "canonicalKey": "shield_of_faith", "level": 1, "prepared": True}
        ]
        state_json["active_spell_effects"] = []
        db = MagicMock()
        state = MagicMock()
        state.state_json = state_json
        state.id = "ss-caster"
        state.session_id = "session-1"
        state.player_user_id = "caster-1"
        state.created_at = "2026-01-01T00:00:00+00:00"
        state.updated_at = None

        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            r.first.return_value = state if call_count[0] == 0 else None
            call_count[0] += 1
            return r

        db.exec.side_effect = exec_side
        mock_ensure.return_value = state

        req = OutOfCombatCastRequest(
            spellId="spell-1", slotLevel=1, variantKey=None, targetPlayerUserId="ghost-user"
        )

        slots_before = state.state_json["spellcasting"]["slots"]["1"]["used"]
        effects_before = len(state.state_json.get("active_spell_effects", []))

        with self.assertRaises(HTTPException) as ctx:
            await cast_spell_out_of_combat(
                session_id="session-1", req=req, user=_make_user("caster-1"), session=db
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("participant", ctx.exception.detail)

        self.assertEqual(
            state.state_json["spellcasting"]["slots"]["1"]["used"],
            slots_before,
            "Caster slots must not change after invalid target rejection",
        )
        self.assertEqual(
            len(state.state_json.get("active_spell_effects", [])),
            effects_before,
            "Caster effects must not change after invalid target rejection",
        )

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    async def test_self_only_spell_targeting_ally_does_not_mutate_state(
        self, mock_ensure, mock_require_view, mock_get_entry
    ):
        from fastapi import HTTPException

        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        caster_json = _slots_state(level=1, used=0, max_slots=3)
        caster_json["spellcasting"]["spells"] = [
            {"id": "spell-1", "canonicalKey": "shield_of_faith", "level": 1, "prepared": True}
        ]
        caster_json["active_spell_effects"] = []
        caster_state = MagicMock()
        caster_state.state_json = caster_json
        caster_state.id = "ss-caster"
        caster_state.session_id = "session-1"
        caster_state.player_user_id = "caster-1"
        caster_state.created_at = "2026-01-01T00:00:00+00:00"
        caster_state.updated_at = None

        target_state = MagicMock()
        target_state.state_json = {}
        target_state.id = "ss-target"
        target_state.session_id = "session-1"
        target_state.player_user_id = "target-2"
        target_state.created_at = "2026-01-01T00:00:00+00:00"
        target_state.updated_at = None

        shield = _make_campaign_spell(
            canonical_key="shield_of_faith",
            level=1,
            concentration=True,
            out_of_combat_castable=True,
            effects_json=[_ac_bonus_effect(2)],
        )
        shield.out_of_combat_target = "self"

        db = MagicMock()
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            idx = call_count[0]
            call_count[0] += 1
            if idx == 0:
                r.first.return_value = caster_state
            elif idx == 1:
                r.first.return_value = target_state
            elif idx == 2:
                r.first.return_value = shield
            else:
                r.first.return_value = None
                r.all.return_value = []
            return r

        db.exec.side_effect = exec_side
        mock_ensure.return_value = caster_state

        req = OutOfCombatCastRequest(
            spellId="spell-1", slotLevel=1, variantKey=None, targetPlayerUserId="target-2"
        )

        slots_before = caster_state.state_json["spellcasting"]["slots"]["1"]["used"]
        effects_before = len(caster_state.state_json.get("active_spell_effects", []))
        target_effects_before = len(target_state.state_json.get("active_spell_effects", []))

        with self.assertRaises(HTTPException) as ctx:
            await cast_spell_out_of_combat(
                session_id="session-1", req=req, user=_make_user("caster-1"), session=db
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("allies", ctx.exception.detail)

        self.assertEqual(
            caster_state.state_json["spellcasting"]["slots"]["1"]["used"],
            slots_before,
            "Caster slots must not change after self-only targeting ally rejection",
        )
        self.assertEqual(
            len(caster_state.state_json.get("active_spell_effects", [])),
            effects_before,
            "Caster effects must not change after self-only targeting ally rejection",
        )
        self.assertEqual(
            len(target_state.state_json.get("active_spell_effects", [])),
            target_effects_before,
            "Target effects must not change after self-only targeting ally rejection",
        )

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    async def test_no_slot_ally_cast_does_not_mutate_state(
        self, mock_ensure, mock_require_view, mock_get_entry
    ):
        from fastapi import HTTPException

        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        caster_json = _slots_state(level=1, used=3, max_slots=3)
        caster_json["spellcasting"]["spells"] = [
            {"id": "spell-1", "canonicalKey": "shield_of_faith", "level": 1, "prepared": True}
        ]
        caster_json["active_spell_effects"] = []
        caster_state = MagicMock()
        caster_state.state_json = caster_json
        caster_state.id = "ss-caster"
        caster_state.session_id = "session-1"
        caster_state.player_user_id = "caster-1"
        caster_state.created_at = "2026-01-01T00:00:00+00:00"
        caster_state.updated_at = None

        target_state = MagicMock()
        target_state.state_json = {}
        target_state.id = "ss-target"
        target_state.session_id = "session-1"
        target_state.player_user_id = "target-2"
        target_state.created_at = "2026-01-01T00:00:00+00:00"
        target_state.updated_at = None

        shield = _make_campaign_spell(
            canonical_key="shield_of_faith",
            level=1,
            concentration=True,
            out_of_combat_castable=True,
            effects_json=[_ac_bonus_effect(2)],
        )
        shield.out_of_combat_target = "self_or_ally"

        db = MagicMock()
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            idx = call_count[0]
            call_count[0] += 1
            if idx == 0:
                r.first.return_value = caster_state
            elif idx == 1:
                r.first.return_value = target_state
            elif idx == 2:
                r.first.return_value = shield
            else:
                r.first.return_value = None
                r.all.return_value = []
            return r

        db.exec.side_effect = exec_side
        mock_ensure.return_value = caster_state

        req = OutOfCombatCastRequest(
            spellId="spell-1", slotLevel=1, variantKey=None, targetPlayerUserId="target-2"
        )

        slots_before = caster_state.state_json["spellcasting"]["slots"]["1"]["used"]
        effects_before = len(caster_state.state_json.get("active_spell_effects", []))
        target_effects_before = len(target_state.state_json.get("active_spell_effects", []))

        with self.assertRaises(HTTPException) as ctx:
            await cast_spell_out_of_combat(
                session_id="session-1", req=req, user=_make_user("caster-1"), session=db
            )
        self.assertEqual(ctx.exception.status_code, 400)

        self.assertEqual(
            caster_state.state_json["spellcasting"]["slots"]["1"]["used"],
            slots_before,
            "Caster slots must not change after no-slot rejection",
        )
        self.assertEqual(
            len(caster_state.state_json.get("active_spell_effects", [])),
            effects_before,
            "Caster effects must not change after no-slot rejection",
        )
        self.assertEqual(
            len(target_state.state_json.get("active_spell_effects", [])),
            target_effects_before,
            "Target effects must not change after no-slot rejection",
        )


# ---------------------------------------------------------------------------
# Tests: Enhance Ability variant regression
# ---------------------------------------------------------------------------

class TestEnhanceAbilityVariants(unittest.TestCase):
    _VARIANTS = [
        ("bears_endurance", "Resistência do Urso", "Bear's Endurance", "constitution"),
        ("bulls_strength", "Força do Touro", "Bull's Strength", "strength"),
        ("cats_grace", "Graça do Gato", "Cat's Grace", "dexterity"),
        ("eagles_splendor", "Esplendor da Águia", "Eagle's Splendor", "charisma"),
        ("foxs_cunning", "Astúcia da Raposa", "Fox's Cunning", "intelligence"),
        ("owls_wisdom", "Sabedoria da Coruja", "Owl's Wisdom", "wisdom"),
    ]

    def _make_enhance_ability_spell(self):
        return _make_campaign_spell(
            canonical_key="enhance_ability",
            level=2,
            concentration=True,
            out_of_combat_castable=True,
            effects_json=[],
            variants_json=[
                {
                    "key": key,
                    "labelPt": label_pt,
                    "labelEn": label_en,
                    "effects": [_advantage_effect(ability)],
                }
                for key, label_pt, label_en, ability in self._VARIANTS
            ],
        )

    def test_spell_exposes_all_six_variants(self):
        spell = self._make_enhance_ability_spell()
        self.assertEqual(len(spell.variants_json), 6)
        keys = {v["key"] for v in spell.variants_json}
        for key, _, _, _ in self._VARIANTS:
            self.assertIn(key, keys)

    def test_each_variant_stores_correct_metadata(self):
        spell = self._make_enhance_ability_spell()
        for key, label_pt, _, ability in self._VARIANTS:
            with self.subTest(variant=key):
                effects = build_persisted_effects(
                    spell=spell, caster_user_id="user-1", target_user_id="user-1", variant_key=key
                )
                self.assertEqual(len(effects), 1)
                meta = effects[0]["metadata"]
                self.assertEqual(meta["selected_variant_key"], key)
                self.assertEqual(meta["selected_variant_label"], label_pt)
                self.assertEqual(
                    meta["declarative_effect"]["params"]["ability"],
                    ability,
                    f"Wrong ability for variant {key!r}",
                )

    def test_cats_grace_grants_dexterity_advantage(self):
        spell = self._make_enhance_ability_spell()
        effects = build_persisted_effects(
            spell=spell, caster_user_id="user-1", target_user_id="user-1", variant_key="cats_grace"
        )
        meta = effects[0]["metadata"]
        self.assertEqual(meta["declarative_effect"]["type"], "advantage_on_checks")
        self.assertEqual(meta["declarative_effect"]["params"]["ability"], "dexterity")

    def test_owls_wisdom_grants_wisdom_advantage(self):
        spell = self._make_enhance_ability_spell()
        effects = build_persisted_effects(
            spell=spell, caster_user_id="user-1", target_user_id="user-1", variant_key="owls_wisdom"
        )
        meta = effects[0]["metadata"]
        self.assertEqual(meta["declarative_effect"]["type"], "advantage_on_checks")
        self.assertEqual(meta["declarative_effect"]["params"]["ability"], "wisdom")

    def test_each_variant_effect_is_concentration(self):
        spell = self._make_enhance_ability_spell()
        for key, _, _, _ in self._VARIANTS:
            with self.subTest(variant=key):
                effects = build_persisted_effects(
                    spell=spell, caster_user_id="user-1", target_user_id="user-1", variant_key=key
                )
                meta = effects[0]["metadata"]
                self.assertTrue(meta["concentration"])
                self.assertIsNotNone(meta["concentration_group"])


# ---------------------------------------------------------------------------
# Tests: Shield of Faith regression
# ---------------------------------------------------------------------------

class TestShieldOfFaithRegression(unittest.IsolatedAsyncioTestCase):
    def _make_shield_spell(self):
        return _make_campaign_spell(
            canonical_key="shield_of_faith",
            level=1,
            concentration=True,
            out_of_combat_castable=True,
            effects_json=[_ac_bonus_effect(2)],
            name_pt="Escudo da Fé",
            name_en="Shield of Faith",
        )

    def _setup_cast(self, mock_get_entry, mock_ensure):
        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        state_json = _slots_state(level=1, used=0, max_slots=4)
        state_json["spellcasting"]["spells"] = [
            {"id": "spell-sof-1", "canonicalKey": "shield_of_faith", "level": 1, "prepared": True}
        ]
        db = MagicMock()
        state = MagicMock()
        state.state_json = state_json
        state.id = "ss-1"
        state.session_id = "session-1"
        state.player_user_id = "user-1"
        state.created_at = "2026-01-01T00:00:00+00:00"
        state.updated_at = None

        shield = self._make_shield_spell()
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            r.first.return_value = state if call_count[0] == 0 else shield
            call_count[0] += 1
            return r

        db.exec.side_effect = exec_side
        mock_ensure.return_value = state
        return db, state

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_cast_creates_temp_ac_bonus_effect(
        self, mock_to_state, mock_pub, mock_fin, mock_ensure, mock_req, mock_entry
    ):
        mock_to_state.return_value = MagicMock()
        db, state = self._setup_cast(mock_entry, mock_ensure)

        req = OutOfCombatCastRequest(spellId="spell-sof-1", slotLevel=1, variantKey=None)
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=_make_user(), session=db
        )

        effects = state.state_json.get("active_spell_effects", [])
        ac_effects = [e for e in effects if e.get("kind") == "temp_ac_bonus"]
        self.assertEqual(len(ac_effects), 1)
        self.assertEqual(ac_effects[0]["numeric_value"], 2)

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_slot_is_spent_after_cast(
        self, mock_to_state, mock_pub, mock_fin, mock_ensure, mock_req, mock_entry
    ):
        mock_to_state.return_value = MagicMock()
        db, state = self._setup_cast(mock_entry, mock_ensure)

        req = OutOfCombatCastRequest(spellId="spell-sof-1", slotLevel=1, variantKey=None)
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=_make_user(), session=db
        )

        used = state.state_json["spellcasting"]["slots"]["1"]["used"]
        self.assertEqual(used, 1)

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_concentration_metadata_present(
        self, mock_to_state, mock_pub, mock_fin, mock_ensure, mock_req, mock_entry
    ):
        mock_to_state.return_value = MagicMock()
        db, state = self._setup_cast(mock_entry, mock_ensure)

        req = OutOfCombatCastRequest(spellId="spell-sof-1", slotLevel=1, variantKey=None)
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=_make_user(), session=db
        )

        effects = state.state_json.get("active_spell_effects", [])
        self.assertTrue(len(effects) >= 1)
        for e in effects:
            meta = e.get("metadata", {})
            self.assertTrue(meta.get("concentration"))
            self.assertIsNotNone(meta.get("concentration_group"))


class TestSelfTargetConcentrationRegression(unittest.IsolatedAsyncioTestCase):

    def _make_shield_spell(self):
        return _make_campaign_spell(
            canonical_key="shield_of_faith",
            level=1,
            concentration=True,
            out_of_combat_castable=True,
            effects_json=[_ac_bonus_effect(2)],
            name_pt="Escudo da Fé",
            name_en="Shield of Faith",
        )

    def _setup_cast(self, mock_get_entry, mock_ensure):
        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        state_json = _slots_state(level=1, used=0, max_slots=3)
        state_json["spellcasting"]["spells"] = [
            {"id": "spell-sof-1", "canonicalKey": "shield_of_faith", "level": 1, "prepared": True}
        ]
        state = MagicMock()
        state.state_json = state_json
        state.id = "ss-1"
        state.session_id = "session-1"
        state.player_user_id = "user-1"
        state.created_at = "2026-01-01T00:00:00+00:00"
        state.updated_at = None

        shield = self._make_shield_spell()
        shield.out_of_combat_target = "self"
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            r.first.return_value = state if call_count[0] == 0 else shield
            call_count[0] += 1
            return r

        db = MagicMock()
        db.exec.side_effect = exec_side
        mock_ensure.return_value = state
        return db, state

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_self_target_concentration_does_not_create_marker(
        self, mock_to_state, mock_pub, mock_fin, mock_ensure, mock_req, mock_entry
    ):
        mock_to_state.return_value = MagicMock()
        db, state = self._setup_cast(mock_entry, mock_ensure)

        req = OutOfCombatCastRequest(spellId="spell-sof-1", slotLevel=1, variantKey=None)
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=_make_user(), session=db
        )

        effects = state.state_json.get("active_spell_effects", [])
        self.assertTrue(len(effects) >= 1)

        markers = [e for e in effects if e.get("metadata", {}).get("concentration_marker")]
        self.assertEqual(len(markers), 0, "Self-target must not create a separate concentration marker")

        ac_effs = [e for e in effects if e.get("kind") == "temp_ac_bonus"]
        self.assertEqual(len(ac_effs), 1, "Buff effect must land directly on caster state")

        ac_meta = ac_effs[0].get("metadata", {})
        self.assertTrue(ac_meta.get("concentration"), "Buff effect must have concentration=True")
        self.assertIsNotNone(ac_meta.get("concentration_group"), "Buff effect must have concentration_group")
        self.assertIsNone(ac_meta.get("concentration_marker"), "Buff effect must not have concentration_marker flag")


# ---------------------------------------------------------------------------
# Tests: build_concentration_marker
# ---------------------------------------------------------------------------

class TestBuildConcentrationMarker(unittest.TestCase):
    def _spell(self, **kwargs):
        return _make_campaign_spell(**kwargs)

    def test_marker_has_concentration_true(self):
        spell = self._spell(
            canonical_key="enhance_ability",
            level=2,
            concentration=True,
            variants_json=[{"key": "owls_wisdom", "labelPt": "Sabedoria", "effects": [_advantage_effect()]}],
        )
        marker = build_concentration_marker(
            spell=spell,
            caster_user_id="caster-1",
            target_user_id="target-2",
            concentration_group="grp-123",
            variant_key="owls_wisdom",
        )
        meta = marker["metadata"]
        self.assertTrue(meta["concentration"])
        self.assertTrue(meta["concentration_marker"])
        self.assertEqual(meta["concentration_group"], "grp-123")

    def test_marker_has_no_declarative_effect(self):
        spell = self._spell(
            canonical_key="shield_of_faith",
            level=1,
            concentration=True,
            effects_json=[_ac_bonus_effect(2)],
        )
        marker = build_concentration_marker(
            spell=spell,
            caster_user_id="caster-1",
            target_user_id="target-2",
            concentration_group="grp-456",
            variant_key=None,
        )
        self.assertNotIn("declarative_effect", marker["metadata"])

    def test_marker_caster_and_target_ids(self):
        spell = self._spell(
            canonical_key="enhance_ability",
            level=2,
            concentration=True,
            variants_json=[{"key": "owls_wisdom", "labelPt": "Sabedoria", "effects": [_advantage_effect()]}],
        )
        marker = build_concentration_marker(
            spell=spell,
            caster_user_id="caster-1",
            target_user_id="target-2",
            concentration_group="grp-789",
            variant_key=None,
        )
        meta = marker["metadata"]
        self.assertEqual(meta["caster_player_user_id"], "caster-1")
        self.assertEqual(meta["target_player_user_id"], "target-2")

    def test_marker_kind_is_spell_effect(self):
        spell = self._spell(
            canonical_key="enhance_ability",
            level=2,
            concentration=True,
            effects_json=[_advantage_effect()],
        )
        marker = build_concentration_marker(
            spell=spell,
            caster_user_id="caster-1",
            target_user_id="target-2",
            concentration_group="grp-000",
            variant_key=None,
        )
        self.assertEqual(marker["kind"], "spell_effect")
        self.assertEqual(marker["duration_type"], "until_long_rest")


# ---------------------------------------------------------------------------
# Tests: serializer gaps for outOfCombatTarget
# ---------------------------------------------------------------------------

class TestSerializerGaps(unittest.TestCase):
    def test_to_base_spell_read_includes_out_of_combat_target(self):
        spell = _make_base_spell(out_of_combat_target="ally")
        read = to_base_spell_read(spell)
        self.assertEqual(read.outOfCombatTarget, "ally")

    def test_to_base_spell_seed_entry_includes_out_of_combat_target(self):
        spell = _make_base_spell(out_of_combat_target="self_or_ally")
        entry = to_base_spell_seed_entry(spell)
        self.assertEqual(entry.outOfCombatTarget, "self_or_ally")


# ---------------------------------------------------------------------------
# Tests: ally targeting (endpoint integration)
# ---------------------------------------------------------------------------

class TestAllyConcentrationReplacement(unittest.IsolatedAsyncioTestCase):
    """Golden test: real concentration-group clearing across session states."""

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    @patch("app.services.combat_service.persistent_effects.finalize_session_state_data", side_effect=lambda d: d)
    async def test_ally_concentration_replacement_cleans_old_target_effect(
        self,
        mock_pe_finalize,
        mock_to_state,
        mock_pub,
        mock_fin,
        mock_ensure,
        mock_req,
        mock_entry,
    ):
        mock_to_state.return_value = MagicMock()

        shield = _make_campaign_spell(
            canonical_key="shield_of_faith",
            level=1,
            concentration=True,
            out_of_combat_castable=True,
            effects_json=[_ac_bonus_effect(2)],
            name_pt="Escudo da Fé",
            name_en="Shield of Faith",
        )
        shield.out_of_combat_target = "self_or_ally"

        # --- Pre-seed effects ---
        old_concentration_marker = {
            "id": "old-marker",
            "kind": "spell_effect",
            "duration_type": "until_long_rest",
            "metadata": {
                "concentration": True,
                "concentration_marker": True,
                "concentration_group": "old-grp",
                "source_spell_key": "bless",
                "caster_player_user_id": "caster-1",
                "target_player_user_id": "ally-a",
            },
        }

        old_buff_on_ally_a = {
            "id": "old-buff",
            "kind": "temp_ac_bonus",
            "duration_type": "until_long_rest",
            "numeric_value": 1,
            "metadata": {
                "concentration": True,
                "concentration_group": "old-grp",
                "source_spell_key": "bless",
                "caster_player_user_id": "caster-1",
                "target_player_user_id": "ally-a",
                "declarative_effect": {
                    "type": "modify_stat",
                    "target": "selected_target",
                    "params": {"stat": "temp_ac_bonus", "value": 1},
                    "stacking": "replace",
                },
            },
        }

        unrelated_effect_on_ally_a = {
            "id": "unrelated-ally-a",
            "kind": "spell_effect",
            "duration_type": "until_long_rest",
            "metadata": {
                "concentration": False,
                "concentration_group": None,
                "source_spell_key": "guidance",
            },
        }

        unrelated_effect_on_ally_b = {
            "id": "unrelated-ally-b",
            "kind": "spell_effect",
            "duration_type": "until_long_rest",
            "metadata": {
                "concentration": False,
                "concentration_group": None,
                "source_spell_key": "resistance",
            },
        }

        db, caster_state, target_state, third_state = _make_multiplayer_cast_setup(
            mock_entry,
            mock_ensure,
            shield,
            caster_user_id="caster-1",
            target_user_id="ally-b",
            third_user_id="ally-a",
            slot_level=1,
            caster_active_effects=[old_concentration_marker],
            target_active_effects=[unrelated_effect_on_ally_b],
            third_active_effects=[old_buff_on_ally_a, unrelated_effect_on_ally_a],
        )

        req = OutOfCombatCastRequest(
            spellId="spell-1", slotLevel=1, variantKey=None, targetPlayerUserId="ally-b"
        )
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=_make_user("caster-1"), session=db
        )

        # --- Assertions ---

        caster_effs = caster_state.state_json.get("active_spell_effects", [])
        ally_a_effs = third_state.state_json.get("active_spell_effects", [])
        ally_b_effs = target_state.state_json.get("active_spell_effects", [])

        # 1. Old concentration group "old-grp" removed from caster state
        old_grp_on_caster = [
            e for e in caster_effs
            if (e.get("metadata") or {}).get("concentration_group") == "old-grp"
        ]
        self.assertEqual(len(old_grp_on_caster), 0,
                         "Old concentration group must be removed from caster")

        # 2. Old concentration group "old-grp" removed from Ally A state
        old_grp_on_ally_a = [
            e for e in ally_a_effs
            if (e.get("metadata") or {}).get("concentration_group") == "old-grp"
        ]
        self.assertEqual(len(old_grp_on_ally_a), 0,
                         "Old concentration group must be removed from Ally A")

        # 3. New concentration group exists on caster state as marker
        new_markers = [
            e for e in caster_effs
            if (e.get("metadata") or {}).get("concentration_marker") is True
        ]
        self.assertEqual(len(new_markers), 1,
                         "Caster must have exactly one concentration marker")
        new_grp = new_markers[0]["metadata"]["concentration_group"]
        self.assertNotEqual(new_grp, "old-grp",
                            "New concentration group must differ from old one")

        # 4. New concentration group exists on Ally B state as buff effect
        new_buffs = [
            e for e in ally_b_effs
            if (e.get("metadata") or {}).get("concentration_group") == new_grp
               and "declarative_effect" in (e.get("metadata") or {})
        ]
        self.assertEqual(len(new_buffs), 1,
                         "Ally B must have the new buff effect with declarative_effect")

        # 5. Ally A keeps unrelated non-concentration effects
        ally_a_unrelated_ids = [
            e["id"] for e in ally_a_effs
            if not (e.get("metadata") or {}).get("concentration")
        ]
        self.assertIn("unrelated-ally-a", ally_a_unrelated_ids,
                       "Ally A must keep unrelated non-concentration effect")

        # 6. Ally B keeps unrelated existing effects + new buff
        ally_b_ids = [e["id"] for e in ally_b_effs]
        self.assertIn("unrelated-ally-b", ally_b_ids,
                      "Ally B must keep unrelated existing effect")
        new_buff_ids = [e["id"] for e in new_buffs]
        self.assertTrue(len(new_buff_ids) >= 1,
                        "Ally B must have the new buff effect")

        # 7. Caster's slot decremented by 1
        caster_used = caster_state.state_json["spellcasting"]["slots"]["1"]["used"]
        self.assertEqual(caster_used, 1, "Caster slot must be decremented by 1")

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session")
    async def test_ally_concentration_replacement_publishes_each_state_once(
        self,
        mock_clear,
        mock_to_state,
        mock_pub,
        mock_fin,
        mock_ensure,
        mock_req,
        mock_entry,
    ):
        mock_to_state.return_value = MagicMock()

        shield = _make_campaign_spell(
            canonical_key="shield_of_faith",
            level=1,
            concentration=True,
            out_of_combat_castable=True,
            effects_json=[_ac_bonus_effect(2)],
            name_pt="Escudo da Fé",
            name_en="Shield of Faith",
        )
        shield.out_of_combat_target = "self_or_ally"

        old_marker = {
            "id": "old-marker",
            "kind": "spell_effect",
            "duration_type": "until_long_rest",
            "metadata": {
                "concentration": True,
                "concentration_marker": True,
                "concentration_group": "old-grp",
                "source_spell_key": "shield_of_faith",
                "caster_player_user_id": "caster-1",
                "target_player_user_id": "ally-a",
            },
        }

        old_buff = {
            "id": "old-buff",
            "kind": "temp_ac_bonus",
            "duration_type": "until_long_rest",
            "metadata": {
                "concentration": True,
                "concentration_group": "old-grp",
                "source_spell_key": "shield_of_faith",
                "caster_player_user_id": "caster-1",
                "target_player_user_id": "ally-a",
            },
        }

        db, caster_state, new_target_state, old_target_state = _make_multiplayer_cast_setup(
            mock_entry,
            mock_ensure,
            shield,
            caster_user_id="caster-1",
            target_user_id="ally-b",
            third_user_id="ally-a",
            slot_level=1,
            caster_active_effects=[old_marker],
            target_active_effects=[],
            third_active_effects=[old_buff],
        )

        mock_clear.return_value = [old_target_state]

        req = OutOfCombatCastRequest(
            spellId="spell-1", slotLevel=1, variantKey=None, targetPlayerUserId="ally-b"
        )
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=_make_user("caster-1"), session=db
        )

        self.assertEqual(mock_pub.call_count, 3,
                         "Should publish exactly 3 state updates (caster, old target, new target)")

        published_ids = {call.args[1] for call in mock_pub.call_args_list}
        self.assertEqual(
            published_ids,
            {"caster-1", "ally-a", "ally-b"},
            "Each affected player must be published exactly once",
        )

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session")
    async def test_ally_concentration_replacement_no_duplicate_publish_when_same_target(
        self,
        mock_clear,
        mock_to_state,
        mock_pub,
        mock_fin,
        mock_ensure,
        mock_req,
        mock_entry,
    ):
        mock_to_state.return_value = MagicMock()

        shield = _make_campaign_spell(
            canonical_key="shield_of_faith",
            level=1,
            concentration=True,
            out_of_combat_castable=True,
            effects_json=[_ac_bonus_effect(2)],
            name_pt="Escudo da Fé",
            name_en="Shield of Faith",
        )
        shield.out_of_combat_target = "self_or_ally"

        old_marker = {
            "id": "old-marker",
            "kind": "spell_effect",
            "duration_type": "until_long_rest",
            "metadata": {
                "concentration": True,
                "concentration_marker": True,
                "concentration_group": "old-grp",
                "source_spell_key": "shield_of_faith",
                "caster_player_user_id": "caster-1",
                "target_player_user_id": "ally-a",
            },
        }

        old_buff = {
            "id": "old-buff",
            "kind": "temp_ac_bonus",
            "duration_type": "until_long_rest",
            "metadata": {
                "concentration": True,
                "concentration_group": "old-grp",
                "source_spell_key": "shield_of_faith",
                "caster_player_user_id": "caster-1",
                "target_player_user_id": "ally-a",
            },
        }

        db, caster_state, target_state, _ = _make_multiplayer_cast_setup(
            mock_entry,
            mock_ensure,
            shield,
            caster_user_id="caster-1",
            target_user_id="ally-a",
            third_user_id=None,
            slot_level=1,
            caster_active_effects=[old_marker],
            target_active_effects=[old_buff],
        )

        mock_clear.return_value = [target_state]

        req = OutOfCombatCastRequest(
            spellId="spell-1", slotLevel=1, variantKey=None, targetPlayerUserId="ally-a"
        )
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=_make_user("caster-1"), session=db
        )

        self.assertEqual(
            mock_pub.call_count,
            2,
            "Should publish exactly 2 state updates (caster + target), not 3",
        )

        published_ids = {call.args[1] for call in mock_pub.call_args_list}
        self.assertEqual(
            published_ids,
            {"caster-1", "ally-a"},
            "Must not duplicate publish when old target == new target",
        )


class TestAllyTargeting(unittest.IsolatedAsyncioTestCase):
    def _make_shield_spell(self):
        return _make_campaign_spell(
            canonical_key="shield_of_faith",
            level=1,
            concentration=True,
            out_of_combat_castable=True,
            effects_json=[_ac_bonus_effect(2)],
            name_pt="Escudo da Fé",
            name_en="Shield of Faith",
        )

    def _make_enhance_spell(self):
        return _make_campaign_spell(
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

    def _setup_two_player_cast(self, mock_get_entry, mock_ensure, campaign_spell, *, slot_level=1):
        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        caster_state_json = _slots_state(level=slot_level, used=0, max_slots=3)
        caster_state_json["spellcasting"]["spells"] = [
            {"id": "spell-1", "canonicalKey": campaign_spell.canonical_key,
             "level": slot_level, "prepared": True}
        ]
        caster_state = MagicMock()
        caster_state.state_json = caster_state_json
        caster_state.id = "ss-caster"
        caster_state.session_id = "session-1"
        caster_state.player_user_id = "caster-1"
        caster_state.created_at = "2026-01-01T00:00:00+00:00"
        caster_state.updated_at = None

        target_state = MagicMock()
        target_state.state_json = {}
        target_state.id = "ss-target"
        target_state.session_id = "session-1"
        target_state.player_user_id = "target-2"
        target_state.created_at = "2026-01-01T00:00:00+00:00"
        target_state.updated_at = None

        db = MagicMock()
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            idx = call_count[0]
            call_count[0] += 1
            if idx == 0:
                r.first.return_value = caster_state   # caster state lookup
            elif idx == 1:
                r.first.return_value = target_state   # target state lookup
            elif idx == 2:
                r.first.return_value = campaign_spell  # campaign spell lookup
            else:
                r.first.return_value = None
                r.all.return_value = []
            return r

        db.exec.side_effect = exec_side
        mock_ensure.return_value = caster_state
        return db, caster_state, target_state

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session", return_value=[])
    async def test_ally_target_effect_lands_on_target_state(
        self, mock_clear_across, mock_to_state, mock_pub, mock_fin, mock_ensure, mock_req, mock_entry
    ):
        mock_to_state.return_value = MagicMock()
        shield = self._make_shield_spell()
        shield.out_of_combat_target = "self_or_ally"
        db, caster_state, target_state = self._setup_two_player_cast(
            mock_entry, mock_ensure, shield
        )
        caster_user = _make_user("caster-1")

        req = OutOfCombatCastRequest(
            spellId="spell-1", slotLevel=1, variantKey=None, targetPlayerUserId="target-2"
        )
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=caster_user, session=db
        )

        # Target state should have the buff effect
        target_effs = target_state.state_json.get("active_spell_effects", [])
        self.assertTrue(len(target_effs) >= 1, "Buff effect must land on target state")
        ac_effects = [e for e in target_effs if e.get("kind") == "temp_ac_bonus"]
        self.assertEqual(len(ac_effects), 1)

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session", return_value=[])
    async def test_ally_target_concentration_creates_caster_marker(
        self, mock_clear_across, mock_to_state, mock_pub, mock_fin, mock_ensure, mock_req, mock_entry
    ):
        mock_to_state.return_value = MagicMock()
        shield = self._make_shield_spell()
        shield.out_of_combat_target = "self_or_ally"
        db, caster_state, target_state = self._setup_two_player_cast(
            mock_entry, mock_ensure, shield
        )
        caster_user = _make_user("caster-1")

        req = OutOfCombatCastRequest(
            spellId="spell-1", slotLevel=1, variantKey=None, targetPlayerUserId="target-2"
        )
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=caster_user, session=db
        )

        # Caster state should have only the concentration marker (not the buff)
        caster_effs = caster_state.state_json.get("active_spell_effects", [])
        self.assertTrue(len(caster_effs) >= 1, "Caster must have concentration marker")
        markers = [e for e in caster_effs if e.get("metadata", {}).get("concentration_marker")]
        self.assertEqual(len(markers), 1)
        # Marker must NOT have declarative_effect (no gameplay bonus on caster)
        self.assertNotIn("declarative_effect", markers[0]["metadata"])

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session", return_value=[])
    async def test_ally_target_spends_caster_slot_only(
        self, mock_clear_across, mock_to_state, mock_pub, mock_fin, mock_ensure, mock_req, mock_entry
    ):
        mock_to_state.return_value = MagicMock()
        shield = self._make_shield_spell()
        shield.out_of_combat_target = "self_or_ally"
        db, caster_state, target_state = self._setup_two_player_cast(
            mock_entry, mock_ensure, shield
        )
        caster_user = _make_user("caster-1")

        req = OutOfCombatCastRequest(
            spellId="spell-1", slotLevel=1, variantKey=None, targetPlayerUserId="target-2"
        )
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=caster_user, session=db
        )

        caster_used = caster_state.state_json["spellcasting"]["slots"]["1"]["used"]
        self.assertEqual(caster_used, 1, "Caster slot must be spent")

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session", return_value=[])
    async def test_self_only_spell_targeting_ally_rejected(
        self, mock_clear_across, mock_to_state, mock_pub, mock_fin, mock_ensure, mock_req, mock_entry
    ):
        from fastapi import HTTPException

        shield = self._make_shield_spell()
        shield.out_of_combat_target = "self"
        db, caster_state, target_state = self._setup_two_player_cast(
            mock_entry, mock_ensure, shield
        )
        caster_user = _make_user("caster-1")

        req = OutOfCombatCastRequest(
            spellId="spell-1", slotLevel=1, variantKey=None, targetPlayerUserId="target-2"
        )
        with self.assertRaises(HTTPException) as ctx:
            await cast_spell_out_of_combat(
                session_id="session-1", req=req, user=caster_user, session=db
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("allies", ctx.exception.detail)

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_invalid_target_not_in_session_rejected(
        self, mock_to_state, mock_pub, mock_fin, mock_ensure, mock_req, mock_entry
    ):
        from fastapi import HTTPException

        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_entry.return_value = entry

        state_json = _slots_state(level=1, used=0, max_slots=3)
        state_json["spellcasting"]["spells"] = [
            {"id": "spell-1", "canonicalKey": "shield_of_faith", "level": 1, "prepared": True}
        ]
        caster_state = MagicMock()
        caster_state.state_json = state_json
        caster_state.id = "ss-caster"
        caster_state.session_id = "session-1"
        caster_state.player_user_id = "caster-1"
        caster_state.created_at = "2026-01-01T00:00:00+00:00"
        caster_state.updated_at = None
        mock_ensure.return_value = caster_state

        db = MagicMock()
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            idx = call_count[0]
            call_count[0] += 1
            if idx == 0:
                r.first.return_value = caster_state
            else:
                r.first.return_value = None   # target not found in session
            return r

        db.exec.side_effect = exec_side

        req = OutOfCombatCastRequest(
            spellId="spell-1", slotLevel=1, variantKey=None, targetPlayerUserId="ghost-user"
        )
        caster_user = _make_user("caster-1")
        with self.assertRaises(HTTPException) as ctx:
            await cast_spell_out_of_combat(
                session_id="session-1", req=req, user=caster_user, session=db
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("participant", ctx.exception.detail)

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_ally_only_spell_without_target_returns_400(
        self, mock_to_state, mock_pub, mock_fin, mock_ensure, mock_req, mock_entry
    ):
        from fastapi import HTTPException

        mock_to_state.return_value = MagicMock()
        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_entry.return_value = entry

        state_json = _slots_state(level=1, used=0, max_slots=3)
        state_json["spellcasting"]["spells"] = [
            {"id": "spell-1", "canonicalKey": "shield_of_faith", "level": 1, "prepared": True}
        ]
        caster_state = MagicMock()
        caster_state.state_json = state_json
        caster_state.id = "ss-caster"
        caster_state.session_id = "session-1"
        caster_state.player_user_id = "caster-1"
        caster_state.created_at = "2026-01-01T00:00:00+00:00"
        caster_state.updated_at = None

        shield = self._make_shield_spell()
        shield.out_of_combat_target = "ally"
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            r.first.return_value = caster_state if call_count[0] == 0 else shield
            call_count[0] += 1
            return r

        db = MagicMock()
        db.exec.side_effect = exec_side
        mock_ensure.return_value = caster_state

        req = OutOfCombatCastRequest(
            spellId="spell-1", slotLevel=1, variantKey=None, targetPlayerUserId=None
        )
        with self.assertRaises(HTTPException) as ctx:
            await cast_spell_out_of_combat(
                session_id="session-1", req=req, user=_make_user("caster-1"), session=db
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("ally target", ctx.exception.detail)

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session", return_value=[])
    async def test_ally_target_effect_includes_caster_and_target_metadata(
        self, mock_clear_across, mock_to_state, mock_pub, mock_fin, mock_ensure, mock_req, mock_entry
    ):
        mock_to_state.return_value = MagicMock()
        shield = self._make_shield_spell()
        shield.out_of_combat_target = "self_or_ally"
        db, caster_state, target_state = self._setup_two_player_cast(
            mock_entry, mock_ensure, shield
        )

        req = OutOfCombatCastRequest(
            spellId="spell-1", slotLevel=1, variantKey=None, targetPlayerUserId="target-2"
        )
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=_make_user("caster-1"), session=db
        )

        target_effs = target_state.state_json.get("active_spell_effects", [])
        self.assertTrue(len(target_effs) >= 1)
        meta = target_effs[0]["metadata"]
        self.assertEqual(meta["caster_player_user_id"], "caster-1")
        self.assertEqual(meta["target_player_user_id"], "target-2")

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session", return_value=[])
    async def test_self_target_still_works(
        self, mock_clear_across, mock_to_state, mock_pub, mock_fin, mock_ensure, mock_req, mock_entry
    ):
        """v1 self-target regression: omitting targetPlayerUserId defaults to self."""
        mock_to_state.return_value = MagicMock()
        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_entry.return_value = entry

        state_json = _slots_state(level=1, used=0, max_slots=3)
        state_json["spellcasting"]["spells"] = [
            {"id": "spell-1", "canonicalKey": "shield_of_faith", "level": 1, "prepared": True}
        ]
        caster_state = MagicMock()
        caster_state.state_json = state_json
        caster_state.id = "ss-caster"
        caster_state.session_id = "session-1"
        caster_state.player_user_id = "caster-1"
        caster_state.created_at = "2026-01-01T00:00:00+00:00"
        caster_state.updated_at = None

        shield = self._make_shield_spell()
        shield.out_of_combat_target = "self_or_ally"
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            r.first.return_value = caster_state if call_count[0] == 0 else shield
            call_count[0] += 1
            return r

        db = MagicMock()
        db.exec.side_effect = exec_side
        mock_ensure.return_value = caster_state

        req = OutOfCombatCastRequest(spellId="spell-1", slotLevel=1, variantKey=None)
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=_make_user("caster-1"), session=db
        )

        # Effect lands on caster's own state (no marker for self-target)
        caster_effs = caster_state.state_json.get("active_spell_effects", [])
        self.assertTrue(len(caster_effs) >= 1)
        markers = [e for e in caster_effs if e.get("metadata", {}).get("concentration_marker")]
        self.assertEqual(len(markers), 0, "Self-target must not create a separate concentration marker")
        ac_effs = [e for e in caster_effs if e.get("kind") == "temp_ac_bonus"]
        self.assertEqual(len(ac_effs), 1, "Buff effect must land directly on caster state")

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session", return_value=[])
    async def test_target_effect_has_matching_concentration_group(
        self, mock_clear_across, mock_to_state, mock_pub, mock_fin, mock_ensure, mock_req, mock_entry
    ):
        """Target effect concentration_group must match caster marker concentration_group."""
        mock_to_state.return_value = MagicMock()
        shield = self._make_shield_spell()
        shield.out_of_combat_target = "self_or_ally"
        db, caster_state, target_state = self._setup_two_player_cast(
            mock_entry, mock_ensure, shield
        )
        caster_user = _make_user("caster-1")

        req = OutOfCombatCastRequest(
            spellId="spell-1", slotLevel=1, variantKey=None, targetPlayerUserId="target-2"
        )
        await cast_spell_out_of_combat(
            session_id="session-1", req=req, user=caster_user, session=db
        )

        caster_effs = caster_state.state_json.get("active_spell_effects", [])
        markers = [e for e in caster_effs if e.get("metadata", {}).get("concentration_marker")]
        self.assertEqual(len(markers), 1, "Caster must have a concentration marker")
        caster_marker = markers[0]
        caster_meta = caster_marker["metadata"]

        target_effs = target_state.state_json.get("active_spell_effects", [])
        ac_effects = [e for e in target_effs if e.get("kind") == "temp_ac_bonus"]
        self.assertEqual(len(ac_effects), 1, "Target must have a temp_ac_bonus effect")
        target_effect = ac_effects[0]
        target_meta = target_effect["metadata"]

        self.assertEqual(
            target_meta["concentration_group"],
            caster_meta["concentration_group"],
            "Target effect concentration_group must match caster marker concentration_group",
        )
        self.assertIn("declarative_effect", target_meta)
        self.assertNotIn("declarative_effect", caster_meta)
        self.assertEqual(target_meta["caster_player_user_id"], "caster-1")
        self.assertEqual(caster_meta["caster_player_user_id"], "caster-1")
        self.assertEqual(target_meta["target_player_user_id"], "target-2")


class TestOutOfCombatActivityLogging(unittest.IsolatedAsyncioTestCase):
    @patch("app.api.routes.sessions.state._prune_out_of_combat_session_activity")
    @patch("app.api.routes.sessions.state.record_session_activity")
    @patch("app.api.routes.sessions.state._resolve_ooc_activity_actor", return_value=("member-1", "Caster One"))
    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session", return_value=[])
    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda d: d)
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_successful_cast_records_out_of_combat_spell_cast_activity(
        self,
        mock_to_state,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
        mock_clear_across,
        mock_resolve_actor,
        mock_record_activity,
        mock_prune_activity,
    ):
        mock_to_state.return_value = MagicMock()
        spell = _make_campaign_spell(
            canonical_key="enhance_ability",
            level=2,
            concentration=True,
            out_of_combat_castable=True,
            variants_json=[{
                "key": "owls_wisdom",
                "labelPt": "Sabedoria da Coruja",
                "effects": [_advantage_effect("wisdom")],
            }],
            name_pt="Melhorar Habilidade",
        )
        spell.out_of_combat_target = "self_or_ally"

        old_marker = {
            "id": "old-marker",
            "kind": "spell_effect",
            "metadata": {
                "concentration": True,
                "concentration_marker": True,
                "concentration_group": "old-grp",
                "source_spell_name": "Melhorar Habilidade",
                "selected_variant_label": "Sabedoria da Coruja",
                "caster_player_user_id": "caster-1",
                "target_player_user_id": "ally-a",
            },
        }
        db, _, _, _ = _make_multiplayer_cast_setup(
            mock_get_entry,
            mock_ensure,
            spell,
            caster_user_id="caster-1",
            target_user_id="ally-b",
            slot_level=2,
            caster_active_effects=[old_marker],
        )

        req = OutOfCombatCastRequest(
            spellId="spell-1",
            slotLevel=2,
            variantKey="owls_wisdom",
            targetPlayerUserId="ally-b",
        )
        await cast_spell_out_of_combat(
            session_id="session-1",
            req=req,
            user=_make_user("caster-1"),
            session=db,
        )

        mock_record_activity.assert_called_once()
        activity_call = mock_record_activity.call_args
        self.assertEqual(activity_call.args[1], "out_of_combat_spell_cast")
        payload = activity_call.kwargs["payload"]
        self.assertEqual(payload["actor_player_user_id"], "caster-1")
        self.assertEqual(payload["actor_display_name"], "Caster One")
        self.assertEqual(payload["target_player_user_id"], "ally-b")
        self.assertEqual(payload["target_display_name"], "ally-b")
        self.assertEqual(payload["spell_key"], "enhance_ability")
        self.assertEqual(payload["spell_name"], "Melhorar Habilidade")
        self.assertEqual(payload["variant_key"], "owls_wisdom")
        self.assertEqual(payload["variant_label"], "Sabedoria da Coruja")
        self.assertEqual(payload["slot_level"], 2)
        self.assertTrue(payload["replaced_concentration"])
        self.assertEqual(payload["previous_concentration_group"], "old-grp")
        self.assertEqual(payload["previous_spell_name"], "Melhorar Habilidade")
        self.assertEqual(payload["previous_variant_label"], "Sabedoria da Coruja")
        self.assertIsNotNone(payload["new_concentration_group"])
        self.assertEqual(payload["concentration_group"], payload["new_concentration_group"])
        self.assertGreaterEqual(len(payload["created_effect_ids"]), 1)
        mock_prune_activity.assert_called_once_with(db, "session-1")

    @patch("app.api.routes.sessions.state._prune_out_of_combat_session_activity")
    @patch("app.api.routes.sessions.state.record_session_activity")
    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    async def test_rejected_cast_does_not_record_activity(
        self,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
        mock_record_activity,
        mock_prune_activity,
    ):
        from fastapi import HTTPException

        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        mock_get_entry.return_value = entry

        state_json = _slots_state(level=3, used=0, max_slots=2)
        state_json["spellcasting"]["spells"] = [
            {"id": "spell-fb-1", "canonicalKey": "fireball", "level": 3, "prepared": True}
        ]
        state = MagicMock()
        state.state_json = state_json
        state.id = "ss-1"
        state.session_id = "session-1"
        state.player_user_id = "user-1"

        fireball = _make_campaign_spell(
            canonical_key="fireball",
            level=3,
            out_of_combat_castable=False,
        )
        call_count = [0]

        def exec_side(q, **kw):
            r = MagicMock()
            r.first.return_value = state if call_count[0] == 0 else fireball
            call_count[0] += 1
            return r

        db = MagicMock()
        db.exec.side_effect = exec_side
        mock_ensure.return_value = state

        req = OutOfCombatCastRequest(spellId="spell-fb-1", slotLevel=3, variantKey=None)
        with self.assertRaises(HTTPException):
            await cast_spell_out_of_combat(
                session_id="session-1",
                req=req,
                user=_make_user("user-1"),
                session=db,
            )

        mock_record_activity.assert_not_called()
        mock_prune_activity.assert_not_called()


class TestOutOfCombatActivityPrune(unittest.TestCase):
    def test_prune_keeps_only_ooc_types_with_cap_offset(self):
        db = MagicMock()
        first_result = MagicMock()
        first_result.all.return_value = ["evt-1", "evt-2"]
        db.exec.side_effect = [first_result, MagicMock()]

        _prune_out_of_combat_session_activity(db, "session-1")

        self.assertEqual(db.exec.call_count, 2)
        select_query = db.exec.call_args_list[0].args[0]
        select_sql = str(select_query.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("session_command_event.command_type IN", select_sql)
        self.assertIn("'out_of_combat_spell_cast'", select_sql)
        self.assertIn("'out_of_combat_effect_removed'", select_sql)
        self.assertIn("OFFSET 50", select_sql)

        delete_query = db.exec.call_args_list[1].args[0]
        delete_sql = str(delete_query.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("DELETE FROM session_command_event", delete_sql)
        self.assertIn("'evt-1'", delete_sql)
        self.assertIn("'evt-2'", delete_sql)
