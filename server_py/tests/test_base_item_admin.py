import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.deps import require_system_admin
from app.api.serializers.base_item import to_base_item_read
from app.api.routes.auth import me
from app.api.routes.admin_base_items import (
    admin_create_base_item,
    admin_delete_base_item,
    admin_list_base_items,
    admin_sync_base_items_seed,
    admin_update_base_item,
)
from app.models.base_item import (
    BaseItem,
    BaseItemArmorCategory,
    BaseItemCostUnit,
    BaseItemDamageType,
    BaseItemDexBonusRule,
    BaseItemEquipmentCategory,
    BaseItemKind,
    BaseItemProperty,
    BaseItemSource,
    BaseItemWeaponCategory,
    BaseItemWeaponRangeType,
)
from app.models.campaign import SystemType
from app.models.item import ItemType
from app.schemas.base_item import BaseItemCreate, BaseItemSeedDocument, BaseItemUpdate
from app.schemas.item import ItemCreate
from app.services.base_item_seeds import (
    bootstrap_base_items_if_empty,
    export_base_item_seed_document,
    import_base_item_seed_document,
    read_base_item_seed_document,
    write_base_item_seed_document,
)
from app.services.base_items import create_base_item


def make_base_item(**overrides):
    payload = {
        "id": "base-item-1",
        "system": SystemType.DND5E,
        "canonical_key": "dagger",
        "name_en": "Dagger",
        "name_pt": "Adaga",
        "description_en": "A sharp blade.",
        "description_pt": "Uma lâmina afiada.",
        "item_kind": BaseItemKind.WEAPON,
        "equipment_category": None,
        "cost_quantity": 2.0,
        "cost_unit": BaseItemCostUnit.GP,
        "weight": 1.0,
        "weapon_category": BaseItemWeaponCategory.SIMPLE,
        "weapon_range_type": BaseItemWeaponRangeType.MELEE,
        "damage_dice": "1d4",
        "damage_type": "piercing",
        "range_normal_meters": 20,
        "range_long_meters": 60,
        "versatile_damage": None,
        "weapon_properties_json": ["finesse", "light", "thrown"],
        "armor_category": None,
        "armor_class_base": None,
        "dex_bonus_rule": None,
        "strength_requirement": None,
        "stealth_disadvantage": False,
        "is_shield": False,
        "source": BaseItemSource.SEED_JSON_BOOTSTRAP,
        "source_ref": "Dagger",
        "is_srd": False,
        "is_active": True,
    }
    payload.update(overrides)
    return BaseItem(**payload)


class RequireSystemAdminTests(unittest.TestCase):
    def test_allows_system_admin(self):
        user = SimpleNamespace(is_system_admin=True)
        self.assertIs(require_system_admin(user), user)

    def test_rejects_non_admin(self):
        with self.assertRaises(HTTPException) as ctx:
            require_system_admin(SimpleNamespace(is_system_admin=False))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_me_response_exposes_system_admin_flag(self):
        profile = me(
            SimpleNamespace(
                id="user-1",
                username="admin",
                display_name="Admin",
                role="GM",
                is_system_admin=True,
            )
        )
        self.assertTrue(profile.isSystemAdmin)


