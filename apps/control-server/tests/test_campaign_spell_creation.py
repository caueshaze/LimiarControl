from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.routes.campaign_spells import create_spell
from app.models.base_spell import SpellSchool, SpellSource
from app.models.campaign import SystemType
from app.schemas.base_spell import BaseSpellCreate
from app.services.campaign_spells import create_campaign_spell


def _make_campaign() -> SimpleNamespace:
    return SimpleNamespace(id="camp-1", system=SystemType.DND5E)


def _make_payload(**overrides) -> BaseSpellCreate:
    data = {
        "canonicalKey": "thorn_whip_variant",
        "nameEn": "Thorn Whip Variant",
        "descriptionEn": "A campaign spell variant for testing.",
        "level": 1,
        "school": SpellSchool.TRANSMUTATION,
        "classesJson": ["Druid"],
    }
    data.update(overrides)
    return BaseSpellCreate(**data)


class CampaignSpellCreateServiceTests(unittest.TestCase):
    @patch("app.services.campaign_spells.get_campaign_spell_by_canonical_key")
    def test_create_campaign_spell_creates_custom_snapshot_entry(self, get_existing) -> None:
        get_existing.return_value = None
        db = MagicMock()
        campaign = _make_campaign()
        payload = _make_payload()

        spell = create_campaign_spell(
            db=db,
            campaign=campaign,
            payload=payload,
        )

        self.assertEqual(spell.campaign_id, campaign.id)
        self.assertIsNone(spell.base_spell_id)
        self.assertEqual(spell.canonical_key, "thorn_whip_variant")
        self.assertEqual(spell.name_en, "Thorn Whip Variant")
        self.assertEqual(spell.name_pt, "Thorn Whip Variant")
        self.assertEqual(spell.description_en, "A campaign spell variant for testing.")
        self.assertEqual(spell.level, 1)
        self.assertEqual(spell.school, SpellSchool.TRANSMUTATION)
        self.assertEqual(spell.classes_json, ["Druid"])
        self.assertEqual(spell.source, SpellSource.ADMIN_PANEL.value)
        self.assertTrue(spell.is_custom)
        self.assertTrue(spell.is_enabled)
        db.add.assert_called_once_with(spell)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(spell)

    @patch("app.services.campaign_spells.get_campaign_spell_by_canonical_key")
    def test_create_campaign_spell_rejects_duplicate_canonical_key(self, get_existing) -> None:
        get_existing.return_value = object()
        db = MagicMock()

        with self.assertRaises(HTTPException) as ctx:
            create_campaign_spell(
                db=db,
                campaign=_make_campaign(),
                payload=_make_payload(),
            )

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("thorn_whip_variant", ctx.exception.detail)
        db.add.assert_not_called()
        db.commit.assert_not_called()


class CampaignSpellCreateRouteTests(unittest.TestCase):
    @patch("app.api.routes.campaign_spells.create_campaign_spell")
    @patch("app.api.routes.campaign_spells.require_gm")
    def test_create_spell_route_returns_serialized_spell(
        self,
        require_gm_mock,
        create_campaign_spell_mock,
    ) -> None:
        campaign = _make_campaign()
        require_gm_mock.return_value = (campaign, MagicMock())
        create_campaign_spell_mock.return_value = SimpleNamespace(
            id="camp-spell-1",
            canonical_key="thunderlance",
            name_en="Thunderlance",
            name_pt="Lanca Trovejante",
            description_en="A lance of storm power.",
            description_pt=None,
            level=2,
            school=SpellSchool.EVOCATION,
            classes_json=["Wizard"],
            casting_time_type=None,
            casting_time="1 action",
            range_meters=18,
            range_text="18 m",
            target_type=None, area_shape=None,
            max_targets=None,
            selection_type=None,
            origin_type=None,
            target_anchor=None,
            attack_type=None,
            range_kind=None,
            effect_timing=None,
            radius_meters=None, length_meters=None, side_meters=None,
            duration="Instantaneous",
            components_json=["V", "S"],
            material_component_text=None,
            concentration=False,
            ritual=False,
            resolution_type=None,
            damage_dice=None,
            damage_type=None,
            heal_dice=None,
            saving_throw=None,
            save_success_outcome=None,
            cover_applies_to_save=None,
            requires_target_sight=None,
            requires_target_effect=None,
            requires_point_sight=None,
            requires_point_effect=None,
            upcast_json=None,
            upcast_mode=None,
            upcast_value=None,
            cantrip_scaling_json=None,
            effects_json=None,
            on_end_effects_json=None,
            variants_json=None,
            persistent_area_json=None,
            source=SpellSource.ADMIN_PANEL.value,
            source_ref=None,
            is_srd=False,
            out_of_combat_castable=False,
            out_of_combat_target="none",
            is_enabled=True,
        )

        result = create_spell(
            "camp-1",
            _make_payload(canonicalKey="thunderlance", nameEn="Thunderlance"),
            user=MagicMock(),
            session=MagicMock(),
        )

        self.assertEqual(result.id, "camp-spell-1")
        self.assertEqual(result.canonicalKey, "thunderlance")
        self.assertEqual(result.nameEn, "Thunderlance")
        self.assertEqual(result.system, SystemType.DND5E)
        create_campaign_spell_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
