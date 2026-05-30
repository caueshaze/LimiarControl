from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.services.combat import CombatService
from app.services.combat_service.spells.spell_context_resolve import (
    SpellContextResolveMixin,
)
from app.services.out_of_combat_cast import (
    OOC_FACTORY_EFFECT_SPELLS,
    OOC_NARRATIVE_UTILITY_SPELLS,
    OOC_REMOVAL_UTILITY_SPELLS,
    OOC_SPECIAL_INPUT_SPELLS,
    _OOC_PERSISTED_FACTORY_REGISTRY,
)
from app.services.spell_keys import normalize_spell_key
from app.services.spell_targeting_semantics import explicit_spell_targeting_overrides


def assert_subset(actual: set[str], expected: set[str], label: str) -> None:
    missing = sorted(actual - expected)
    assert not missing, f"{label} keys missing from seed: {missing}"


def assert_normalized(keys: set[str], label: str) -> None:
    bad = {key: normalize_spell_key(key) for key in sorted(keys) if key != normalize_spell_key(key)}
    assert not bad, f"{label} has non-normalized keys: {bad}"


class SpellRegistryConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_path = Path(__file__).resolve().parents[3] / "Base" / "base_spells.seed.json"
        payload = json.loads(seed_path.read_text(encoding="utf-8"))
        cls.seed_spell_keys = {
            normalize_spell_key(entry.get("canonicalKey"))
            for entry in payload.get("spells", [])
            if isinstance(entry, dict)
        }
        cls.seed_spell_keys.discard("")

    def test_spell_automation_registry_keys_exist_in_seed(self):
        keys = set(CombatService._SPELL_AUTOMATION_REGISTRY.keys())
        assert_subset(keys, self.seed_spell_keys, "automation_registry")

    def test_targeting_semantics_keys_exist_in_seed(self):
        keys = set(explicit_spell_targeting_overrides().keys())
        assert_subset(keys, self.seed_spell_keys, "targeting_overrides")

    def test_utility_context_keys_exist_in_seed(self):
        utility_keys = set(SpellContextResolveMixin.UTILITY_SPELL_CONTEXT_META.keys())
        narrative_keys = set(SpellContextResolveMixin._NARRATIVE_UTILITY_META_BY_SPELL.keys())
        assert_subset(utility_keys, self.seed_spell_keys, "utility_context_registry")
        assert_subset(narrative_keys, self.seed_spell_keys, "narrative_context_registry")

    def test_ooc_category_keys_exist_in_seed(self):
        keys = (
            OOC_NARRATIVE_UTILITY_SPELLS
            | OOC_FACTORY_EFFECT_SPELLS
            | OOC_REMOVAL_UTILITY_SPELLS
            | OOC_SPECIAL_INPUT_SPELLS
        )
        assert_subset(keys, self.seed_spell_keys, "ooc_categories")

    def test_ooc_factory_category_matches_registry(self):
        self.assertEqual(OOC_FACTORY_EFFECT_SPELLS, set(_OOC_PERSISTED_FACTORY_REGISTRY))

    def test_ooc_factory_registry_keys_exist_in_seed(self):
        keys = set(_OOC_PERSISTED_FACTORY_REGISTRY.keys())
        assert_subset(keys, self.seed_spell_keys, "ooc_factory_registry")

    def test_ooc_factory_spells_exist_in_utility_context_registry(self):
        utility_keys = set(SpellContextResolveMixin.UTILITY_SPELL_CONTEXT_META.keys())
        assert_subset(
            set(OOC_FACTORY_EFFECT_SPELLS),
            utility_keys,
            "ooc_factory_spells_vs_utility_context",
        )

    def test_ooc_categories_are_disjoint(self):
        categories = {
            "narrative": OOC_NARRATIVE_UTILITY_SPELLS,
            "factory": OOC_FACTORY_EFFECT_SPELLS,
            "removal": OOC_REMOVAL_UTILITY_SPELLS,
            "special_input": OOC_SPECIAL_INPUT_SPELLS,
        }
        overlaps: dict[str, list[str]] = {}
        names = list(categories.keys())
        for idx, left_name in enumerate(names):
            for right_name in names[idx + 1 :]:
                overlap = sorted(categories[left_name] & categories[right_name])
                if overlap:
                    overlaps[f"{left_name}∩{right_name}"] = overlap
        self.assertEqual(overlaps, {}, f"OOC categories overlap: {overlaps}")

    def test_registry_keys_are_normalized(self):
        assert_normalized(set(CombatService._SPELL_AUTOMATION_REGISTRY.keys()), "automation_registry")
        assert_normalized(set(explicit_spell_targeting_overrides().keys()), "targeting_overrides")
        assert_normalized(set(SpellContextResolveMixin.UTILITY_SPELL_CONTEXT_META.keys()), "utility_context_registry")
        assert_normalized(
            set(SpellContextResolveMixin._NARRATIVE_UTILITY_META_BY_SPELL.keys()),
            "narrative_context_registry",
        )
        assert_normalized(OOC_NARRATIVE_UTILITY_SPELLS, "ooc_narrative_set")
        assert_normalized(OOC_FACTORY_EFFECT_SPELLS, "ooc_factory_set")
        assert_normalized(OOC_REMOVAL_UTILITY_SPELLS, "ooc_removal_set")
        assert_normalized(OOC_SPECIAL_INPUT_SPELLS, "ooc_special_input_set")
        assert_normalized(set(_OOC_PERSISTED_FACTORY_REGISTRY.keys()), "ooc_factory_registry")


if __name__ == "__main__":
    unittest.main()