class BaseItemSchemaTests(unittest.TestCase):
    def test_normalizes_weapon_payload(self):
        payload = BaseItemCreate(
            canonicalKey="  Great Club  ",
            namePt="Clava Grande",
            itemKind=BaseItemKind.WEAPON,
            weaponCategory=BaseItemWeaponCategory.SIMPLE,
            weaponRangeType=BaseItemWeaponRangeType.MELEE,
            damageDice="1",
            damageType=BaseItemDamageType.BLUDGEONING,
            rangeNormalMeters=5,
            weaponPropertiesJson=["Duas Mãos", "Pesada"],
        )

        self.assertEqual(payload.canonicalKey, "great_club")
        self.assertEqual(payload.nameEn, "Clava Grande")
        self.assertEqual(
            payload.weaponPropertiesJson,
            [BaseItemProperty.TWO_HANDED, BaseItemProperty.HEAVY],
        )
        self.assertEqual(payload.damageDice, "1")

    def test_normalizes_heavy_armor_rule(self):
        payload = BaseItemCreate(
            canonicalKey="chain_mail",
            nameEn="Chain Mail",
            itemKind=BaseItemKind.ARMOR,
            armorCategory=BaseItemArmorCategory.HEAVY,
            armorClassBase=16,
            dexBonusRule="0",
            strengthRequirement=0,
        )

        self.assertEqual(payload.dexBonusRule, BaseItemDexBonusRule.NONE)
        self.assertIsNone(payload.strengthRequirement)

    def test_accepts_enum_instances_from_serializers(self):
        payload = BaseItemCreate(
            canonicalKey="longbow",
            nameEn="Longbow",
            itemKind=BaseItemKind.WEAPON,
            equipmentCategory=BaseItemEquipmentCategory.AMMUNITION,
            weaponCategory=BaseItemWeaponCategory.MARTIAL,
            weaponRangeType=BaseItemWeaponRangeType.RANGED,
            damageDice="1d8",
            damageType=BaseItemDamageType.PIERCING,
            rangeNormalMeters=150,
            rangeLongMeters=600,
            source=BaseItemSource.SEED_JSON_BOOTSTRAP,
        )

        self.assertEqual(payload.equipmentCategory, BaseItemEquipmentCategory.AMMUNITION)
        self.assertEqual(payload.damageType, BaseItemDamageType.PIERCING)
        self.assertEqual(payload.source, BaseItemSource.SEED_JSON_BOOTSTRAP)

    def test_rejects_invalid_weapon_property(self):
        with self.assertRaisesRegex(ValueError, "Invalid weapon properties"):
            BaseItemCreate(
                canonicalKey="broken_sword",
                nameEn="Broken Sword",
                itemKind=BaseItemKind.WEAPON,
                weaponCategory=BaseItemWeaponCategory.SIMPLE,
                weaponRangeType=BaseItemWeaponRangeType.MELEE,
                damageDice="1d4",
                damageType="slashing",
                weaponPropertiesJson=["not-a-real-property"],
            )

    def test_rejects_non_weapon_property_in_weapon_properties(self):
        with self.assertRaisesRegex(
            ValueError,
            "weaponPropertiesJson only accepts weapon properties",
        ):
            BaseItemCreate(
                canonicalKey="stealth_sword",
                nameEn="Stealth Sword",
                itemKind=BaseItemKind.WEAPON,
                weaponCategory=BaseItemWeaponCategory.SIMPLE,
                weaponRangeType=BaseItemWeaponRangeType.MELEE,
                damageDice="1d6",
                damageType="slashing",
                rangeNormalMeters=5,
                weaponPropertiesJson=["stealth_disadvantage"],
            )

    def test_rejects_invalid_source(self):
        with self.assertRaisesRegex(ValueError, "Unknown source"):
            BaseItemCreate(
                canonicalKey="staff",
                nameEn="Staff",
                itemKind=BaseItemKind.WEAPON,
                weaponCategory=BaseItemWeaponCategory.SIMPLE,
                weaponRangeType=BaseItemWeaponRangeType.MELEE,
                damageDice="1d6",
                damageType="bludgeoning",
                rangeNormalMeters=5,
                source="manual_note",
            )

    def test_rejects_long_range_for_non_thrown_melee_weapon(self):
        with self.assertRaisesRegex(
            ValueError,
            "rangeLongMeters can only differ from rangeNormalMeters for ranged weapons or thrown weapons",
        ):
            BaseItemCreate(
                canonicalKey="maul",
                nameEn="Maul",
                itemKind=BaseItemKind.WEAPON,
                weaponCategory=BaseItemWeaponCategory.MARTIAL,
                weaponRangeType=BaseItemWeaponRangeType.MELEE,
                damageDice="2d6",
                damageType="bludgeoning",
                rangeNormalMeters=5,
                rangeLongMeters=10,
            )

    def test_rejects_strength_requirement_for_non_heavy_armor(self):
        with self.assertRaisesRegex(
            ValueError,
            "strengthRequirement only applies to heavy armor",
        ):
            BaseItemCreate(
                canonicalKey="breastplate",
                nameEn="Breastplate",
                itemKind=BaseItemKind.ARMOR,
                armorCategory=BaseItemArmorCategory.MEDIUM,
                armorClassBase=14,
                dexBonusRule="max_2",
                strengthRequirement=13,
            )

    def test_accepts_structured_healing_consumable(self):
        payload = BaseItemCreate(
            canonicalKey="potion_healing",
            nameEn="Healing Potion",
            itemKind=BaseItemKind.CONSUMABLE,
            equipmentCategory=BaseItemEquipmentCategory.CONSUMABLE_SUPPLY,
            healDice="2d4",
            healBonus=2,
        )

        self.assertEqual(payload.healDice, "2d4")
        self.assertEqual(payload.healBonus, 2)

    def test_accepts_magic_item_spell_effect_shape(self):
        payload = BaseItemCreate(
            canonicalKey="phantyr_bracelet_magic_missile",
            nameEn="Phantyr Bracelet of Magic Missile",
            itemKind=BaseItemKind.GEAR,
            equipmentCategory=BaseItemEquipmentCategory.JEWELRY,
            chargesMax=1,
            rechargeType="none",
            magicEffect={
                "type": "cast_spell",
                "spellCanonicalKey": "magic_missile",
                "castLevel": 1,
                "ignoreComponents": True,
                "noFreeHandRequired": True,
            },
        )

        self.assertEqual(payload.chargesMax, 1)
        self.assertEqual(payload.rechargeType, "none")
        self.assertEqual(payload.magicEffect.spellCanonicalKey, "magic_missile")

    def test_rejects_healing_fields_for_non_consumable_base_item(self):
        with self.assertRaisesRegex(
            ValueError,
            "Only consumables can define healDice or healBonus",
        ):
            BaseItemCreate(
                canonicalKey="blessed_armor",
                nameEn="Blessed Armor",
                itemKind=BaseItemKind.ARMOR,
                armorCategory=BaseItemArmorCategory.HEAVY,
                armorClassBase=16,
                dexBonusRule="none",
                healDice="2d4",
                healBonus=2,
            )

    @patch("app.services.magic_item_effects.get_base_spell_by_canonical_key")
    def test_create_base_item_rejects_missing_magic_effect_spell_reference(self, mock_get_spell):
        mock_get_spell.return_value = None
        payload = BaseItemCreate(
            canonicalKey="phantyr_bracelet_magic_missile",
            nameEn="Phantyr Bracelet of Magic Missile",
            itemKind=BaseItemKind.GEAR,
            equipmentCategory=BaseItemEquipmentCategory.JEWELRY,
            chargesMax=1,
            rechargeType="none",
            magicEffect={
                "type": "cast_spell",
                "spellCanonicalKey": "magic_missile",
                "castLevel": 1,
                "ignoreComponents": True,
                "noFreeHandRequired": True,
            },
        )

        db = MagicMock()
        db.exec.return_value.first.return_value = None
        with self.assertRaises(HTTPException) as ctx:
            create_base_item(db=db, payload=payload)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("magicEffect.spellCanonicalKey", ctx.exception.detail)

    def test_seed_document_rejects_duplicate_entries(self):
        item = BaseItemCreate(
            canonicalKey="dagger",
            nameEn="Dagger",
            itemKind=BaseItemKind.WEAPON,
            weaponCategory=BaseItemWeaponCategory.SIMPLE,
            weaponRangeType=BaseItemWeaponRangeType.MELEE,
            damageDice="1d4",
            damageType="piercing",
            rangeNormalMeters=5,
        )

        with self.assertRaisesRegex(ValueError, "Duplicate seed entry"):
            BaseItemSeedDocument(version=1, items=[item, item])


