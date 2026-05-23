"""Tests for Acid Splash (Borrifo Ácido) cantrip.

Covers:
- Seed contract: DEX save, saveSuccessOutcome=none, maxTargets=2, coverAppliesToSave=physical
- Cantrip scaling (damage_dice): 1d6/2d6/3d6/4d6 at char levels 1/5/11/17
- Save semantics: success → 0 damage (never half)
- Cover: physical cover reduces effective save DC
- Runtime smoke: save failure → damage pending; save success → 0 damage
"""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.schemas.combat import CombatCastSpellRequest
from app.schemas.roll import RollResult
from app.services.combat import CombatService
from app.services.combat_service.cover_modifiers import resolve_cover_save_dc
from app.services.combat_service.spell_dice_math import CombatSpellDiceMathMixin


ACID_SPLASH_SCALING = {
    "scalingMode": "character_level",
    "scalingEffectType": "damage_dice",
    "thresholds": [
        {"characterLevel": 1, "damage": {"dice": "1d6"}},
        {"characterLevel": 5, "damage": {"dice": "2d6"}},
        {"characterLevel": 11, "damage": {"dice": "3d6"}},
        {"characterLevel": 17, "damage": {"dice": "4d6"}},
    ],
}


def _make_player() -> dict:
    return {
        "id": "p1", "ref_id": "caster", "kind": "player",
        "display_name": "Caster", "status": "active", "team": "players",
        "visible": True, "actor_user_id": "u1", "active_effects": [],
        "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
    }


def _make_target(ref_id="enemy-a") -> dict:
    return {
        "id": ref_id, "ref_id": ref_id, "kind": "session_entity",
        "display_name": "Target", "status": "active", "team": "enemies",
        "visible": True, "actor_user_id": None, "active_effects": [],
        "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
    }


def _make_state() -> CombatState:
    return CombatState(
        id="c1", session_id="s1", phase=CombatPhase.active,
        round=1, current_turn_index=0,
        participants=[_make_player(), _make_target()],
        use_map=False,
    )


def _context() -> dict:
    return {
        "spell_name": "Borrifo Ácido",
        "spell_canonical_key": "acid_splash",
        "spell_mode": "saving_throw",
        "selection_type": "creature",
        "slot_level": None,
        "action_cost": "action",
        "source_kind": "spell",
        "effect_kind": "damage",
        "effect_dice": "1d6",
        "effect_bonus": 0,
        "damage_type": "Acid",
        "save_ability": "dexterity",
        "save_dc": 13,
        "save_success_outcome": "none",
        "target_type": "ranged",
        "range_kind": "distance",
        "attack_type": "none",
        "requires_target_sight": True,
        "requires_target_effect": True,
        "concentration": False,
        "cover_applies_to_save": "physical",
    }


def _roll(success: bool) -> RollResult:
    return RollResult(
        event_id="r1", roll_type="save",
        actor_kind="session_entity", actor_ref_id="enemy-a",
        actor_display_name="Target",
        rolls=[5 if not success else 18],
        selected_roll=5 if not success else 18,
        advantage_mode="normal", modifier_used=0, override_used=False,
        formula="1d20", total=5 if not success else 18,
        ability="dexterity", dc=13, success=success,
        timestamp=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class AcidSplashSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "acid_splash"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "acid_splash not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 0)
        self.assertEqual(e["school"], "conjuration")
        self.assertEqual(e["castingTimeType"], "action")
        self.assertEqual(e["savingThrow"], "DEX")
        self.assertEqual(e["saveSuccessOutcome"], "none")
        self.assertEqual(e["damageDice"], "1d6")
        self.assertEqual(e["damageType"], "Acid")
        self.assertFalse(e["concentration"])

    def test_max_targets_is_2(self):
        self.assertEqual(self.entry.get("maxTargets"), 2)

    def test_cover_applies_to_save_physical(self):
        self.assertEqual(self.entry.get("coverAppliesToSave"), "physical")

    def test_cantrip_scaling_present(self):
        cs = self.entry.get("cantripScaling")
        self.assertIsNotNone(cs)
        self.assertEqual(cs["scalingMode"], "character_level")
        self.assertEqual(cs["scalingEffectType"], "damage_dice")

    def test_cantrip_scaling_thresholds(self):
        thresholds = self.entry["cantripScaling"]["thresholds"]
        by_level = {t["characterLevel"]: t["damage"]["dice"] for t in thresholds}
        self.assertEqual(by_level[1], "1d6")
        self.assertEqual(by_level[5], "2d6")
        self.assertEqual(by_level[11], "3d6")
        self.assertEqual(by_level[17], "4d6")

    def test_no_upcast(self):
        self.assertIsNone(self.entry.get("upcast"))


# ---------------------------------------------------------------------------
# Cantrip scaling
# ---------------------------------------------------------------------------

class AcidSplashCantripScalingTests(unittest.TestCase):
    def _apply(self, caster_level: int):
        return CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
            spell_level=0,
            caster_level=caster_level,
            effect_dice="1d6",
            cantrip_scaling=ACID_SPLASH_SCALING,
        )

    def test_scales_by_character_level(self):
        self.assertEqual(self._apply(1)["effect_dice"], "1d6")
        self.assertEqual(self._apply(4)["effect_dice"], "1d6")
        self.assertEqual(self._apply(5)["effect_dice"], "2d6")
        self.assertEqual(self._apply(10)["effect_dice"], "2d6")
        self.assertEqual(self._apply(11)["effect_dice"], "3d6")
        self.assertEqual(self._apply(16)["effect_dice"], "3d6")
        self.assertEqual(self._apply(17)["effect_dice"], "4d6")
        self.assertEqual(self._apply(20)["effect_dice"], "4d6")

    def test_cantrip_instance_count_always_none(self):
        for level in [1, 5, 11, 17]:
            result = self._apply(level)
            self.assertIsNone(result["cantrip_instance_count"])

    def test_leveled_spell_does_not_scale(self):
        result = CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
            spell_level=1, caster_level=17, effect_dice="1d6",
            cantrip_scaling=ACID_SPLASH_SCALING,
        )
        self.assertEqual(result["effect_dice"], "1d6")


