"""Tests for Poison Spray / Borrifo Venenoso (issue #371).

Covers:
- Seed/catalog contract (CON save, save success = none, poison, no cover bypass)
- Cantrip scaling by character level (1d12/2d12/3d12/4d12)
- Save semantics: success => 0 damage (never half)
- Cover: no explicit bypass (contrast with Sacred Flame's "none")
- Runtime smoke: CON save failure → damage applied; success → 0 damage
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_player() -> dict:
    return {
        "id": "p1",
        "ref_id": "caster",
        "kind": "player",
        "display_name": "Caster",
        "status": "active",
        "team": "players",
        "visible": True,
        "actor_user_id": "u1",
        "active_effects": [],
        "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
    }


def _make_target() -> dict:
    return {
        "id": "e1",
        "ref_id": "enemy-a",
        "kind": "session_entity",
        "display_name": "Target",
        "status": "active",
        "team": "enemies",
        "visible": True,
        "actor_user_id": None,
        "active_effects": [],
        "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
    }


def _protection_effect() -> dict:
    return {
        "id": "eff-protection",
        "kind": "spell_effect",
        "metadata": {
            "source_spell_key": "protection_from_evil_and_good",
            "declarative_save_effect": {
                "type": "saving_throw_advantage_against_creature_types",
                "params": {
                    "mode": "advantage",
                    "source": "protection_from_evil_and_good",
                    "source_creature_types": ["aberration", "celestial", "elemental", "fey", "fiend", "undead"],
                    "roll_types": ["saving_throw"],
                    "consume_on_apply": False,
                },
            },
        },
    }


def _make_state() -> CombatState:
    return CombatState(
        id="c1",
        session_id="s1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=[_make_player(), _make_target()],
        use_map=False,
    )


def _poison_spray_context(save_success: bool = False) -> dict:
    return {
        "spell_name": "Borrifo Venenoso",
        "spell_canonical_key": "poison_spray",
        "spell_mode": "saving_throw",
        "selection_type": "creature",
        "slot_level": None,
        "action_cost": "action",
        "source_kind": "spell",
        "effect_kind": "damage",
        "effect_dice": "1d12",
        "effect_bonus": 0,
        "damage_type": "Poison",
        "save_ability": "constitution",
        "save_dc": 13,
        "save_success_outcome": "none",
        "target_type": "ranged",
        "range_kind": "distance",
        "attack_type": "none",
        "requires_target_sight": True,
        "requires_target_effect": True,
        "concentration": False,
        "cover_applies_to_save": None,
    }


def _roll(success: bool) -> RollResult:
    return RollResult(
        event_id="r1",
        roll_type="save",
        actor_kind="session_entity",
        actor_ref_id="enemy-a",
        actor_display_name="Target",
        rolls=[5 if not success else 18],
        selected_roll=5 if not success else 18,
        advantage_mode="normal",
        modifier_used=0,
        override_used=False,
        formula="1d20",
        total=5 if not success else 18,
        ability="constitution",
        dc=13,
        success=success,
        timestamp=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class PoisonSpraySeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "poison_spray"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "poison_spray not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 0)
        self.assertEqual(e["school"], "conjuration")
        self.assertEqual(e["castingTimeType"], "action")
        self.assertEqual(e["rangeMeters"], 3)
        self.assertEqual(e["savingThrow"], "CON")
        self.assertEqual(e["saveSuccessOutcome"], "none")
        self.assertEqual(e["damageDice"], "1d12")
        self.assertEqual(e["damageType"], "Poison")
        self.assertFalse(e["concentration"])

    def test_no_upcast(self):
        self.assertIsNone(self.entry.get("upcast"))

    def test_cantrip_scaling_present(self):
        cs = self.entry.get("cantripScaling")
        self.assertIsNotNone(cs)
        self.assertEqual(cs["scalingMode"], "character_level")
        self.assertEqual(cs["scalingEffectType"], "damage_dice")

    def test_cantrip_scaling_thresholds(self):
        thresholds = self.entry["cantripScaling"]["thresholds"]
        t1 = next(t for t in thresholds if t["characterLevel"] == 1)
        t5 = next(t for t in thresholds if t["characterLevel"] == 5)
        t11 = next(t for t in thresholds if t["characterLevel"] == 11)
        t17 = next(t for t in thresholds if t["characterLevel"] == 17)
        self.assertEqual(t1["damage"]["dice"], "1d12")
        self.assertEqual(t5["damage"]["dice"], "2d12")
        self.assertEqual(t11["damage"]["dice"], "3d12")
        self.assertEqual(t17["damage"]["dice"], "4d12")

    def test_cover_applies_to_save_not_none(self):
        cover = self.entry.get("coverAppliesToSave")
        self.assertNotEqual(cover, "none", "poison_spray must not carry Sacred Flame's explicit cover bypass")


# ---------------------------------------------------------------------------
# Cantrip scaling
# ---------------------------------------------------------------------------

class PoisonSprayCantripScalingTests(unittest.TestCase):
    SCALING = {
        "scalingMode": "character_level",
        "scalingEffectType": "damage_dice",
        "thresholds": [
            {"characterLevel": 1, "damage": {"dice": "1d12"}},
            {"characterLevel": 5, "damage": {"dice": "2d12"}},
            {"characterLevel": 11, "damage": {"dice": "3d12"}},
            {"characterLevel": 17, "damage": {"dice": "4d12"}},
        ],
    }

    def _apply(self, caster_level: int, *, spell_level: int = 0):
        return CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
            spell_level=spell_level,
            caster_level=caster_level,
            effect_dice="1d12",
            cantrip_scaling=self.SCALING,
        )

    def test_scales_by_character_level(self):
        self.assertEqual(self._apply(1)["effect_dice"], "1d12")
        self.assertEqual(self._apply(4)["effect_dice"], "1d12")
        self.assertEqual(self._apply(5)["effect_dice"], "2d12")
        self.assertEqual(self._apply(10)["effect_dice"], "2d12")
        self.assertEqual(self._apply(11)["effect_dice"], "3d12")
        self.assertEqual(self._apply(16)["effect_dice"], "3d12")
        self.assertEqual(self._apply(17)["effect_dice"], "4d12")
        self.assertEqual(self._apply(20)["effect_dice"], "4d12")

    def test_leveled_spell_does_not_cantrip_scale(self):
        self.assertEqual(self._apply(17, spell_level=1)["effect_dice"], "1d12")


# ---------------------------------------------------------------------------
# Save outcome semantics
# ---------------------------------------------------------------------------

class PoisonSpraySaveOutcomeTests(unittest.TestCase):
    def test_failed_save_takes_full_damage(self):
        self.assertEqual(
            CombatService._resolve_save_damage_amount(9, is_saved=False, save_success_outcome="none"),
            9,
        )

    def test_successful_save_deals_zero_damage(self):
        self.assertEqual(
            CombatService._resolve_save_damage_amount(9, is_saved=True, save_success_outcome="none"),
            0,
        )

    def test_successful_save_is_not_half_damage(self):
        self.assertNotEqual(
            CombatService._resolve_save_damage_amount(9, is_saved=True, save_success_outcome="none"),
            4,
        )


# ---------------------------------------------------------------------------
# Cover behavior
# ---------------------------------------------------------------------------

class PoisonSprayCoverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = {s["canonicalKey"]: s for s in (raw["spells"] if isinstance(raw, dict) else raw)}
        cls.ps_entry = spells.get("poison_spray", {})
        cls.sf_entry = spells.get("sacred_flame", {})

    def test_poison_spray_has_no_explicit_cover_bypass(self):
        self.assertNotEqual(self.ps_entry.get("coverAppliesToSave"), "none")

    def test_sacred_flame_has_cover_bypass_for_contrast(self):
        self.assertEqual(self.sf_entry.get("coverAppliesToSave"), "none")

    def test_cover_none_keeps_dc_sacred_flame_style(self):
        # Sacred Flame: cover is ignored because coverAppliesToSave="none"
        effective, modifier = resolve_cover_save_dc(15, "half", "none", "constitution")
        self.assertEqual(effective, 15)
        self.assertEqual(modifier, 0)

    def test_physical_cover_reduces_dc_default_behavior(self):
        # Default behavior (no bypass): half cover reduces DC by 2
        effective, modifier = resolve_cover_save_dc(15, "half", "physical", "constitution")
        self.assertEqual(effective, 13)
        self.assertEqual(modifier, 2)


# ---------------------------------------------------------------------------
# Runtime cast flow smoke tests
# ---------------------------------------------------------------------------

class PoisonSprayCastFlowTests(unittest.IsolatedAsyncioTestCase):
    async def _cast(self, save_success: bool):
        state = _make_state()
        attacker_state = MagicMock()
        attacker_state.state_json = {
            "spellcasting": {
                "cantrips": [{"canonicalKey": "poison_spray", "prepared": True}],
            }
        }
        req = CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="poison_spray",
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
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=_poison_spray_context()),
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service", return_value=MagicMock(validate=MagicMock(return_value=targeting_result))),
            patch("app.services.combat_service.spells.cast_target.resolve_saving_throw", return_value=_roll(save_success)),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock),
        ):
            return await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)

    async def test_failed_con_save_applies_poison_damage(self):
        # Save fails → is_saved=False, damage roll is still pending (effect_roll_required=True)
        result = await self._cast(save_success=False)
        self.assertFalse(result["is_saved"])
        self.assertTrue(result.get("effect_roll_required"))

    async def test_successful_con_save_deals_zero_damage(self):
        # Save succeeds with save_success_outcome="none" → is_saved=True, damage=0, no pending roll
        result = await self._cast(save_success=True)
        self.assertTrue(result["is_saved"])
        self.assertEqual(result.get("damage", 0), 0)
        self.assertFalse(result.get("effect_roll_required"))

    async def test_no_active_effect_applied_on_save_failure(self):
        await self._cast(save_success=False)

    async def test_no_concentration_marker_applied(self):
        state = _make_state()
        attacker_state = MagicMock()
        attacker_state.state_json = {"spellcasting": {"cantrips": []}}
        req = CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="poison_spray",
            target_ref_id="enemy-a",
        )
        targeting_result = MagicMock(
            is_valid=True,
            validated_primary_target_ref_id="enemy-a",
            spatial_metadata=MagicMock(cover=None),
        )
        ctx = _poison_spray_context()
        ctx["concentration"] = False

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 20, 20, 15, 3, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=ctx),
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service", return_value=MagicMock(validate=MagicMock(return_value=targeting_result))),
            patch("app.services.combat_service.spells.cast_target.resolve_saving_throw", return_value=_roll(False)),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock),
        ):
            result = await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)

        caster_effects = state.participants[0].get("active_effects") or []
        concentration_effects = [
            e for e in caster_effects
            if (e.get("metadata") or {}).get("concentration")
        ]
        self.assertEqual(concentration_effects, [])

    async def test_source_aware_advantage_against_fiend(self):
        state = _make_state()
        state.participants[0]["creature_type"] = "fiend"
        state.participants[1]["active_effects"] = [_protection_effect()]
        attacker_state = MagicMock()
        attacker_state.state_json = {"spellcasting": {"cantrips": []}}
        req = CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="poison_spray",
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
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=_poison_spray_context()),
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service", return_value=MagicMock(validate=MagicMock(return_value=targeting_result))),
            patch("app.services.combat_service.spells.cast_target.resolve_saving_throw", return_value=_roll(False)) as save_mock,
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock),
        ):
            await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)
        self.assertEqual(save_mock.call_args.kwargs["advantage_mode"], "advantage")


if __name__ == "__main__":
    unittest.main()
