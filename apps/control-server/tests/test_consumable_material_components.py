from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from app.services.spell_material_components import (
    SpellMaterialError,
    consume_spell_material,
    validate_spell_material,
)


def _protection_spell():
    return SimpleNamespace(
        material_component_consumed=True,
        consumable_material_options_json=[
            {"key": "holy_water", "nameEn": "Holy water", "namePt": "Água benta", "quantity": 1},
            {
                "key": "powdered_silver_and_iron",
                "nameEn": "Powdered silver and iron",
                "namePt": "Prata e ferro em pó",
                "quantity": 1,
            },
        ],
    )


class ConsumableMaterialComponentsTests(unittest.TestCase):
    def test_strict_multi_option_requires_key(self):
        with self.assertRaises(SpellMaterialError):
            validate_spell_material(
                MagicMock(),
                session_id="s1",
                caster_user_id="u1",
                spell=_protection_spell(),
                consumable_material_key=None,
            )

    def test_invalid_key_raises(self):
        with self.assertRaises(SpellMaterialError):
            validate_spell_material(
                MagicMock(),
                session_id="s1",
                caster_user_id="u1",
                spell=_protection_spell(),
                consumable_material_key="wrong_key",
            )

    @patch("app.services.spell_material_components._resolve_inventory_item_for_material")
    def test_validate_does_not_consume(self, mock_resolve):
        inventory_item = SimpleNamespace(id="inv1", quantity=3)
        item = SimpleNamespace(name="Holy water")
        mock_resolve.return_value = (inventory_item, item)
        with patch("app.services.spell_material_components.consume_inventory_item") as consume_mock:
            result = validate_spell_material(
                MagicMock(),
                session_id="s1",
                caster_user_id="u1",
                spell=_protection_spell(),
                consumable_material_key="holy_water",
            )
        self.assertTrue(result.required)
        self.assertFalse(result.consumed)
        consume_mock.assert_not_called()

    @patch("app.services.spell_material_components._resolve_inventory_item_for_material")
    def test_material_key_normalization_accepts_hyphen_and_spaces(self, mock_resolve):
        inventory_item = SimpleNamespace(id="inv1", quantity=3)
        item = SimpleNamespace(name="Holy water")
        mock_resolve.return_value = (inventory_item, item)
        result = validate_spell_material(
            MagicMock(),
            session_id="s1",
            caster_user_id="u1",
            spell=_protection_spell(),
            consumable_material_key="holy-water",
        )
        self.assertEqual(result.material_key, "holy_water")

    @patch("app.services.spell_material_components._resolve_inventory_item_for_material")
    def test_consume_mutates_when_valid(self, mock_resolve):
        inventory_item = SimpleNamespace(id="inv1", quantity=3)
        item = SimpleNamespace(name="Holy water")
        mock_resolve.return_value = (inventory_item, item)
        with patch("app.services.spell_material_components.consume_inventory_item") as consume_mock:
            result = consume_spell_material(
                MagicMock(),
                session_id="s1",
                caster_user_id="u1",
                spell=_protection_spell(),
                consumable_material_key="holy_water",
            )
        self.assertTrue(result.required)
        self.assertTrue(result.consumed)
        self.assertEqual(result.material_key, "holy_water")
        consume_mock.assert_called_once()
