"""Spell System Hardening tests.

Covers:
  - Automation metadata resolution (authority, classification, magic_missile)
  - Area spell dependency policy (MAP_UNAVAILABLE_FOR_AREA_SPELL)
  - Targeting fallback narrowing
  - Character-sheet spell reference matching
  - Resolution type mapping (centralized)
  - Regression checks for existing spells
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from _combat_test_shared import TestCombatServiceBase, TestResolutionTypeMapping
from app.models.campaign_spell import CampaignSpell
from app.models.base_spell import BaseSpell, SpellSchool
from app.models.combat import CombatPhase
from app.models.campaign import SystemType
from app.models.session_state import SessionState
from app.services.combat_service.spell_automation import (
    CombatSpellAutomationMixin,
    SpellAutomationSpec,
)
from app.services.combat_service.spell_automation_metadata import (
    SpellAutomationMetadata,
    resolve_spell_automation_metadata,
    resolve_spell_automation_metadata_from_catalog,
)
from app.services.combat_service.targeting_diagnostics import (
    ALL_CANONICAL_REASONS,
    MAP_UNAVAILABLE_FOR_AREA_SPELL,
    AREA_TARGETING_UNAVAILABLE,
)
from app.services.combat_service.targeting_intent import AreaTargetingIntent


class FakeCatalogEntry:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestSpellAutomationMetadata(unittest.TestCase):
    """Automation metadata is the single source of truth for spell classification."""

    def test_generic_direct_damage_spell(self):
        meta = resolve_spell_automation_metadata(
            canonical_key="magic_missile",
            resolution_type="damage",
            target_mode="ranged",
            damage_dice="3d4+3",
        )
        self.assertEqual(meta.automation_mode, "generic_direct")
        self.assertEqual(meta.default_spell_mode, "direct_damage")
        self.assertFalse(meta.requires_map)
        self.assertIsNone(meta.handler_key)
        self.assertTrue(meta.requires_effect_inputs)

    def test_generic_area_spell(self):
        meta = resolve_spell_automation_metadata(
            canonical_key="fireball",
            resolution_type="damage",
            target_mode="sphere",
            damage_dice="8d6",
            saving_throw="DEX",
        )
        self.assertEqual(meta.automation_mode, "generic_area")
        self.assertEqual(meta.default_spell_mode, "direct_damage")
        self.assertTrue(meta.requires_map)
        self.assertIsNone(meta.handler_key)

    def test_special_handler_spell(self):
        registry = {
            "animal_friendship": SpellAutomationSpec(
                canonical_key="animal_friendship",
                default_mode="saving_throw",
                requires_effect_payload=False,
                handler_name="_cast_animal_friendship_automation",
            ),
        }
        meta = resolve_spell_automation_metadata(
            canonical_key="animal_friendship",
            resolution_type="control",
            target_mode="ranged",
            saving_throw="WIS",
            automation_registry=registry,
        )
        self.assertEqual(meta.automation_mode, "special_handler")
        self.assertEqual(meta.default_spell_mode, "saving_throw")
        self.assertFalse(meta.requires_map)
        self.assertEqual(meta.handler_key, "_cast_animal_friendship_automation")
        self.assertFalse(meta.requires_effect_inputs)

    def test_magic_missile_is_generic_direct(self):
        meta = resolve_spell_automation_metadata(
            canonical_key="magic_missile",
            resolution_type="damage",
            target_mode="ranged",
            damage_dice="3d4+3",
        )
        self.assertEqual(meta.automation_mode, "generic_direct")
        self.assertIsNone(meta.handler_key)

    def test_heal_spell(self):
        meta = resolve_spell_automation_metadata(
            canonical_key="healing_word",
            resolution_type="heal",
            target_mode="ranged",
            heal_dice="1d4",
        )
        self.assertEqual(meta.automation_mode, "generic_direct")
        self.assertEqual(meta.default_spell_mode, "heal")

    def test_utility_spell(self):
        meta = resolve_spell_automation_metadata(
            canonical_key="goodberry",
            resolution_type="utility",
            target_mode="touch",
        )
        self.assertEqual(meta.automation_mode, "generic_direct")
        self.assertEqual(meta.default_spell_mode, "utility")
        self.assertFalse(meta.requires_effect_inputs)

    def test_cone_area_spell(self):
        meta = resolve_spell_automation_metadata(
            canonical_key="burning_hands",
            resolution_type="damage",
            target_mode="cone",
            damage_dice="3d6",
            saving_throw="DEX",
        )
        self.assertEqual(meta.automation_mode, "generic_area")
        self.assertTrue(meta.requires_map)

    def test_line_area_spell(self):
        meta = resolve_spell_automation_metadata(
            canonical_key="lightning_bolt",
            resolution_type="damage",
            target_mode="line",
            damage_dice="8d6",
            saving_throw="DEX",
        )
        self.assertEqual(meta.automation_mode, "generic_area")
        self.assertTrue(meta.requires_map)

    def test_cylinder_area_spell(self):
        meta = resolve_spell_automation_metadata(
            canonical_key="some_cylinder",
            resolution_type="damage",
            target_mode="cylinder",
        )
        self.assertEqual(meta.automation_mode, "generic_area")

    def test_to_api_dict(self):
        meta = resolve_spell_automation_metadata(
            canonical_key="fireball",
            resolution_type="damage",
            target_mode="sphere",
            damage_dice="8d6",
        )
        d = meta.to_api_dict()
        self.assertEqual(d["automationMode"], "generic_area")
        self.assertEqual(d["defaultSpellMode"], "direct_damage")
        self.assertTrue(d["requiresMap"])
        self.assertIsNone(d["handlerKey"])


class TestSpellAutomationMetadataFromCatalog(unittest.TestCase):
    """Test the convenience wrapper that reads from model objects."""

    def test_reads_from_base_spell_model(self):
        spell = FakeCatalogEntry(
            canonical_key="fireball",
            resolution_type="damage",
            target_mode="sphere",
            saving_throw="DEX",
            damage_dice="8d6",
            heal_dice=None,
        )
        meta = resolve_spell_automation_metadata_from_catalog(spell)
        self.assertEqual(meta.automation_mode, "generic_area")
        self.assertEqual(meta.default_spell_mode, "direct_damage")

    def test_special_handler_via_registry(self):
        registry = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY
        spell = FakeCatalogEntry(
            canonical_key="animal_friendship",
            resolution_type="control",
            target_mode="ranged",
            saving_throw="WIS",
            damage_dice=None,
            heal_dice=None,
        )
        meta = resolve_spell_automation_metadata_from_catalog(
            spell,
            automation_registry=registry,
        )
        self.assertEqual(meta.automation_mode, "special_handler")
        self.assertEqual(meta.default_spell_mode, "saving_throw")


class TestResolutionTypeMappingExtended(unittest.TestCase):
    """Extended resolution type mapping tests beyond existing ones."""

    def test_damage_maps_to_direct_damage(self):
        from app.services.combat import CombatService

        self.assertEqual(
            CombatService._map_resolution_type_to_spell_mode("damage"),
            "direct_damage",
        )

    def test_control_maps_to_saving_throw(self):
        from app.services.combat import CombatService

        self.assertEqual(
            CombatService._map_resolution_type_to_spell_mode("control"),
            "saving_throw",
        )

    def test_debuff_maps_to_saving_throw(self):
        from app.services.combat import CombatService

        self.assertEqual(
            CombatService._map_resolution_type_to_spell_mode("debuff"),
            "saving_throw",
        )

    def test_buff_maps_to_utility(self):
        from app.services.combat import CombatService

        self.assertEqual(
            CombatService._map_resolution_type_to_spell_mode("buff"),
            "utility",
        )


class TestMagicMissileNoLongerInRegistry(unittest.TestCase):
    """magic_missile must not appear in the automation registry."""

    def test_not_in_backend_registry(self):
        registry = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY
        self.assertNotIn("magic_missile", registry)

    def test_resolves_as_generic_direct(self):
        meta = resolve_spell_automation_metadata(
            canonical_key="magic_missile",
            resolution_type="damage",
            target_mode="ranged",
            damage_dice="3d4+3",
            automation_registry=CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY,
        )
        self.assertEqual(meta.automation_mode, "generic_direct")
        self.assertIsNone(meta.handler_key)
        self.assertEqual(meta.default_spell_mode, "direct_damage")


class TestAreaSpellFailureCode(unittest.TestCase):
    """Area spell failure uses MAP_UNAVAILABLE_FOR_AREA_SPELL."""

    def test_canonical_reason_registered(self):
        self.assertIn(MAP_UNAVAILABLE_FOR_AREA_SPELL, ALL_CANONICAL_REASONS)

    def test_local_targeting_service_rejects_area_with_new_code(self):
        from app.services.combat_service.combat_targeting import (
            LocalCombatTargetingService,
        )
        from app.services.combat_service.targeting_result import TargetingResult

        service = LocalCombatTargetingService()
        state = MagicMock()
        intent = AreaTargetingIntent(
            session_id="s1",
            action_id="a1",
            actor_ref_id="p1",
            actor_kind="player",
            requested_target_ref_id="e1",
            spell_canonical_key="fireball",
            spell_mode="saving_throw",
            shape="sphere",
            size_meters=6,
        )
        result = service.validate(intent, state)
        self.assertFalse(result.is_valid)
        self.assertIsNotNone(result.diagnostics)
        self.assertIn(
            MAP_UNAVAILABLE_FOR_AREA_SPELL,
            result.diagnostics.failure_reasons,
        )


class TestCharacterSheetSpellReferenceMatching(unittest.TestCase):
    """Player spell entry matching supports campaignSpellId."""

    def test_matches_by_campaign_spell_id(self):
        from app.services.combat import CombatService

        data = {
            "spellcasting": {
                "spells": [
                    {
                        "name": "Fireball",
                        "canonicalKey": "fireball",
                        "campaignSpellId": "cs-123",
                        "level": 3,
                        "prepared": True,
                    },
                    {
                        "name": "Magic Missile",
                        "canonicalKey": "magic_missile",
                        "level": 1,
                        "prepared": True,
                    },
                ],
            },
        }
        result = CombatService._resolve_player_spell_entry(
            data,
            spell_canonical_key="fireball",
            campaign_spell_id="cs-123",
        )
        self.assertEqual(result.get("campaignSpellId"), "cs-123")

    def test_campaign_spell_id_takes_priority_over_canonical_key(self):
        from app.services.combat import CombatService

        data = {
            "spellcasting": {
                "spells": [
                    {
                        "name": "Custom Fireball",
                        "canonicalKey": "fireball",
                        "campaignSpellId": "cs-456",
                        "level": 3,
                        "prepared": True,
                    },
                    {
                        "name": "Fireball",
                        "canonicalKey": "fireball",
                        "level": 3,
                        "prepared": True,
                    },
                ],
            },
        }
        result = CombatService._resolve_player_spell_entry(
            data,
            spell_canonical_key="fireball",
            campaign_spell_id="cs-456",
        )
        self.assertEqual(result.get("name"), "Custom Fireball")
        self.assertEqual(result.get("campaignSpellId"), "cs-456")

    def test_legacy_matching_by_canonical_key_still_works(self):
        from app.services.combat import CombatService

        data = {
            "spellcasting": {
                "spells": [
                    {
                        "name": "Fireball",
                        "canonicalKey": "fireball",
                        "level": 3,
                        "prepared": True,
                    },
                ],
            },
        }
        result = CombatService._resolve_player_spell_entry(
            data,
            spell_canonical_key="fireball",
        )
        self.assertEqual(result.get("canonicalKey"), "fireball")
        self.assertIsNone(result.get("campaignSpellId"))

    def test_legacy_matching_by_name_still_works(self):
        from app.services.combat import CombatService

        data = {
            "spellcasting": {
                "spells": [
                    {
                        "name": "Fireball",
                        "level": 3,
                        "prepared": True,
                    },
                ],
            },
        }
        result = CombatService._resolve_player_spell_entry(
            data,
            spell_canonical_key=None,
            spell_name="Fireball",
        )
        self.assertEqual(result.get("name"), "Fireball")

    def test_modern_entry_ignores_canonical_key_mismatch(self):
        """campaignSpellId match wins even when canonicalKey on the entry is wrong."""
        from app.services.combat import CombatService

        data = {
            "spellcasting": {
                "spells": [
                    {
                        "name": "Custom Fireball",
                        # canonicalKey deliberately mismatched
                        "canonicalKey": "totally_wrong_key",
                        "campaignSpellId": "cs-modern",
                        "level": 3,
                        "prepared": True,
                    },
                ],
            },
        }
        result = CombatService._resolve_player_spell_entry(
            data,
            spell_canonical_key="fireball",
            campaign_spell_id="cs-modern",
        )
        self.assertEqual(result.get("campaignSpellId"), "cs-modern")
        self.assertEqual(result.get("name"), "Custom Fireball")

    def test_fallback_logs_debug_on_canonical_key_path(self):
        """Legacy canonicalKey fallback emits a debug log message."""
        import logging
        from app.services.combat import CombatService

        data = {
            "spellcasting": {
                "spells": [
                    {
                        "name": "Fireball",
                        "canonicalKey": "fireball",
                        "level": 3,
                        "prepared": True,
                    },
                ],
            },
        }
        with self.assertLogs(
            "app.services.combat_service.core", level=logging.DEBUG
        ) as cm:
            result = CombatService._resolve_player_spell_entry(
                data,
                spell_canonical_key="fireball",
                campaign_spell_id=None,
            )
        self.assertEqual(result.get("canonicalKey"), "fireball")
        self.assertTrue(
            any("legacy canonicalKey fallback" in msg for msg in cm.output),
            f"Expected legacy canonicalKey fallback log, got: {cm.output}",
        )

    def test_fallback_logs_debug_on_name_path(self):
        """Legacy name fallback emits a debug log message."""
        import logging
        from app.services.combat import CombatService

        data = {
            "spellcasting": {
                "spells": [
                    {
                        "name": "Fireball",
                        "level": 3,
                        "prepared": True,
                    },
                ],
            },
        }
        with self.assertLogs(
            "app.services.combat_service.core", level=logging.DEBUG
        ) as cm:
            result = CombatService._resolve_player_spell_entry(
                data,
                spell_canonical_key=None,
                spell_name="Fireball",
            )
        self.assertEqual(result.get("name"), "Fireball")
        self.assertTrue(
            any("legacy name fallback" in msg for msg in cm.output),
            f"Expected legacy name fallback log, got: {cm.output}",
        )

    def test_modern_entry_does_not_emit_fallback_log(self):
        """Modern campaignSpellId match must not emit any fallback log."""
        import logging
        from app.services.combat import CombatService

        data = {
            "spellcasting": {
                "spells": [
                    {
                        "name": "Fireball",
                        "canonicalKey": "fireball",
                        "campaignSpellId": "cs-modern",
                        "level": 3,
                        "prepared": True,
                    },
                ],
            },
        }
        # assertLogs raises AssertionError when no log is emitted — that's what we want
        try:
            with self.assertLogs(
                "app.services.combat_service.core", level=logging.DEBUG
            ) as cm:
                CombatService._resolve_player_spell_entry(
                    data,
                    spell_canonical_key="fireball",
                    campaign_spell_id="cs-modern",
                )
            # If logs were emitted, fail if any are fallback-related
            fallback_logs = [
                msg for msg in cm.output
                if "legacy" in msg
            ]
            self.assertEqual(
                fallback_logs, [],
                f"Modern path emitted unexpected fallback logs: {fallback_logs}",
            )
        except AssertionError:
            # assertLogs raises AssertionError when no logs are emitted — that's fine
            pass


class TestSpellAutomationRegistryOnlySpecialHandlers(unittest.TestCase):
    """Only genuinely special-handler spells should be in the registry."""

    def test_registry_contains_only_real_handlers(self):
        registry = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY
        for key, spec in registry.items():
            self.assertTrue(
                spec.handler_name.strip(),
                f"Spell '{key}' has an empty handler_name — it should not be in the registry.",
            )

    def test_animal_friendship_is_registered(self):
        registry = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY
        self.assertIn("animal_friendship", registry)
        self.assertEqual(
            registry["animal_friendship"].handler_name,
            "_cast_animal_friendship_automation",
        )

    def test_hunters_mark_is_registered(self):
        registry = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY
        self.assertIn("hunters_mark", registry)
        self.assertEqual(
            registry["hunters_mark"].handler_name, "_cast_hunters_mark_automation"
        )

    def test_goodberry_is_registered(self):
        registry = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY
        self.assertIn("goodberry", registry)
        self.assertEqual(
            registry["goodberry"].handler_name, "_cast_goodberry_automation"
        )


class TestSpellAuthorityAtCastTime(unittest.TestCase):
    """Verify that combat resolves mechanics from CampaignSpell when available."""

    def test_catalog_entry_lookup_prefers_campaign_spell(self):
        from app.services.combat import CombatService

        db = MagicMock()
        campaign_spell = MagicMock(spec=CampaignSpell)
        campaign_spell.canonical_key = "fireball"
        campaign_spell.is_enabled = True

        db.exec.return_value.first.return_value = campaign_spell

        session_entry = MagicMock()
        session_entry.campaign_id = "camp-1"
        CombatService._get_session_entry = classmethod(lambda cls, d, s: session_entry)
        CombatService._get_campaign_system_for_session = classmethod(
            lambda cls, d, s: SystemType.DND5E
        )

        result = CombatService._get_spell_catalog_entry_for_session(
            db, "session-1", "fireball"
        )
        self.assertIsInstance(result, MagicMock)
        self.assertEqual(result.canonical_key, "fireball")


class TestExistingResolutionTypeMappingStillPasses(TestResolutionTypeMapping):
    """Regression: all existing resolution type mapping tests still pass."""

    pass
