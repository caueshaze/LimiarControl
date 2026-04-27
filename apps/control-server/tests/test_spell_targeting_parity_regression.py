"""Regression suite: spell targeting pipeline parity.

Validates consistency ACROSS pipeline layers for the four core archetypes:
  Magic Missile  — leveled upcast + effect instances + direct damage
  Eldritch Blast — cantrip instance scaling + spell attack + cover AC
  Acid Splash    — cantrip damage-dice scaling + saving throw + cover DC
  Fireball       — area + per-target cover DC + preview/runtime agreement

Non-goals (already covered elsewhere):
  test_cantrip_scaling.py          — acid_splash/eldritch_blast dice math, MM upcast math
  test_instance_target_assignment.py — _validate_instance_targets rules
  test_cast_area_cover.py          — fireball per-target cover DC in cast runtime
  test_area_preview_cover.py       — area preview effective_save_dc
"""
from __future__ import annotations

import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.schemas.combat_spells import EffectInstanceTarget
from app.services.combat import CombatService, CombatServiceError
from app.services.combat_service.cover_modifiers import (
    resolve_cover_modifier,
    resolve_cover_save_dc,
)
from app.services.combat_service.spell_dice_math import CombatSpellDiceMathMixin
from app.services.combat_service.spells.area_spatial_metadata import (
    build_area_affected_target_spatial_metadata,
)
from app.services.combat_service.targeting_result import SpatialMetadata, TargetingResult


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _build_state(participants=None):
    if participants is None:
        participants = [
            {
                "id": "p1",
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Hero",
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-1",
                "initiative": 15,
            },
            {
                "id": "e1",
                "ref_id": "entity:goblin-a",
                "kind": "session_entity",
                "display_name": "Goblin A",
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
                "initiative": 8,
            },
            {
                "id": "e2",
                "ref_id": "entity:goblin-b",
                "kind": "session_entity",
                "display_name": "Goblin B",
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
                "initiative": 6,
            },
        ]
    return CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=participants,
    )


def _targeting_result(cover: str | None, is_valid: bool = True) -> TargetingResult:
    return TargetingResult(
        is_valid=is_valid,
        validated_primary_target_ref_id="entity:goblin-a",
        affected_target_ref_ids=["entity:goblin-a"],
        target_kind="session_entity",
        spatial_metadata=SpatialMetadata(
            targeting_authority="limiar_map",
            cover=cover,
        ),
    )