class BaseItemServiceTests(unittest.TestCase):
    @patch("app.services.base_items.get_base_item_by_canonical_key")
    def test_create_base_item_rejects_duplicate_canonical_key(self, mock_existing):
        mock_existing.return_value = make_base_item()
        payload = BaseItemCreate(
            canonicalKey="dagger",
            nameEn="Dagger",
            itemKind=BaseItemKind.WEAPON,
            weaponCategory=BaseItemWeaponCategory.SIMPLE,
            weaponRangeType=BaseItemWeaponRangeType.MELEE,
            damageDice="1d4",
            damageType="piercing",
            rangeNormalMeters=5,
        )

        with self.assertRaises(HTTPException) as ctx:
            create_base_item(db=MagicMock(), payload=payload)

        self.assertEqual(ctx.exception.status_code, 409)


class BaseItemSeedTests(unittest.TestCase):
    def test_write_and_read_seed_document_roundtrip(self):
        item_a = BaseItemCreate(
            canonicalKey="club",
            nameEn="Club",
            itemKind=BaseItemKind.WEAPON,
            weaponCategory=BaseItemWeaponCategory.SIMPLE,
            weaponRangeType=BaseItemWeaponRangeType.MELEE,
            damageDice="1d4",
            damageType="bludgeoning",
            rangeNormalMeters=5,
        )
        item_b = BaseItemCreate(
            canonicalKey="dagger",
            nameEn="Dagger",
            itemKind=BaseItemKind.WEAPON,
            weaponCategory=BaseItemWeaponCategory.SIMPLE,
            weaponRangeType=BaseItemWeaponRangeType.MELEE,
            damageDice="1d4",
            damageType="piercing",
            rangeNormalMeters=5,
        )
        item_c = BaseItemCreate(
            canonicalKey="potion_healing",
            nameEn="Healing Potion",
            itemKind=BaseItemKind.CONSUMABLE,
            equipmentCategory=BaseItemEquipmentCategory.CONSUMABLE_SUPPLY,
            healDice="2d4",
            healBonus=2,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "base_items.seed.json"
            write_base_item_seed_document(
                BaseItemSeedDocument(version=1, items=[item_b, item_c, item_a]),
                path,
            )
            document = read_base_item_seed_document(path)

        self.assertEqual(document.version, 1)
        self.assertEqual(
            [item.canonicalKey for item in document.items],
            ["potion_healing", "club", "dagger"],
        )
        potion = next(item for item in document.items if item.canonicalKey == "potion_healing")
        self.assertEqual(potion.healDice, "2d4")
        self.assertEqual(potion.healBonus, 2)

    def test_default_seed_contains_structured_healing_potions(self):
        document = read_base_item_seed_document()
        by_key = {item.canonicalKey: item for item in document.items}

        self.assertEqual(by_key["goodberry"].healBonus, 1)
        self.assertEqual(by_key["potion_healing"].healDice, "2d4")
        self.assertEqual(by_key["potion_healing"].healBonus, 2)
        self.assertEqual(by_key["potion_healing_greater"].healDice, "4d4")
        self.assertEqual(by_key["potion_healing_greater"].healBonus, 4)
        self.assertEqual(by_key["potion_healing_superior"].healDice, "8d4")
        self.assertEqual(by_key["potion_healing_superior"].healBonus, 8)
        self.assertEqual(by_key["potion_healing_supreme"].healDice, "10d4")
        self.assertEqual(by_key["potion_healing_supreme"].healBonus, 20)

    def test_serializer_normalizes_legacy_weapon_property_aliases(self):
        item = make_base_item(weapon_properties_json=["heavy", "two-handed"])

        serialized = to_base_item_read(item)

        self.assertEqual(serialized.weaponPropertiesJson, ["heavy", "two_handed"])

    def test_read_seed_document_rejects_invalid_mechanical_values(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "base_items.seed.json"
            path.write_text(
                """
                {
                  "version": 1,
                  "items": [
                    {
                      "system": "DND5E",
                      "canonicalKey": "bad_item",
                      "nameEn": "Bad Item",
                      "itemKind": "weapon",
                      "weaponCategory": "simple",
                      "weaponRangeType": "melee",
                      "damageDice": "1d4",
                      "damageType": "piercing",
                      "source": "free_text_source"
                    }
                  ]
                }
                """,
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Unknown source"):
                read_base_item_seed_document(path)

    def test_bootstrap_imports_seed_when_catalog_is_empty(self):
        session = MagicMock()
        session.exec.return_value.first.return_value = None

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "base_items.seed.json"
            path.write_text('{"version": 1, "items": []}', encoding="utf-8")
            with patch(
                "app.services.base_item_seeds.import_base_item_seed_file",
                return_value={"inserted": 2, "updated": 0, "total": 2},
            ) as mock_import:
                result = bootstrap_base_items_if_empty(session, path=path)

        self.assertEqual(result["inserted"], 2)
        mock_import.assert_called_once_with(session, path=path, replace=False)

    def test_export_base_item_seed_document_writes_sorted_json(self):
        item_b = make_base_item(
            id="item-b",
            canonical_key="dagger",
            name_en="Dagger",
            name_pt="Adaga",
        )
        item_a = make_base_item(
            id="item-a",
            canonical_key="club",
            name_en="Club",
            name_pt="Clava",
        )
        session = MagicMock()
        session.exec.return_value.all.return_value = [item_b, item_a]

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "base_items.seed.json"
            export_base_item_seed_document(session, path=path)
            document = read_base_item_seed_document(path)

        self.assertEqual([item.canonicalKey for item in document.items], ["club", "dagger"])

    @patch("app.services.base_item_seeds.update_base_item")
    def test_replace_deactivates_stale_items_without_deleting_them(self, mock_update):
        existing = make_base_item(id="item-existing", canonical_key="dagger", is_active=True)
        stale = make_base_item(id="item-stale", canonical_key="club", is_active=True)
        session = MagicMock()
        session.exec.return_value.all.return_value = [existing, stale]
        mock_update.return_value = existing
        document = BaseItemSeedDocument(
            version=1,
            items=[
                BaseItemCreate(
                    canonicalKey="dagger",
                    nameEn="Dagger",
                    itemKind=BaseItemKind.WEAPON,
                    weaponCategory=BaseItemWeaponCategory.SIMPLE,
                    weaponRangeType=BaseItemWeaponRangeType.MELEE,
                    damageDice="1d4",
                    damageType="piercing",
                    rangeNormalMeters=5,
                ),
            ],
        )

        result = import_base_item_seed_document(session, document, replace=True)

        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["deactivated"], 1)
        self.assertFalse(stale.is_active)
        session.delete.assert_not_called()
        session.commit.assert_called_once()
        mock_update.assert_called_once_with(
            db=session,
            item=existing,
            payload=document.items[0],
            commit=False,
            refresh=False,
        )

    @patch("app.services.base_item_seeds.create_base_item")
    def test_import_rolls_back_all_changes_when_a_seed_entry_fails(self, mock_create):
        created = make_base_item(id="item-created", canonical_key="dagger")
        mock_create.side_effect = [
            created,
            RuntimeError("boom"),
        ]
        session = MagicMock()
        session.exec.return_value.all.return_value = []
        document = BaseItemSeedDocument(
            version=1,
            items=[
                BaseItemCreate(
                    canonicalKey="dagger",
                    nameEn="Dagger",
                    itemKind=BaseItemKind.WEAPON,
                    weaponCategory=BaseItemWeaponCategory.SIMPLE,
                    weaponRangeType=BaseItemWeaponRangeType.MELEE,
                    damageDice="1d4",
                    damageType="piercing",
                    rangeNormalMeters=5,
                ),
                BaseItemCreate(
                    canonicalKey="club",
                    nameEn="Club",
                    itemKind=BaseItemKind.WEAPON,
                    weaponCategory=BaseItemWeaponCategory.SIMPLE,
                    weaponRangeType=BaseItemWeaponRangeType.MELEE,
                    damageDice="1d4",
                    damageType="bludgeoning",
                    rangeNormalMeters=5,
                ),
            ],
        )

        with self.assertRaisesRegex(RuntimeError, "boom"):
            import_base_item_seed_document(session, document, replace=False)

        session.commit.assert_not_called()
        session.rollback.assert_called_once()


class AdminBaseItemRouteTests(unittest.TestCase):
    def setUp(self):
        self.admin_user = SimpleNamespace(id="user-1", is_system_admin=True)

    @patch("app.api.routes.admin_base_items.list_base_items")
    def test_admin_list_route_returns_serialized_items(self, mock_list):
        mock_list.return_value = [make_base_item()]

        result = admin_list_base_items(_user=self.admin_user, session=MagicMock())

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].canonicalKey, "dagger")

    @patch("app.api.routes.admin_base_items.import_base_item_seed_file")
    def test_admin_sync_seed_route_returns_sync_result(self, mock_import):
        mock_import.return_value = {"inserted": 4, "updated": 121, "total": 125}

        result = admin_sync_base_items_seed(_user=self.admin_user, session=MagicMock())

        self.assertEqual(result.inserted, 4)
        self.assertEqual(result.updated, 121)
        self.assertEqual(result.total, 125)
        mock_import.assert_called_once()

    @patch("app.api.routes.admin_base_items.create_base_item")
    def test_admin_create_route_returns_created_item(self, mock_create):
        mock_create.return_value = make_base_item()
        payload = BaseItemCreate(
            canonicalKey="dagger",
            nameEn="Dagger",
            itemKind=BaseItemKind.WEAPON,
            weaponCategory=BaseItemWeaponCategory.SIMPLE,
            weaponRangeType=BaseItemWeaponRangeType.MELEE,
            damageDice="1d4",
            damageType="piercing",
            rangeNormalMeters=5,
        )

        result = admin_create_base_item(payload, _user=self.admin_user, session=MagicMock())

        self.assertEqual(result.canonicalKey, "dagger")

    @patch("app.api.routes.admin_base_items.get_base_item_by_id")
    @patch("app.api.routes.admin_base_items.update_base_item")
    def test_admin_update_route_returns_updated_item(self, mock_update, mock_get):
        mock_get.return_value = make_base_item()
        mock_update.return_value = make_base_item(name_en="Updated Dagger", name_pt="Adaga Nova")
        payload = BaseItemUpdate(
            canonicalKey="dagger",
            nameEn="Updated Dagger",
            itemKind=BaseItemKind.WEAPON,
            weaponCategory=BaseItemWeaponCategory.SIMPLE,
            weaponRangeType=BaseItemWeaponRangeType.MELEE,
            damageDice="1d4",
            damageType="piercing",
            rangeNormalMeters=5,
        )

        result = admin_update_base_item(
            "base-item-1",
            payload,
            _user=self.admin_user,
            session=MagicMock(),
        )

        self.assertEqual(result.nameEn, "Updated Dagger")

    @patch("app.api.routes.admin_base_items.get_base_item_by_id")
    @patch("app.api.routes.admin_base_items.delete_base_item")
    def test_admin_delete_route_calls_service(self, mock_delete, mock_get):
        mock_get.return_value = make_base_item()

        response = admin_delete_base_item(
            "base-item-1",
            _user=self.admin_user,
            session=MagicMock(),
        )

        self.assertIsNone(response)
        mock_delete.assert_called_once()


