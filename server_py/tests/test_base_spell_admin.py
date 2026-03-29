import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.deps import require_system_admin
from app.api.serializers.base_spell import to_base_spell_read, to_base_spell_seed_entry
from app.api.routes.admin_base_spells import (
    admin_create_base_spell,
    admin_delete_base_spell,
    admin_list_base_spells,
    admin_update_base_spell,
)
from app.models.base_spell import (
    BaseSpell,
    CastingTimeType,
    ResolutionType,
    SpellSchool,
    SpellSource,
    TargetMode,
    UpcastMode,
)
from app.models.campaign import SystemType
from app.schemas.base_spell import (
    BaseSpellCreate,
    BaseSpellSeedDocument,
    BaseSpellUpdate,
    SpellUpcastConfig,
)
from app.services.base_spell_seeds import (
    bootstrap_base_spells_if_empty,
    export_base_spell_seed_document,
    read_base_spell_seed_document,
    write_base_spell_seed_document,
)
from app.services.base_spells import create_base_spell


def make_base_spell(**overrides):
    payload = {
        "id": "spell-1",
        "system": SystemType.DND5E,
        "canonical_key": "fireball",
        "name_en": "Fireball",
        "name_pt": "Bola de Fogo",
        "description_en": "A bright streak flashes from your pointing finger.",
        "description_pt": "Um clarão brilhante sai do seu dedo indicador.",
        "level": 3,
        "school": SpellSchool.EVOCATION,
        "classes_json": ["Sorcerer", "Wizard"],
        "casting_time_type": CastingTimeType.ACTION.value,
        "casting_time": "1 action",
        "range_meters": 45,
        "range_text": "150 ft",
        "target_mode": TargetMode.SPHERE.value,
        "duration": "Instantaneous",
        "components_json": ["V", "S", "M"],
        "material_component_text": "a tiny ball of bat guano and sulfur",
        "concentration": False,
        "ritual": False,
        "resolution_type": ResolutionType.DAMAGE.value,
        "saving_throw": "DEX",
        "save_success_outcome": "half_damage",
        "damage_dice": "8d6",
        "damage_type": "Fire",
        "heal_dice": None,
        "upcast_json": {"mode": "extra_damage_dice", "dice": "1d6", "perLevel": 1},
        "upcast_mode": UpcastMode.EXTRA_DAMAGE_DICE.value,
        "upcast_value": "1d6",
        "source": SpellSource.SEED_JSON_BOOTSTRAP.value,
        "source_ref": None,
        "is_srd": True,
        "is_active": True,
    }
    payload.update(overrides)
    return BaseSpell(**payload)


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class BaseSpellSchemaTests(unittest.TestCase):
    def _make_create(self, **overrides):
        defaults = {
            "canonicalKey": "fireball",
            "nameEn": "Fireball",
            "descriptionEn": "Explosion of flame.",
            "level": 3,
            "school": SpellSchool.EVOCATION,
            "resolutionType": "damage",
            "savingThrow": "DEX",
            "saveSuccessOutcome": "half_damage",
            "damageDice": "8d6",
            "damageType": "Fire",
        }
        defaults.update(overrides)
        return BaseSpellCreate(**defaults)

    def test_normalizes_canonical_key(self):
        spell = self._make_create(canonicalKey="  Fire Ball  ")
        self.assertEqual(spell.canonicalKey, "fire_ball")

    def test_normalizes_canonical_key_accents(self):
        spell = self._make_create(canonicalKey="Détectér Magie")
        self.assertEqual(spell.canonicalKey, "detecter_magie")

    def test_rejects_empty_canonical_key(self):
        with self.assertRaises(ValueError):
            self._make_create(canonicalKey="")

    def test_requires_name_en(self):
        with self.assertRaises(ValueError):
            self._make_create(nameEn="")

    def test_requires_description_en(self):
        with self.assertRaises(ValueError):
            self._make_create(descriptionEn="")

    def test_level_must_be_0_to_9(self):
        with self.assertRaises(ValueError):
            self._make_create(level=10)
        with self.assertRaises(ValueError):
            self._make_create(level=-1)

    def test_range_meters_cannot_be_negative(self):
        with self.assertRaises(ValueError):
            self._make_create(rangeMeters=-5)

    def test_normalizes_spell_classes(self):
        spell = self._make_create(classesJson=["wizard", "SORCERER"])
        self.assertEqual(spell.classesJson, ["Wizard", "Sorcerer"])

    def test_rejects_unknown_spell_class(self):
        with self.assertRaises(ValueError):
            self._make_create(classesJson=["Artificer"])

    def test_rejects_unknown_damage_type(self):
        with self.assertRaises(ValueError):
            self._make_create(damageType="Plasma")

    def test_normalizes_damage_type_case(self):
        spell = self._make_create(damageType="fire")
        self.assertEqual(spell.damageType, "Fire")

    def test_rejects_unknown_saving_throw(self):
        with self.assertRaises(ValueError):
            self._make_create(savingThrow="LUCK")

    def test_rejects_unknown_save_success_outcome(self):
        with self.assertRaises(ValueError):
            self._make_create(saveSuccessOutcome="quarter_damage")

    def test_rejects_unknown_casting_time_type(self):
        with self.assertRaises(ValueError):
            self._make_create(castingTimeType="instant")

    def test_rejects_unknown_target_mode(self):
        with self.assertRaises(ValueError):
            self._make_create(targetMode="area")

    def test_rejects_unknown_resolution_type(self):
        with self.assertRaises(ValueError):
            self._make_create(resolutionType="attack_roll")

    def test_rejects_unknown_upcast_mode(self):
        with self.assertRaises(ValueError):
            self._make_create(upcastMode="double")

    def test_accepts_structured_upcast(self):
        spell = self._make_create(
            resolutionType="heal",
            savingThrow=None,
            saveSuccessOutcome=None,
            damageDice=None,
            damageType=None,
            healDice="1d8",
            upcast={
                "mode": "extra_heal_dice",
                "dice": "1d8",
                "perLevel": 1,
            },
        )
        self.assertIsNotNone(spell.upcast)
        self.assertEqual(spell.upcast.mode, "extra_heal_dice")
        self.assertEqual(spell.upcast.dice, "1d8")

    def test_legacy_upcast_fields_are_normalized_to_structured_upcast(self):
        spell = self._make_create(
            resolutionType="heal",
            savingThrow=None,
            saveSuccessOutcome=None,
            damageDice=None,
            damageType=None,
            healDice="1d8",
            upcastMode="add_dice",
            upcastValue="1d8",
        )
        self.assertIsNotNone(spell.upcast)
        self.assertEqual(spell.upcast.mode, "extra_heal_dice")
        self.assertEqual(spell.upcast.dice, "1d8")

    def test_rejects_unknown_source(self):
        with self.assertRaises(ValueError):
            self._make_create(source="manual_note")

    def test_accepts_valid_dice_expression(self):
        spell = self._make_create(damageDice="2d6+3")
        self.assertEqual(spell.damageDice, "2d6+3")

    def test_rejects_invalid_dice_expression(self):
        with self.assertRaises(ValueError):
            self._make_create(damageDice="lots of damage")

    def test_damage_can_have_saving_throw(self):
        spell = self._make_create(
            resolutionType="damage",
            savingThrow="DEX",
            saveSuccessOutcome="half_damage",
            damageDice="8d6",
            damageType="Fire",
        )
        self.assertEqual(spell.savingThrow, "DEX")
        self.assertEqual(spell.saveSuccessOutcome, "half_damage")

    def test_control_can_have_saving_throw(self):
        spell = self._make_create(
            resolutionType="control",
            savingThrow="WIS",
            saveSuccessOutcome=None,
            damageDice=None,
            damageType=None,
        )
        self.assertEqual(spell.savingThrow, "WIS")
        self.assertIsNone(spell.saveSuccessOutcome)

    def test_buff_clears_damage_fields(self):
        spell = self._make_create(
            resolutionType="buff",
            savingThrow=None,
            saveSuccessOutcome=None,
            damageDice="2d6",
            damageType="Fire",
        )
        self.assertIsNone(spell.damageDice)
        self.assertIsNone(spell.damageType)

    def test_heal_requires_heal_dice(self):
        with self.assertRaises(ValueError):
            self._make_create(
                resolutionType="heal",
                savingThrow=None,
                saveSuccessOutcome=None,
                damageDice=None,
                damageType=None,
                healDice=None,
            )

    def test_clears_saving_throw_for_buff_resolution(self):
        spell = self._make_create(
            resolutionType="buff",
            savingThrow="DEX",
            saveSuccessOutcome=None,
            damageDice=None,
            damageType=None,
        )
        self.assertIsNone(spell.savingThrow)
        self.assertIsNone(spell.saveSuccessOutcome)

    def test_clears_saving_throw_for_utility_resolution(self):
        spell = self._make_create(
            resolutionType="utility",
            savingThrow="DEX",
            saveSuccessOutcome=None,
            damageDice=None,
            damageType=None,
        )
        self.assertIsNone(spell.savingThrow)
        self.assertIsNone(spell.saveSuccessOutcome)

    def test_clears_material_without_m_component(self):
        spell = self._make_create(
            componentsJson=["V", "S"],
            materialComponentText="some material",
        )
        self.assertIsNone(spell.materialComponentText)

    def test_clears_upcast_value_when_upcast_mode_none(self):
        spell = self._make_create(
            upcastMode="none",
            upcastValue="1d6",
        )
        self.assertIsNone(spell.upcastValue)

    def test_name_fallback_fills_name_pt(self):
        spell = self._make_create(nameEn="Fireball")
        self.assertEqual(spell.namePt, "Fireball")

    def test_range_meters_as_mechanical_source(self):
        spell = self._make_create(rangeMeters=45, rangeText="150 ft")
        self.assertEqual(spell.rangeMeters, 45)
        self.assertEqual(spell.rangeText, "150 ft")

    def test_range_text_editorial_only(self):
        """rangeMeters is the mechanical source; rangeText is editorial."""
        spell = self._make_create(rangeMeters=0, rangeText="Touch")
        self.assertEqual(spell.rangeMeters, 0)
        self.assertEqual(spell.rangeText, "Touch")


