import unittest

from app.api.routes.sessions.state_common import serialize_equipped_armor
from app.models.base_item import BaseItemArmorCategory, BaseItemArmorMaterial, BaseItemDexBonusRule
from app.models.item import Item, ItemType


def _armor_item(
    *,
    name: str = "Armor",
    category: BaseItemArmorCategory = BaseItemArmorCategory.MEDIUM,
    base_ac: int = 14,
    dex_rule: BaseItemDexBonusRule = BaseItemDexBonusRule.MAX_2,
    material: BaseItemArmorMaterial | None = None,
    is_shield: bool = False,
) -> Item:
    return Item(
        id="item-1",
        campaign_id="camp-1",
        name=name,
        type=ItemType.ARMOR,
        description="armor",
        armor_category=category,
        armor_class_base=base_ac,
        dex_bonus_rule=dex_rule,
        armor_material=material,
        is_shield=is_shield,
    )


class EquippedArmorMaterialSnapshotTests(unittest.TestCase):
    def test_equipped_armor_includes_metal_material(self):
        item = _armor_item(name="Chain Mail", category=BaseItemArmorCategory.HEAVY, base_ac=16, dex_rule=BaseItemDexBonusRule.NONE, material=BaseItemArmorMaterial.METAL)
        snapshot = serialize_equipped_armor(item)
        self.assertEqual(snapshot["armorType"], "heavy")
        self.assertEqual(snapshot["armorMaterial"], "metal")

    def test_equipped_armor_includes_non_metal_material(self):
        item = _armor_item(name="Leather", category=BaseItemArmorCategory.LIGHT, base_ac=11, dex_rule=BaseItemDexBonusRule.FULL, material=BaseItemArmorMaterial.LEATHER)
        snapshot = serialize_equipped_armor(item)
        self.assertEqual(snapshot["armorType"], "light")
        self.assertEqual(snapshot["armorMaterial"], "leather")

    def test_equipped_armor_with_unknown_material_returns_null(self):
        item = _armor_item(name="Scale Mail", category=BaseItemArmorCategory.MEDIUM, base_ac=14, dex_rule=BaseItemDexBonusRule.MAX_2, material=None)
        snapshot = serialize_equipped_armor(item)
        self.assertEqual(snapshot["armorType"], "medium")
        self.assertIsNone(snapshot["armorMaterial"])

    def test_shape_without_armor_is_explicit(self):
        snapshot = serialize_equipped_armor(None)
        self.assertEqual(snapshot["armorType"], "none")
        self.assertEqual(snapshot["baseAC"], 0)
        self.assertIn("armorMaterial", snapshot)
        self.assertIsNone(snapshot["armorMaterial"])

    def test_shield_does_not_enter_equipped_armor(self):
        shield = _armor_item(
            name="Shield",
            category=BaseItemArmorCategory.SHIELD,
            base_ac=2,
            dex_rule=BaseItemDexBonusRule.FULL,
            material=BaseItemArmorMaterial.METAL,
            is_shield=True,
        )
        snapshot = serialize_equipped_armor(shield)
        self.assertEqual(snapshot["armorType"], "none")
        self.assertIsNone(snapshot["armorMaterial"])

    def test_material_is_not_inferred_from_armor_type_or_name(self):
        item = _armor_item(name="Chain Mail", category=BaseItemArmorCategory.HEAVY, base_ac=16, dex_rule=BaseItemDexBonusRule.NONE, material=None)
        snapshot = serialize_equipped_armor(item)
        self.assertEqual(snapshot["armorType"], "heavy")
        self.assertIsNone(snapshot["armorMaterial"])


if __name__ == "__main__":
    unittest.main()
