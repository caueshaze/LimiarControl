import unittest

from app.models.base_item import (
    BaseItem,
    BaseItemCostUnit,
    BaseItemKind,
    BaseItemWeaponCategory,
    BaseItemWeaponRangeType,
)
from app.models.campaign import SystemType
from app.services.combat_service.exceptions import _parse_dice
from app.services.campaign_catalog import _base_item_to_campaign_item


class CampaignCatalogBaseItemCompatibilityTests(unittest.TestCase):
    def test_base_item_snapshot_preserves_catalog_fields_for_campaign_items(self):
        base_item = BaseItem(
            id="base-dagger",
            system=SystemType.DND5E,
            canonical_key="dagger",
            name_en="Dagger",
            name_pt="Adaga",
            description_en="A sharp blade.",
            description_pt="Uma lâmina afiada.",
            item_kind=BaseItemKind.WEAPON,
            cost_quantity=2.0,
            cost_unit=BaseItemCostUnit.GP,
            weight=1.0,
            weapon_category=BaseItemWeaponCategory.SIMPLE,
            weapon_range_type=BaseItemWeaponRangeType.MELEE,
            damage_dice="1d4",
            damage_type="piercing",
            range_normal_meters=20,
            range_long_meters=60,
            weapon_properties_json=["finesse", "light", "thrown"],
            is_shield=False,
            is_srd=False,
            is_active=True,
        )

        item = _base_item_to_campaign_item(base_item, "campaign-1")

        self.assertEqual(item.base_item_id, "base-dagger")
        self.assertEqual(item.canonical_key_snapshot, "dagger")
        self.assertEqual(item.name_en_snapshot, "Dagger")
        self.assertEqual(item.name_pt_snapshot, "Adaga")
        self.assertEqual(item.damage_dice, "1d4")
        self.assertEqual(item.damage_type, "piercing")
        self.assertEqual(item.weapon_category, BaseItemWeaponCategory.SIMPLE)
        self.assertEqual(item.weapon_range_type, BaseItemWeaponRangeType.MELEE)
        self.assertEqual(item.properties, ["finesse", "light", "thrown"])
        self.assertEqual(item.price, 2.0)
        self.assertEqual(item.cost_unit, BaseItemCostUnit.GP)
        self.assertEqual(item.range_meters, 20.0)
        self.assertEqual(item.range_long_meters, 60.0)


class CombatDamageParsingTests(unittest.TestCase):
    def test_parse_dice_supports_static_damage_values(self):
        self.assertEqual(_parse_dice("1"), (0, 0, 1))
        self.assertEqual(_parse_dice("12"), (0, 0, 12))


if __name__ == "__main__":
    unittest.main()