class BaseSpellSeedDocumentTests(unittest.TestCase):
    def test_rejects_duplicate_entries(self):
        spell = BaseSpellCreate(
            canonicalKey="fireball",
            nameEn="Fireball",
            descriptionEn="Explosion of flame.",
            level=3,
            school=SpellSchool.EVOCATION,
        )
        with self.assertRaisesRegex(ValueError, "Duplicate seed entry"):
            BaseSpellSeedDocument(version=1, spells=[spell, spell])


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class BaseSpellServiceTests(unittest.TestCase):
    @patch("app.services.base_spells.get_base_spell_by_canonical_key")
    def test_create_rejects_duplicate_canonical_key(self, mock_existing):
        mock_existing.return_value = make_base_spell()
        payload = BaseSpellCreate(
            canonicalKey="fireball",
            nameEn="Fireball",
            descriptionEn="Explosion of flame.",
            level=3,
            school=SpellSchool.EVOCATION,
        )
        with self.assertRaises(HTTPException) as ctx:
            create_base_spell(db=MagicMock(), payload=payload)
        self.assertEqual(ctx.exception.status_code, 409)


# ---------------------------------------------------------------------------
# Serializer tests
# ---------------------------------------------------------------------------

class BaseSpellSerializerTests(unittest.TestCase):
    def test_to_base_spell_read_maps_all_fields(self):
        spell = make_base_spell()
        read = to_base_spell_read(spell)
        self.assertEqual(read.canonicalKey, "fireball")
        self.assertEqual(read.castingTimeType, "action")
        self.assertEqual(read.resolutionType, "damage")
        self.assertEqual(read.savingThrow, "DEX")
        self.assertEqual(read.saveSuccessOutcome, "half_damage")
        self.assertEqual(read.damageDice, "8d6")
        self.assertEqual(read.damageType, "Fire")
        self.assertEqual(read.targetMode, "sphere")
        self.assertIsNotNone(read.upcast)
        self.assertEqual(read.upcast.mode, "extra_damage_dice")
        self.assertEqual(read.upcast.dice, "1d6")
        self.assertEqual(read.upcastMode, "extra_damage_dice")
        self.assertEqual(read.upcastValue, "1d6")
        self.assertEqual(read.rangeMeters, 45)
        self.assertEqual(read.rangeText, "150 ft")
        self.assertTrue(read.isSrd)
        self.assertTrue(read.isActive)

    def test_to_base_spell_seed_entry_roundtrip(self):
        spell = make_base_spell()
        entry = to_base_spell_seed_entry(spell)
        self.assertEqual(entry.canonicalKey, "fireball")
        self.assertEqual(entry.resolutionType, "damage")
        self.assertIsNotNone(entry.upcast)
        self.assertEqual(entry.upcast.mode, "extra_damage_dice")


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class BaseSpellSeedTests(unittest.TestCase):
    def test_write_and_read_seed_document_roundtrip(self):
        spell_a = BaseSpellCreate(
            canonicalKey="acid_splash",
            nameEn="Acid Splash",
            descriptionEn="Hurl a bubble of acid.",
            level=0,
            school=SpellSchool.CONJURATION,
        )
        spell_b = BaseSpellCreate(
            canonicalKey="fireball",
            nameEn="Fireball",
            descriptionEn="Explosion of flame.",
            level=3,
            school=SpellSchool.EVOCATION,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "base_spells.seed.json"
            write_base_spell_seed_document(
                BaseSpellSeedDocument(version=1, spells=[spell_b, spell_a]),
                path,
            )
            document = read_base_spell_seed_document(path)

        self.assertEqual(document.version, 1)
        # Should be sorted by level then canonical_key
        self.assertEqual(
            [s.canonicalKey for s in document.spells],
            ["acid_splash", "fireball"],
        )

    def test_read_seed_document_rejects_invalid_mechanical_values(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "base_spells.seed.json"
            path.write_text(
                """
                {
                  "version": 1,
                  "spells": [
                    {
                      "system": "DND5E",
                      "canonicalKey": "bad_spell",
                      "nameEn": "Bad Spell",
                      "descriptionEn": "Does bad things.",
                      "level": 1,
                      "school": "evocation",
                      "source": "free_text_source"
                    }
                  ]
                }
                """,
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Unknown source"):
                read_base_spell_seed_document(path)

    def test_bootstrap_imports_seed_when_catalog_is_empty(self):
        session = MagicMock()
        session.exec.return_value.first.return_value = None

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "base_spells.seed.json"
            path.write_text('{"version": 1, "spells": []}', encoding="utf-8")
            with patch(
                "app.services.base_spell_seeds.import_base_spell_seed_file",
                return_value={"inserted": 5, "updated": 0, "total": 5},
            ) as mock_import:
                result = bootstrap_base_spells_if_empty(session, path=path)

        self.assertEqual(result["inserted"], 5)
        mock_import.assert_called_once_with(session, path=path, replace=False)

    def test_export_base_spell_seed_document_writes_sorted_json(self):
        spell_b = make_base_spell(
            id="spell-b",
            canonical_key="fireball",
            name_en="Fireball",
            level=3,
        )
        spell_a = make_base_spell(
            id="spell-a",
            canonical_key="acid_splash",
            name_en="Acid Splash",
            level=0,
            school=SpellSchool.CONJURATION,
        )
        session = MagicMock()
        session.exec.return_value.all.return_value = [spell_b, spell_a]

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "base_spells.seed.json"
            export_base_spell_seed_document(session, path=path)
            document = read_base_spell_seed_document(path)

        self.assertEqual(
            [s.canonicalKey for s in document.spells],
            ["acid_splash", "fireball"],
        )


# ---------------------------------------------------------------------------
# Admin route tests
# ---------------------------------------------------------------------------

class AdminBaseSpellRouteTests(unittest.TestCase):
    def setUp(self):
        self.admin_user = SimpleNamespace(id="user-1", is_system_admin=True)

    @patch("app.api.routes.admin_base_spells.list_base_spells")
    def test_admin_list_route_returns_serialized_spells(self, mock_list):
        mock_list.return_value = [make_base_spell()]
        result = admin_list_base_spells(_user=self.admin_user, session=MagicMock())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].canonicalKey, "fireball")
        self.assertEqual(result[0].resolutionType, "damage")

    @patch("app.api.routes.admin_base_spells.create_base_spell")
    def test_admin_create_route_returns_created_spell(self, mock_create):
        mock_create.return_value = make_base_spell()
        payload = BaseSpellCreate(
            canonicalKey="fireball",
            nameEn="Fireball",
            descriptionEn="Explosion of flame.",
            level=3,
            school=SpellSchool.EVOCATION,
            resolutionType="damage",
            savingThrow="DEX",
            saveSuccessOutcome="half_damage",
            damageDice="8d6",
            damageType="Fire",
        )
        result = admin_create_base_spell(payload, _user=self.admin_user, session=MagicMock())
        self.assertEqual(result.canonicalKey, "fireball")

    @patch("app.api.routes.admin_base_spells.get_base_spell_by_id")
    @patch("app.api.routes.admin_base_spells.update_base_spell")
    def test_admin_update_route_returns_updated_spell(self, mock_update, mock_get):
        mock_get.return_value = make_base_spell()
        mock_update.return_value = make_base_spell(name_en="Greater Fireball")
        payload = BaseSpellUpdate(nameEn="Greater Fireball")
        result = admin_update_base_spell(
            "spell-1",
            payload,
            _user=self.admin_user,
            session=MagicMock(),
        )
        self.assertEqual(result.nameEn, "Greater Fireball")

    @patch("app.api.routes.admin_base_spells.get_base_spell_by_id")
    @patch("app.api.routes.admin_base_spells.delete_base_spell")
    def test_admin_delete_route_calls_service(self, mock_delete, mock_get):
        mock_get.return_value = make_base_spell()
        response = admin_delete_base_spell(
            "spell-1",
            _user=self.admin_user,
            session=MagicMock(),
        )
        self.assertIsNone(response)
        mock_delete.assert_called_once()

    def test_non_admin_is_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            require_system_admin(SimpleNamespace(is_system_admin=False))
        self.assertEqual(ctx.exception.status_code, 403)


# ---------------------------------------------------------------------------
# Seed JSON file validation
# ---------------------------------------------------------------------------

class SeedJsonFileTests(unittest.TestCase):
    def test_seed_json_file_is_valid(self):
        seed_path = Path(__file__).resolve().parents[2] / "Base" / "base_spells.seed.json"
        if not seed_path.is_file():
            self.skipTest("base_spells.seed.json not found")
        document = read_base_spell_seed_document(seed_path)
        self.assertGreater(len(document.spells), 0)
        for spell in document.spells:
            self.assertTrue(spell.canonicalKey)
            self.assertTrue(spell.nameEn)
            self.assertTrue(spell.descriptionEn)
            self.assertGreaterEqual(spell.level, 0)
            self.assertLessEqual(spell.level, 9)


# ---------------------------------------------------------------------------
# Upcast validation tests
# ---------------------------------------------------------------------------

class SpellUpcastValidationTests(unittest.TestCase):
    def _make_damage_spell(self, **overrides):
        defaults = {
            "canonicalKey": "fire_bolt",
            "nameEn": "Fire Bolt",
            "descriptionEn": "Hurls fire.",
            "level": 0,
            "school": SpellSchool.EVOCATION,
            "resolutionType": "damage",
            "damageDice": "1d10",
            "damageType": "Fire",
        }
        defaults.update(overrides)
        return BaseSpellCreate(**defaults)

    def _make_heal_spell(self, **overrides):
        defaults = {
            "canonicalKey": "cure_wounds",
            "nameEn": "Cure Wounds",
            "descriptionEn": "Heals a creature.",
            "level": 1,
            "school": SpellSchool.EVOCATION,
            "resolutionType": "heal",
            "healDice": "1d8",
        }
        defaults.update(overrides)
        return BaseSpellCreate(**defaults)

    def test_extra_damage_dice_requires_dice_or_flat(self):
        with self.assertRaises(ValueError):
            SpellUpcastConfig(mode="extra_damage_dice", perLevel=1)

    def test_extra_heal_dice_requires_dice_or_flat(self):
        with self.assertRaises(ValueError):
            SpellUpcastConfig(mode="extra_heal_dice", perLevel=1)

    def test_flat_bonus_requires_flat_value(self):
        with self.assertRaises(ValueError):
            SpellUpcastConfig(mode="flat_bonus", perLevel=1)

    def test_additional_targets_needs_no_dice(self):
        config = SpellUpcastConfig(mode="additional_targets", perLevel=1)
        self.assertEqual(config.mode, "additional_targets")

    def test_duration_scaling_needs_no_dice(self):
        config = SpellUpcastConfig(mode="duration_scaling", perLevel=1)
        self.assertEqual(config.mode, "duration_scaling")

    def test_extra_damage_dice_rejected_for_heal_spell(self):
        with self.assertRaises(ValueError):
            self._make_heal_spell(
                upcast={"mode": "extra_damage_dice", "dice": "1d6", "perLevel": 1},
            )

    def test_extra_heal_dice_rejected_for_damage_spell(self):
        with self.assertRaises(ValueError):
            self._make_damage_spell(
                upcast={"mode": "extra_heal_dice", "dice": "1d6", "perLevel": 1},
            )

    def test_buff_clears_damage_dice(self):
        spell = BaseSpellCreate(
            canonicalKey="shield",
            nameEn="Shield",
            descriptionEn="Protects you.",
            level=1,
            school=SpellSchool.ABJURATION,
            resolutionType="buff",
            damageDice="2d6",
            damageType="Fire",
        )
        self.assertIsNone(spell.damageDice)
        self.assertIsNone(spell.damageType)

    def test_effect_scaling_requires_scaling_key(self):
        with self.assertRaises(ValueError):
            SpellUpcastConfig(
                mode="effect_scaling",
                scalingSummary="something scales",
                perLevel=1,
            )

    def test_effect_scaling_requires_scaling_summary(self):
        with self.assertRaises(ValueError):
            SpellUpcastConfig(
                mode="effect_scaling",
                scalingKey="some_key",
                perLevel=1,
            )

    def test_effect_scaling_valid_with_required_fields(self):
        config = SpellUpcastConfig(
            mode="effect_scaling",
            scalingKey="armor_class_bonus",
            scalingSummary="+1 AC per slot level",
            perLevel=1,
        )
        self.assertEqual(config.mode, "effect_scaling")
        self.assertEqual(config.scalingKey, "armor_class_bonus")

    def test_effect_scaling_accepts_optional_editorial(self):
        config = SpellUpcastConfig(
            mode="effect_scaling",
            scalingKey="armor_class_bonus",
            scalingSummary="+1 AC per slot level",
            scalingEditorial="Cap at +5.",
            perLevel=1,
        )
        self.assertEqual(config.scalingEditorial, "Cap at +5.")

    def test_extra_effect_requires_unlock_key(self):
        with self.assertRaises(ValueError):
            SpellUpcastConfig(
                mode="extra_effect",
                unlockSummary="Something is unlocked",
                perLevel=1,
            )

    def test_extra_effect_requires_unlock_summary(self):
        with self.assertRaises(ValueError):
            SpellUpcastConfig(
                mode="extra_effect",
                unlockKey="additional_beam",
                perLevel=1,
            )

    def test_extra_effect_valid_with_required_fields(self):
        config = SpellUpcastConfig(
            mode="extra_effect",
            unlockKey="additional_beam",
            unlockSummary="One extra beam per slot level above 5th",
            perLevel=1,
        )
        self.assertEqual(config.mode, "extra_effect")
        self.assertEqual(config.unlockKey, "additional_beam")

    def test_hunters_mark_classified_as_buff(self):
        """Hunter's Mark is an offensive caster buff, not a debuff."""
        spell = BaseSpellCreate(
            canonicalKey="hunters_mark",
            nameEn="Hunter's Mark",
            descriptionEn="You mark a creature and deal extra damage when you hit it.",
            level=1,
            school=SpellSchool.DIVINATION,
            resolutionType="buff",
        )
        self.assertEqual(spell.resolutionType, "buff")
        self.assertIsNone(spell.savingThrow)


if __name__ == "__main__":
    unittest.main()