class ItemSchemaTests(unittest.TestCase):
    def test_rejects_invalid_structured_item_property(self):
        with self.assertRaisesRegex(ValueError, "Invalid item properties"):
            ItemCreate(
                name="Broken Blade",
                type=ItemType.WEAPON,
                description="Bad data",
                damageDice="1d6",
                damageType="slashing",
                weaponCategory=BaseItemWeaponCategory.SIMPLE,
                weaponRangeType=BaseItemWeaponRangeType.MELEE,
                properties=["free_text"],
            )

    def test_accepts_thrown_weapon_range_in_campaign_item(self):
        payload = ItemCreate(
            name="Dagger",
            type=ItemType.WEAPON,
            description="Thrown weapon",
            damageDice="1d4",
            damageType="piercing",
            weaponCategory=BaseItemWeaponCategory.SIMPLE,
            weaponRangeType=BaseItemWeaponRangeType.MELEE,
            rangeMeters=6,
            rangeLongMeters=18,
            properties=["finesse", "light", "thrown"],
        )

        self.assertEqual(payload.properties, ["finesse", "light", "thrown"])

    def test_accepts_structured_healing_consumable_item(self):
        payload = ItemCreate(
            name="Healing Potion",
            type=ItemType.CONSUMABLE,
            description="Restores HP",
            healDice="2d4",
            healBonus=2,
        )

        self.assertEqual(payload.healDice, "2d4")
        self.assertEqual(payload.healBonus, 2)

    def test_rejects_healing_fields_for_non_consumable_campaign_item(self):
        with self.assertRaisesRegex(
            ValueError,
            "Only consumables can define healDice or healBonus",
        ):
            ItemCreate(
                name="Blessed Sword",
                type=ItemType.WEAPON,
                description="Incorrect data",
                damageDice="1d8",
                damageType="slashing",
                weaponCategory=BaseItemWeaponCategory.MARTIAL,
                weaponRangeType=BaseItemWeaponRangeType.MELEE,
                rangeMeters=5,
                healDice="2d4",
                healBonus=2,
            )


if __name__ == "__main__":
    unittest.main()