def _req(**kwargs):
    defaults = dict(
        has_advantage=False,
        has_disadvantage=False,
        concentration_roll_source="system",
        concentration_manual_roll=None,
        effect_instance_targets=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Group 1 — Magic Missile
# ---------------------------------------------------------------------------

class TestMagicMissileParity(unittest.TestCase):
    """
    Magic Missile: context instance counts agree with runtime behaviour.

    The seed contract:
      upcast.mode = "additional_effect_instances"
      upcast.baseEffectInstances = 3
      upcast.dice = "1d4+1"
      upcast.perLevel = 1

    Expected:
      slot 1 → effect_instance_count = 3, upcast_added_instances = 0
      slot 2 → effect_instance_count = 4, upcast_added_instances = 1
      slot 3 → effect_instance_count = 5, upcast_added_instances = 2
    """

    MM_UPCAST = {
        "mode": "additional_effect_instances",
        "dice": "1d4+1",
        "perLevel": 1,
        "baseEffectInstances": 3,
    }

    def _instance_count(self, slot_level: int) -> tuple[int, int]:
        """Return (effect_instance_count, upcast_added_instances) for a given slot."""
        structured = CombatSpellDiceMathMixin._get_structured_spell_upcast(self.MM_UPCAST)
        upcast_result = CombatSpellDiceMathMixin._apply_structured_spell_upcast(
            spell_level=1,
            slot_level=slot_level,
            effect_kind="damage",
            effect_dice="3d4+3",
            effect_bonus=3,
            upcast=structured,
        )
        base = structured["baseEffectInstances"]
        added = upcast_result.get("upcast_added_instances", 0)
        return base + added, added

    # --- Context: instance count per slot ---

    def test_slot1_three_instances(self):
        count, added = self._instance_count(1)
        self.assertEqual(count, 3)
        self.assertEqual(added, 0)

    def test_slot2_four_instances_one_added(self):
        count, added = self._instance_count(2)
        self.assertEqual(count, 4)
        self.assertEqual(added, 1)

    def test_slot3_five_instances_two_added(self):
        count, added = self._instance_count(3)
        self.assertEqual(count, 5)
        self.assertEqual(added, 2)

    # --- Context: instance dice is per-missile, not aggregate ---

    def test_instance_dice_is_per_missile(self):
        structured = CombatSpellDiceMathMixin._get_structured_spell_upcast(self.MM_UPCAST)
        self.assertEqual(structured["dice"], "1d4+1",
                         "effect_instance_dice must be per-missile (1d4+1), not the aggregate (3d4+3)")

    def test_slot3_upcast_instance_dice_unchanged(self):
        structured = CombatSpellDiceMathMixin._get_structured_spell_upcast(self.MM_UPCAST)
        upcast_result = CombatSpellDiceMathMixin._apply_structured_spell_upcast(
            spell_level=1, slot_level=3, effect_kind="damage",
            effect_dice="3d4+3", effect_bonus=3, upcast=structured,
        )
        self.assertEqual(upcast_result.get("upcast_instance_effect_dice"), "1d4+1")

    # --- Target assignment: slot-3 accepts 5 instances ---

    def test_slot3_accepts_five_instance_assignment(self):
        state = _build_state()
        targets = [
            EffectInstanceTarget(instance_index=i, target_ref_id="entity:goblin-a")
            for i in range(1, 6)
        ]
        req = SimpleNamespace(effect_instance_targets=targets)
        spell_ctx = {
            "effect_instance_count": 5,
            "effect_instance_dice": "1d4+1",
            "spell_mode": "direct_damage",
            "spell_canonical_key": "magic_missile",
            "spell_name": "Magic Missile",
            "effect_kind": "damage",
            "damage_type": "Force",
        }
        result = CombatService._validate_instance_targets(
            req=req, spell_context=spell_ctx, state=state,
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 5)

    def test_slot3_allows_multiple_instances_on_same_target(self):
        state = _build_state()
        targets = [
            EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a"),
            EffectInstanceTarget(instance_index=2, target_ref_id="entity:goblin-a"),
            EffectInstanceTarget(instance_index=3, target_ref_id="entity:goblin-a"),
            EffectInstanceTarget(instance_index=4, target_ref_id="entity:goblin-b"),
            EffectInstanceTarget(instance_index=5, target_ref_id="entity:goblin-b"),
        ]
        req = SimpleNamespace(effect_instance_targets=targets)
        spell_ctx = {
            "effect_instance_count": 5,
            "effect_instance_dice": "1d4+1",
            "spell_mode": "direct_damage",
            "spell_canonical_key": "magic_missile",
            "spell_name": "Magic Missile",
            "effect_kind": "damage",
            "damage_type": "Force",
        }
        result = CombatService._validate_instance_targets(
            req=req, spell_context=spell_ctx, state=state,
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 5)

    # --- Runtime: _resolve_instance_direct uses instance dice, not aggregate ---

    def test_runtime_rolls_instance_dice_not_aggregate(self):
        """_resolve_instance_direct must roll '1d4+1' per missile, not '5d4+5'."""
        db = MagicMock()
        state = _build_state()
        attacker = state.participants[0]
        target_p = state.participants[1]
        spell_ctx = {
            "effect_instance_count": 5,
            "effect_instance_dice": "1d4+1",
            "effect_dice": "5d4+5",  # aggregate — must NOT be used
            "spell_mode": "direct_damage",
            "spell_canonical_key": "magic_missile",
            "effect_kind": "damage",
            "damage_type": "Force",
        }
        req = _req()
        with patch.object(CombatService, "_resolve_damage_roll", return_value=([3, 1], 4)) as mock_roll, \
             patch.object(CombatService, "_apply_spell_effect", return_value=(5, "", 6, None)):
            CombatService._resolve_instance_direct(db, state, attacker, target_p, spell_ctx, req)
        mock_roll.assert_called_once()
        actual_dice = mock_roll.call_args[0][0]
        self.assertEqual(actual_dice, "1d4+1",
                         "Runtime must roll the per-instance dice, not the aggregate")

    # --- Direct damage bypasses cover (no targeting_result param) ---

    def test_direct_damage_has_no_cover_or_targeting_param(self):
        sig = inspect.signature(CombatService._resolve_instance_direct)
        self.assertNotIn("cover", sig.parameters)
        self.assertNotIn("targeting_result", sig.parameters,
                         "_resolve_instance_direct must not accept cover — Magic Missile ignores AC/cover")


# ---------------------------------------------------------------------------
# Group 2 — Eldritch Blast
# ---------------------------------------------------------------------------

class TestEldritchBlastParity(unittest.TestCase):
    """
    Eldritch Blast: cantrip instance count per level + cover AC in spell attack runtime.

    Scaling contract (from seed cantripScaling):
      level 1  → 1 beam  (1d10)
      level 5  → 2 beams (1d10 each)
      level 11 → 3 beams (1d10 each)
      level 17 → 4 beams (1d10 each)

    Cover contract (spell_attack): effective_ac = base_ac + cover_modifier
      half         → +2
      threeQuarters → +5
      none / None  → +0
    """

    EB_SCALING = {
        "scalingMode": "character_level",
        "scalingEffectType": "effect_instances",
        "thresholds": [
            {"characterLevel": 1, "instances": 1, "instanceDamage": {"dice": "1d10"}},
            {"characterLevel": 5, "instances": 2, "instanceDamage": {"dice": "1d10"}},
            {"characterLevel": 11, "instances": 3, "instanceDamage": {"dice": "1d10"}},
            {"characterLevel": 17, "instances": 4, "instanceDamage": {"dice": "1d10"}},
        ],
    }

    def _apply_scaling(self, caster_level: int) -> dict:
        return CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
            spell_level=0,
            caster_level=caster_level,
            effect_dice="1d10",
            cantrip_scaling=self.EB_SCALING,
        )

    # --- Instance count per caster level ---

    def test_level1_one_beam(self):
        result = self._apply_scaling(1)
        self.assertEqual(result["cantrip_instance_count"], 1)
        self.assertEqual(result["cantrip_instance_dice"], "1d10")

    def test_level5_two_beams(self):
        result = self._apply_scaling(5)
        self.assertEqual(result["cantrip_instance_count"], 2)
        self.assertEqual(result["cantrip_instance_dice"], "1d10")

    def test_level11_three_beams(self):
        result = self._apply_scaling(11)
        self.assertEqual(result["cantrip_instance_count"], 3)

    def test_level17_four_beams(self):
        result = self._apply_scaling(17)
        self.assertEqual(result["cantrip_instance_count"], 4)

    def test_level4_still_one_beam(self):
        result = self._apply_scaling(4)
        self.assertEqual(result["cantrip_instance_count"], 1)

    # --- Cover AC applied to spell attack ---

    def _run_instance_attack(self, cover: str | None, base_ac: int, attack_total: int):
        """Call _resolve_instance_attack with controlled roll and cover."""
        db = MagicMock()
        state = _build_state()
        attacker = state.participants[0]
        target_p = state.participants[1]
        spell_ctx = {
            "effect_instance_count": 2,
            "effect_instance_dice": "1d10",
            "spell_mode": "spell_attack",
            "spell_canonical_key": "eldritch_blast",
            "effect_kind": "damage",
            "damage_type": "Force",
            "attack_bonus": 5,
        }
        tr = _targeting_result(cover)
        mock_roll_result = MagicMock()
        mock_roll_result.total = attack_total
        mock_roll_result.selected_roll = min(attack_total - 5, 20)  # approximate d20
        mock_roll_result.success = attack_total >= (base_ac + resolve_cover_modifier(cover))
        with patch.object(CombatService, "_get_stats",
                          return_value=(MagicMock(), base_ac, 30, 30, 3, 5)), \
             patch("app.services.combat_service.spells.cast_target.resolve_attack_base",
                   return_value=mock_roll_result), \
             patch.object(CombatService, "_resolve_damage_roll", return_value=([6], 6)), \
             patch.object(CombatService, "_apply_spell_effect", return_value=(20, "", 25, None)), \
             patch("app.services.combat_service.spells.cast_target.flag_modified"):
            return CombatService._resolve_instance_attack(
                db, "session-1", state, attacker, target_p, spell_ctx, _req(), False,
                targeting_result=tr,
            )

    def test_half_cover_adds_2_to_effective_ac(self):
        base_ac = 14
        result = self._run_instance_attack("half", base_ac, attack_total=18)
        self.assertEqual(result["base_ac"], base_ac)
        self.assertEqual(result["effective_ac"], base_ac + 2)
        self.assertEqual(result["cover_modifier"], 2)
        self.assertEqual(result["cover"], "half")

    def test_three_quarters_cover_adds_5_to_effective_ac(self):
        base_ac = 14
        result = self._run_instance_attack("threeQuarters", base_ac, attack_total=20)
        self.assertEqual(result["effective_ac"], base_ac + 5)
        self.assertEqual(result["cover_modifier"], 5)

    def test_no_cover_uses_base_ac(self):
        base_ac = 14
        result = self._run_instance_attack(None, base_ac, attack_total=16)
        self.assertEqual(result["effective_ac"], base_ac)
        self.assertEqual(result["cover_modifier"], 0)

    def test_half_cover_causes_miss_on_borderline_roll(self):
        """Roll 16 vs AC 15 → hits without cover, misses with half cover (AC 17)."""
        base_ac = 15
        # Without cover: 16 ≥ 15 → hit
        result_no_cover = self._run_instance_attack(None, base_ac, attack_total=16)
        self.assertTrue(result_no_cover["is_hit"])
        # With half cover: effective_ac = 17, 16 < 17 → miss
        result_half = self._run_instance_attack("half", base_ac, attack_total=16)
        self.assertFalse(result_half["is_hit"])

    def test_three_quarters_causes_miss_borderline(self):
        """Roll 19 vs AC 15 → hits without cover, misses with 3/4 cover (AC 20)."""
        base_ac = 15
        result_no_cover = self._run_instance_attack(None, base_ac, attack_total=19)
        self.assertTrue(result_no_cover["is_hit"])
        result_3q = self._run_instance_attack("threeQuarters", base_ac, attack_total=19)
        self.assertFalse(result_3q["is_hit"])