# ---------------------------------------------------------------------------
# Save outcome semantics
# ---------------------------------------------------------------------------

class AcidSplashSaveOutcomeTests(unittest.TestCase):
    def test_failed_save_takes_full_damage(self):
        self.assertEqual(
            CombatService._resolve_save_damage_amount(8, is_saved=False, save_success_outcome="none"),
            8,
        )

    def test_successful_save_deals_zero_damage(self):
        self.assertEqual(
            CombatService._resolve_save_damage_amount(8, is_saved=True, save_success_outcome="none"),
            0,
        )


# ---------------------------------------------------------------------------
# Cover behavior
# ---------------------------------------------------------------------------

class AcidSplashCoverTests(unittest.TestCase):
    def test_physical_cover_reduces_save_dc(self):
        effective, modifier = resolve_cover_save_dc(13, "half", "physical", "dexterity")
        self.assertLess(effective, 13)
        self.assertGreater(modifier, 0)

    def test_no_cover_keeps_full_dc(self):
        effective, modifier = resolve_cover_save_dc(13, None, "physical", "dexterity")
        self.assertEqual(effective, 13)
        self.assertEqual(modifier, 0)


# ---------------------------------------------------------------------------
# Runtime cast flow smoke tests
# ---------------------------------------------------------------------------

class AcidSplashCastFlowTests(unittest.IsolatedAsyncioTestCase):
    async def _cast(self, save_success: bool):
        state = _make_state()
        attacker_state = MagicMock()
        attacker_state.state_json = {
            "spellcasting": {"cantrips": [{"canonicalKey": "acid_splash", "prepared": True}]},
        }
        req = CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="acid_splash",
            target_ref_id="enemy-a",
        )
        targeting_result = MagicMock(
            is_valid=True,
            validated_primary_target_ref_id="enemy-a",
            spatial_metadata=MagicMock(cover=None),
        )

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 20, 20, 15, 3, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=_context()),
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service", return_value=MagicMock(validate=MagicMock(return_value=targeting_result))),
            patch("app.services.combat_service.spells.cast_target.resolve_saving_throw", return_value=_roll(save_success)),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock),
        ):
            return await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)

    async def test_failed_dex_save_requires_damage_roll(self):
        result = await self._cast(save_success=False)
        self.assertFalse(result["is_saved"])
        self.assertTrue(result.get("effect_roll_required"))

    async def test_successful_dex_save_deals_zero_damage(self):
        result = await self._cast(save_success=True)
        self.assertTrue(result["is_saved"])
        self.assertEqual(result.get("damage", 0), 0)
        self.assertFalse(result.get("effect_roll_required"))

    async def test_no_concentration_applied(self):
        state = _make_state()
        attacker_state = MagicMock()
        attacker_state.state_json = {"spellcasting": {"cantrips": []}}
        req = CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="acid_splash",
            target_ref_id="enemy-a",
        )
        targeting_result = MagicMock(
            is_valid=True,
            validated_primary_target_ref_id="enemy-a",
            spatial_metadata=MagicMock(cover=None),
        )

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 20, 20, 15, 3, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=_context()),
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service", return_value=MagicMock(validate=MagicMock(return_value=targeting_result))),
            patch("app.services.combat_service.spells.cast_target.resolve_saving_throw", return_value=_roll(False)),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock),
        ):
            result = await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)
        caster = next(p for p in state.participants if p["id"] == "p1")
        concentration_effects = [
            e for e in caster.get("active_effects", [])
            if e.get("metadata", {}).get("concentration")
        ]
        self.assertEqual(len(concentration_effects), 0)
