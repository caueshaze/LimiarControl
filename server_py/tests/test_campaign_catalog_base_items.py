import unittest

from app.models.base_item import (
    BaseItem,
    BaseItemCostUnit,
    BaseItemKind,
    BaseItemEquipmentCategory,
    BaseItemWeaponCategory,
    BaseItemWeaponRangeType,
)
from app.models.campaign import SystemType
from app.models.item import ItemType
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

    def test_base_item_snapshot_preserves_healing_fields_for_consumables(self):
        base_item = BaseItem(
            id="base-potion",
            system=SystemType.DND5E,
            canonical_key="potion_healing",
            name_en="Healing Potion",
            name_pt="Poção de Cura",
            description_en="Restores vitality.",
            description_pt="Restaura vitalidade.",
            item_kind=BaseItemKind.CONSUMABLE,
            equipment_category=BaseItemEquipmentCategory.CONSUMABLE_SUPPLY,
            cost_quantity=50.0,
            cost_unit=BaseItemCostUnit.GP,
            weight=0.5,
            heal_dice="2d4",
            heal_bonus=2,
            weapon_properties_json=[],
            is_shield=False,
            is_srd=False,
            is_active=True,
        )

        item = _base_item_to_campaign_item(base_item, "campaign-1")

        self.assertEqual(item.base_item_id, "base-potion")
        self.assertEqual(item.item_kind, BaseItemKind.CONSUMABLE)
        self.assertEqual(item.heal_dice, "2d4")
        self.assertEqual(item.heal_bonus, 2)

    def test_base_item_snapshot_preserves_magic_spell_effect_fields(self):
        base_item = BaseItem(
            id="base-bracelet",
            system=SystemType.DND5E,
            canonical_key="phantyr_bracelet_magic_missile",
            name_en="Phantyr Bracelet of Magic Missile",
            name_pt="Bracelete de Phantyr: Mísseis Mágicos",
            description_en="Single-use bracelet.",
            description_pt="Bracelete de uso único.",
            item_kind=BaseItemKind.GEAR,
            equipment_category=BaseItemEquipmentCategory.JEWELRY,
            charges_max=1,
            recharge_type="none",
            magic_effect_json={
                "type": "cast_spell",
                "spellCanonicalKey": "magic_missile",
                "castLevel": 1,
                "ignoreComponents": True,
                "noFreeHandRequired": True,
            },
            is_shield=False,
            is_srd=False,
            is_active=True,
        )

        item = _base_item_to_campaign_item(base_item, "campaign-1")

        self.assertEqual(item.type, ItemType.MAGIC)
        self.assertEqual(item.charges_max, 1)
        self.assertEqual(item.recharge_type, "none")
        self.assertEqual(item.magic_effect_json["spellCanonicalKey"], "magic_missile")


class CombatDamageParsingTests(unittest.TestCase):
    def test_parse_dice_supports_static_damage_values(self):
        self.assertEqual(_parse_dice("1"), (0, 0, 1))
        self.assertEqual(_parse_dice("12"), (0, 0, 12))


if __name__ == "__main__":
    unittest.main()