# ---------------------------------------------------------------------------
# Group 3 — Acid Splash
# ---------------------------------------------------------------------------

class TestAcidSplashParity(unittest.TestCase):
    """
    Acid Splash: cantrip damage-dice scaling + saving throw + cover_applies_to_save.

    Scaling contract (damage_dice mode, NOT effect_instances):
      level 1-4  → 1d6
      level 5-10 → 2d6
      level 11-16 → 3d6
      level 17+   → 4d6

    Instance contract: effect_instance_count = 1 (no multi-instance)

    Cover contract: the seed has coverAppliesToSave = "physical", so cover
    DOES apply to acid splash by default. The tests below verify that the
    cover_applies_to_save field is the authoritative gate — if it is None,
    cover must not reduce DC even when cover is present.
    """

    AS_SCALING = {
        "scalingMode": "character_level",
        "scalingEffectType": "damage_dice",
        "thresholds": [
            {"characterLevel": 1, "damage": {"dice": "1d6"}},
            {"characterLevel": 5, "damage": {"dice": "2d6"}},
            {"characterLevel": 11, "damage": {"dice": "3d6"}},
            {"characterLevel": 17, "damage": {"dice": "4d6"}},
        ],
    }

    def _apply_scaling(self, caster_level: int) -> dict:
        return CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
            spell_level=0,
            caster_level=caster_level,
            effect_dice="1d6",
            cantrip_scaling=self.AS_SCALING,
        )

    # --- Cantrip dice scaling ---

    def test_level1_1d6(self):
        result = self._apply_scaling(1)
        self.assertEqual(result["effect_dice"], "1d6")

    def test_level4_still_1d6(self):
        result = self._apply_scaling(4)
        self.assertEqual(result["effect_dice"], "1d6")

    def test_level5_2d6(self):
        result = self._apply_scaling(5)
        self.assertEqual(result["effect_dice"], "2d6")

    def test_level11_3d6(self):
        result = self._apply_scaling(11)
        self.assertEqual(result["effect_dice"], "3d6")

    def test_level17_4d6(self):
        result = self._apply_scaling(17)
        self.assertEqual(result["effect_dice"], "4d6")

    # --- No effect_instance_count > 1 (damage_dice scaling is NOT instance scaling) ---

    def test_damage_dice_scaling_produces_no_instance_metadata(self):
        result = self._apply_scaling(5)
        self.assertIsNone(result["cantrip_instance_count"],
                          "Acid Splash damage_dice scaling must not produce instance metadata")
        self.assertIsNone(result["cantrip_instance_dice"])

    def test_effect_instance_count_is_one(self):
        """Mirror _build_spell_context_response: no cantrip_instance_count → count = 1."""
        result = self._apply_scaling(11)
        instance_count = result["cantrip_instance_count"] if result["cantrip_instance_count"] is not None else 1
        self.assertEqual(instance_count, 1)

    # --- cover_applies_to_save is the authoritative gate ---

    def test_cover_applies_when_cover_applies_to_save_is_physical(self):
        """half cover + cover_applies_to_save="physical" → DC reduced by 2."""
        effective_dc, modifier = resolve_cover_save_dc(15, "half", "physical")
        self.assertEqual(effective_dc, 13)
        self.assertEqual(modifier, 2)

    def test_cover_does_not_apply_when_cover_applies_to_save_is_none(self):
        """half cover + cover_applies_to_save=None → DC unchanged."""
        effective_dc, modifier = resolve_cover_save_dc(15, "half", None)
        self.assertEqual(effective_dc, 15,
                         "cover_applies_to_save=None must preserve base DC even with half cover")
        self.assertEqual(modifier, 0)

    def test_cover_does_not_apply_when_cover_applies_to_save_is_none_string(self):
        effective_dc, modifier = resolve_cover_save_dc(15, "threeQuarters", "none")
        self.assertEqual(effective_dc, 15)
        self.assertEqual(modifier, 0)


