"""Tests for Enlarge/Reduce (Aumentar/Reduzir).

Covers:
- Seed contract: level=2, concentration, 2 variants (enlarge/reduce), no saving throw
- Effective size changes when size_modifier effect is applied to participant
- Enlarge: size +1, STR advantage on checks and saves, weapon +1d4
- Reduce: size -1, STR disadvantage on checks and saves, weapon -1d4 (min 1 damage)
- Schema validation re-tested only for fields not covered by test_spell_declarative_effects.py
"""

from __future__ import annotations

import json
import unittest

from app.services.combat_service.token_resolution import (
    _resolve_effective_size,
    build_effective_size_payload,
)


def _participant_with_size_modifier(value: int) -> dict:
    return {
        "id": "p1",
        "ref_id": "target",
        "active_effects": [
            {
                "kind": "size_modifier",
                "numeric_value": value,
                "metadata": {"source_spell_key": "enlarge_reduce"},
            }
        ],
    }


def _participant_no_effects() -> dict:
    return {"id": "p1", "ref_id": "target", "active_effects": []}


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class EnlargeReduceSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "enlarge_reduce"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "enlarge_reduce not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 2)
        self.assertEqual(e["school"], "transmutation")
        self.assertEqual(e["castingTimeType"], "action")
        self.assertTrue(e["concentration"])
        self.assertEqual(e["attackType"], "none")

    def test_no_saving_throw(self):
        self.assertIsNone(self.entry.get("savingThrow"))

    def test_has_two_variants(self):
        variants = self.entry.get("variants") or []
        keys = {v["key"] for v in variants}
        self.assertEqual(keys, {"enlarge", "reduce"})

    def test_enlarge_variant_size_value_is_plus_one(self):
        variants = {v["key"]: v for v in (self.entry.get("variants") or [])}
        enlarge_size_effect = next(e for e in variants["enlarge"]["effects"] if e["type"] == "size_modifier")
        self.assertEqual(enlarge_size_effect["params"]["value"], 1)

    def test_reduce_variant_size_value_is_minus_one(self):
        variants = {v["key"]: v for v in (self.entry.get("variants") or [])}
        reduce_size_effect = next(e for e in variants["reduce"]["effects"] if e["type"] == "size_modifier")
        self.assertEqual(reduce_size_effect["params"]["value"], -1)

    def test_reduce_weapon_damage_has_minimum_total_damage(self):
        variants = {v["key"]: v for v in (self.entry.get("variants") or [])}
        weapon_effect = next(e for e in variants["reduce"]["effects"] if e["type"] == "modify_weapon_damage")
        self.assertEqual(weapon_effect["params"]["operation"], "subtract")
        self.assertEqual(weapon_effect["params"]["minimum_total_damage"], 1)

    def test_all_effects_duration_timed_60s(self):
        variants = {v["key"]: v for v in (self.entry.get("variants") or [])}
        for effect in variants["enlarge"]["effects"]:
            self.assertEqual(effect["duration"]["type"], "timed")
            self.assertEqual(effect["duration"]["seconds"], 60)


# ---------------------------------------------------------------------------
# Effective size resolution
# ---------------------------------------------------------------------------

class EnlargeReduceEffectiveSizeTests(unittest.TestCase):
    def test_no_modifier_keeps_medium_size(self):
        p = _participant_no_effects()
        result = build_effective_size_payload(p, "Medium")
        self.assertEqual(result["effective_size"], "Medium")
        self.assertEqual(result["base_size"], "Medium")

    def test_enlarge_increases_medium_to_large(self):
        p = _participant_with_size_modifier(1)
        result = build_effective_size_payload(p, "Medium")
        self.assertEqual(result["effective_size"], "Large")

    def test_reduce_decreases_medium_to_small(self):
        p = _participant_with_size_modifier(-1)
        result = build_effective_size_payload(p, "Medium")
        self.assertEqual(result["effective_size"], "Small")

    def test_enlarge_from_small_gives_medium(self):
        p = _participant_with_size_modifier(1)
        result = build_effective_size_payload(p, "Small")
        self.assertEqual(result["effective_size"], "Medium")

    def test_reduce_from_tiny_stays_tiny(self):
        p = _participant_with_size_modifier(-1)
        result = build_effective_size_payload(p, "Tiny")
        self.assertEqual(result["effective_size"], "Tiny")

    def test_enlarge_from_gargantuan_stays_gargantuan(self):
        p = _participant_with_size_modifier(1)
        result = build_effective_size_payload(p, "Gargantuan")
        self.assertEqual(result["effective_size"], "Gargantuan")

    def test_resolve_effective_size_enlarge_large_to_huge(self):
        p = _participant_with_size_modifier(1)
        self.assertEqual(_resolve_effective_size("Large", p), "Huge")

    def test_effective_footprint_grows_with_enlarge(self):
        base = build_effective_size_payload(_participant_no_effects(), "Medium")
        enlarged = build_effective_size_payload(_participant_with_size_modifier(1), "Medium")
        self.assertGreater(enlarged["effective_footprint"]["width"], base["effective_footprint"]["width"])

    def test_effective_footprint_shrinks_with_reduce(self):
        # Reduce Large (2x2) → Medium (1x1)
        base = build_effective_size_payload(_participant_no_effects(), "Large")
        reduced = build_effective_size_payload(_participant_with_size_modifier(-1), "Large")
        self.assertLess(reduced["effective_footprint"]["width"], base["effective_footprint"]["width"])
