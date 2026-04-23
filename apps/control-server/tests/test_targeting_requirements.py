from __future__ import annotations

import unittest

from app.services.combat_service.targeting_requirements import (
    TargetingRequirements,
    resolve_spell_targeting_requirements,
    resolve_weapon_targeting_requirements,
)


class TargetingRequirementsTests(unittest.TestCase):
    def test_weapon_requirements_use_explicit_family_defaults(self) -> None:
        resolved = resolve_weapon_targeting_requirements()

        self.assertEqual(
            resolved,
            TargetingRequirements(
                requires_target_sight=True,
                requires_target_effect=True,
                requires_point_sight=False,
                requires_point_effect=False,
            ),
        )

    def test_spell_metadata_is_authoritative_when_present(self) -> None:
        resolved = resolve_spell_targeting_requirements(
            {
                "target_type": "ranged",
                "spell_mode": "spell_attack",
                "requires_target_sight": False,
                "requires_target_effect": True,
                "requires_point_sight": True,
                "requires_point_effect": False,
            }
        )

        self.assertFalse(resolved.requires_target_sight)
        self.assertTrue(resolved.requires_target_effect)
        self.assertTrue(resolved.requires_point_sight)
        self.assertFalse(resolved.requires_point_effect)

    def test_spell_metadata_supports_camel_case_sources(self) -> None:
        resolved = resolve_spell_targeting_requirements(
            {
                "targetType": "ranged", "areaShape": "sphere",
                "spellMode": "saving_throw",
                "requiresTargetSight": True,
                "requiresTargetEffect": False,
                "requiresPointSight": False,
                "requiresPointEffect": True,
            }
        )

        self.assertTrue(resolved.requires_target_sight)
        self.assertFalse(resolved.requires_target_effect)
        self.assertFalse(resolved.requires_point_sight)
        self.assertTrue(resolved.requires_point_effect)

    def test_spell_legacy_fallback_is_used_only_when_metadata_is_missing(self) -> None:
        resolved = resolve_spell_targeting_requirements(
            {
                "target_type": "ranged",
                "spell_mode": "spell_attack",
            }
        )

        self.assertTrue(resolved.requires_target_sight)
        self.assertTrue(resolved.requires_target_effect)
        self.assertFalse(resolved.requires_point_sight)
        self.assertTrue(resolved.requires_point_effect)

    def test_partial_spell_metadata_only_falls_back_for_missing_fields(self) -> None:
        resolved = resolve_spell_targeting_requirements(
            {
                "target_type": "ranged",
                "spell_mode": "spell_attack",
                "requires_target_sight": False,
            }
        )

        self.assertFalse(resolved.requires_target_sight)
        self.assertTrue(resolved.requires_target_effect)
        self.assertFalse(resolved.requires_point_sight)
        self.assertTrue(resolved.requires_point_effect)


if __name__ == "__main__":
    unittest.main()