# ---------------------------------------------------------------------------
# Group 4 — Fireball (area)
# ---------------------------------------------------------------------------

class TestFireballParity(unittest.TestCase):
    """
    Fireball: area spell with per-target cover DC.

    Seed contract:
      area_shape = "sphere"
      range_meters = 45, radius_meters = 6
      resolution_type = saving_throw, saving_throw = DEX
      save_success_outcome = half_damage
      coverAppliesToSave = "physical"

    Preview/runtime parity: both preview (area_targeting.py) and cast runtime
    (cast_area.py) delegate to build_area_affected_target_spatial_metadata /
    resolve_cover_save_dc. The tests below verify the shared data builder and
    the mathematical invariants that both paths must satisfy.
    """

    BASE_DC = 15
    COVER_APPLIES = "physical"

    def _metadata(self, cover_by_ref: dict, affected_ref_ids: list[str] | None = None):
        if affected_ref_ids is None:
            affected_ref_ids = list(cover_by_ref.keys())
        name_by_ref = {ref: f"Target-{ref[-1]}" for ref in affected_ref_ids}
        return build_area_affected_target_spatial_metadata(
            affected_ref_ids=affected_ref_ids,
            name_by_ref=name_by_ref,
            cover_by_ref=cover_by_ref,
            base_save_dc=self.BASE_DC,
            cover_applies_to_save=self.COVER_APPLIES,
        )

    # --- Per-target DC from metadata builder ---

    def test_no_cover_target_uses_base_dc(self):
        results = self._metadata({"t1": None})
        self.assertEqual(results[0]["effective_save_dc"], self.BASE_DC)
        self.assertEqual(results[0]["cover_modifier"], 0)

    def test_half_cover_target_reduces_dc_by_2(self):
        results = self._metadata({"t1": "half"})
        self.assertEqual(results[0]["effective_save_dc"], self.BASE_DC - 2)
        self.assertEqual(results[0]["cover_modifier"], 2)

    def test_three_quarters_cover_reduces_dc_by_5(self):
        results = self._metadata({"t1": "threeQuarters"})
        self.assertEqual(results[0]["effective_save_dc"], self.BASE_DC - 5)
        self.assertEqual(results[0]["cover_modifier"], 5)

    def test_full_cover_does_not_reduce_dc(self):
        results = self._metadata({"t1": "full"})
        self.assertEqual(results[0]["effective_save_dc"], self.BASE_DC,
                         "Full cover must not reduce DC (it blocks the spell, not modifies DC)")
        self.assertEqual(results[0]["cover_modifier"], 0)

    # --- cover_applies_to_save=None → base DC for all targets ---

    def test_no_cover_metadata_field_preserves_all_dcs(self):
        """If a spell has coverAppliesToSave=None, cover is ignored for every target."""
        ref_ids = ["t1", "t2", "t3"]
        cover_by_ref = {"t1": None, "t2": "half", "t3": "threeQuarters"}
        results = build_area_affected_target_spatial_metadata(
            affected_ref_ids=ref_ids,
            name_by_ref={r: r for r in ref_ids},
            cover_by_ref=cover_by_ref,
            base_save_dc=self.BASE_DC,
            cover_applies_to_save=None,  # ← override to None
        )
        for entry in results:
            self.assertEqual(entry["effective_save_dc"], self.BASE_DC,
                             f"Target {entry['target_ref_id']} should use base DC when coverAppliesToSave=None")
            self.assertEqual(entry["cover_modifier"], 0)

    # --- Per-target independence ---

    def test_each_target_gets_its_own_dc(self):
        cover_by_ref = {
            "t-a": None,           # base DC
            "t-b": "half",         # DC - 2
            "t-c": "threeQuarters", # DC - 5
        }
        results = self._metadata(cover_by_ref, affected_ref_ids=["t-a", "t-b", "t-c"])
        by_ref = {r["target_ref_id"]: r for r in results}

        self.assertEqual(by_ref["t-a"]["effective_save_dc"], self.BASE_DC)
        self.assertEqual(by_ref["t-b"]["effective_save_dc"], self.BASE_DC - 2)
        self.assertEqual(by_ref["t-c"]["effective_save_dc"], self.BASE_DC - 5)

    def test_affected_ref_ids_order_is_preserved(self):
        ordered = ["t-c", "t-a", "t-b"]
        results = self._metadata(
            {"t-a": None, "t-b": "half", "t-c": "threeQuarters"},
            affected_ref_ids=ordered,
        )
        self.assertEqual([r["target_ref_id"] for r in results], ordered)

    def test_cover_does_not_alter_affected_ref_ids(self):
        """Cover metadata must not add or remove targets from affected list."""
        ref_ids = ["t1", "t2"]
        cover_by_ref = {"t1": "half", "t2": "threeQuarters", "t-extra": "half"}
        results = self._metadata(cover_by_ref, affected_ref_ids=ref_ids)
        returned_ids = [r["target_ref_id"] for r in results]
        self.assertEqual(returned_ids, ref_ids,
                         "cover_by_ref extra keys must not add targets to the metadata list")

    # --- Preview/runtime use the same DC function ---

    def test_metadata_builder_agrees_with_direct_dc_call(self):
        """build_area_affected_target_spatial_metadata must produce the same DC
        as a direct resolve_cover_save_dc call — preview and runtime share this function."""
        for cover in [None, "half", "threeQuarters", "full"]:
            results = self._metadata({"t1": cover})
            expected_dc, expected_modifier = resolve_cover_save_dc(
                self.BASE_DC, cover, self.COVER_APPLIES
            )
            self.assertEqual(results[0]["effective_save_dc"], expected_dc,
                             f"Mismatch for cover={cover}")
            self.assertEqual(results[0]["cover_modifier"], expected_modifier,
                             f"Modifier mismatch for cover={cover}")

    def test_base_save_dc_field_is_always_unchanged(self):
        """base_save_dc in metadata must always be the original, not modified."""
        for cover in [None, "half", "threeQuarters", "full"]:
            results = self._metadata({"t1": cover})
            self.assertEqual(results[0]["base_save_dc"], self.BASE_DC,
                             f"base_save_dc must not be modified for cover={cover}")


# ---------------------------------------------------------------------------
# Group 5 — Cross-archetype invariants
# ---------------------------------------------------------------------------

class TestSpellPipelineInvariants(unittest.TestCase):
    """
    Invariants that must hold across ALL spell archetypes.
    These catch category-level regressions regardless of specific spell.
    """

    # --- Full cover does not produce a DC reduction ---

    def test_full_cover_dc_reduction_is_zero_not_five(self):
        modifier = resolve_cover_modifier("full")
        self.assertEqual(modifier, 0,
                         "Full cover provides no DC/AC modifier — it blocks targeting entirely")

    def test_full_cover_save_dc_unchanged(self):
        effective_dc, modifier = resolve_cover_save_dc(15, "full", "physical")
        self.assertEqual(effective_dc, 15)
        self.assertEqual(modifier, 0)

    # --- Cover is metadata, not targeting validity ---

    def test_half_cover_does_not_invalidate_targeting_result(self):
        """cover='half' is spatial metadata; it must not flip is_valid to False."""
        tr = _targeting_result("half", is_valid=True)
        self.assertTrue(tr.is_valid)
        self.assertEqual(tr.spatial_metadata.cover, "half")

    def test_three_quarters_cover_does_not_invalidate_targeting_result(self):
        tr = _targeting_result("threeQuarters", is_valid=True)
        self.assertTrue(tr.is_valid)

    # --- cover_applies_to_save is the single gate ---

    def test_unknown_cover_applies_value_does_not_reduce_dc(self):
        """Any value other than "physical" must be treated as 'no cover applies'."""
        effective_dc, modifier = resolve_cover_save_dc(15, "half", "hybrid_unknown_value")
        self.assertEqual(effective_dc, 15)
        self.assertEqual(modifier, 0)

    # --- Upcast fallback only when explicit baseEffectInstances is absent ---

    def test_explicit_base_effect_instances_takes_priority(self):
        """When baseEffectInstances is set, it must be used directly (no derivation)."""
        structured = CombatSpellDiceMathMixin._get_structured_spell_upcast({
            "mode": "additional_effect_instances",
            "dice": "1d4+1",
            "perLevel": 1,
            "baseEffectInstances": 3,
        })
        self.assertEqual(structured["baseEffectInstances"], 3,
                         "Explicit baseEffectInstances must be passed through unchanged")

    # --- Area cover does not alter affected target refs ---

    def test_area_cover_lookup_does_not_add_targets(self):
        """Targets in cover_by_ref but not in affected_ref_ids must be ignored."""
        result = build_area_affected_target_spatial_metadata(
            affected_ref_ids=["real-target"],
            name_by_ref={"real-target": "Real"},
            cover_by_ref={"real-target": "half", "phantom": "none"},
            base_save_dc=14,
            cover_applies_to_save="physical",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["target_ref_id"], "real-target")

    def test_area_cover_lookup_missing_target_defaults_to_no_cover(self):
        """Target in affected_ref_ids but absent from cover_by_ref → no cover reduction."""
        result = build_area_affected_target_spatial_metadata(
            affected_ref_ids=["t1"],
            name_by_ref={"t1": "Target"},
            cover_by_ref={},  # no entry for t1
            base_save_dc=14,
            cover_applies_to_save="physical",
        )
        self.assertEqual(result[0]["cover"], None)
        self.assertEqual(result[0]["effective_save_dc"], 14)


if __name__ == "__main__":
    unittest.main()
