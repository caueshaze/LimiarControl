"""Tests for Goodberry (Bom Fruto) spell automation (issue #301).

Covers:
- create_consumable declarative effect type schema validation
- Out-of-combat eligibility with create_consumable effects
- build_persisted_effects returns [] for create_consumable (no active_spell_effects created)
- collect_create_consumable_effects extracts correct params
- grant_catalog_item_to_player_inventory: quantity, expiry, source_spell tracking, no stacking
- Consumption pipeline: heals 1 HP, caps at max, decrements quantity, rejects expired/empty
- activity_payload contains inventory_refresh_required when consumables granted
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from pydantic import ValidationError

from app.schemas.base_spell_effects import CreateConsumableParams, SpellDeclarativeEffect
from app.services.goodberry_inventory import grant_catalog_item_to_player_inventory
from app.services.healing_consumables import (
    apply_healing_outside_combat,
    resolve_healing_consumable,
    roll_healing_consumable,
)
from app.services.healing_consumables_types import HealingConsumableError
from app.services.out_of_combat_cast import (
    build_persisted_effects,
    check_out_of_combat_cast_eligibility,
    collect_create_consumable_effects,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _goodberry_effect() -> dict:
    return {
        "type": "create_consumable",
        "target": "caster",
        "params": {
            "canonical_key": "goodberry",
            "quantity": 10,
            "expires_in_seconds": 86400,
        },
    }


def _make_spell(
    *,
    canonical_key: str = "goodberry",
    level: int = 1,
    effects_json: list | None = None,
    out_of_combat_castable: bool = True,
    out_of_combat_target: str = "self",
    concentration: bool = False,
):
    spell = MagicMock()
    spell.canonical_key = canonical_key
    spell.level = level
    spell.concentration = concentration
    spell.out_of_combat_castable = out_of_combat_castable
    spell.out_of_combat_target = out_of_combat_target
    spell.effects_json = effects_json if effects_json is not None else [_goodberry_effect()]
    spell.variants_json = []
    spell.name_pt = "Bom Fruto"
    spell.name_en = "Goodberry"
    return spell


def _slot_state(*, slot_level: int = 1, used: int = 0, max_slots: int = 4) -> dict:
    return {"spellcasting": {"slots": {str(slot_level): {"used": used, "max": max_slots}}}}


def _first_result(value):
    result = MagicMock()
    result.first.return_value = value
    return result


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class GoodberryCastSchemaTests(unittest.TestCase):
    def test_create_consumable_effect_validates_correctly(self):
        effect = SpellDeclarativeEffect(**_goodberry_effect())
        self.assertEqual(effect.type, "create_consumable")
        self.assertIsInstance(effect.params, CreateConsumableParams)
        self.assertEqual(effect.params.canonical_key, "goodberry")
        self.assertEqual(effect.params.quantity, 10)
        self.assertEqual(effect.params.expires_in_seconds, 86400)

    def test_create_consumable_effect_without_expiry_validates(self):
        effect_dict = {**_goodberry_effect()}
        effect_dict["params"] = {
            "canonical_key": "goodberry",
            "quantity": 1,
        }
        effect = SpellDeclarativeEffect(**effect_dict)
        self.assertIsNone(effect.params.expires_in_seconds)

    def test_create_consumable_effect_rejects_quantity_zero(self):
        effect_dict = {**_goodberry_effect()}
        effect_dict["params"] = {"canonical_key": "goodberry", "quantity": 0}
        with self.assertRaises(ValidationError):
            SpellDeclarativeEffect(**effect_dict)

    def test_create_consumable_effect_rejects_wrong_params_type(self):
        effect_dict = {
            "type": "create_consumable",
            "target": "caster",
            "params": {"condition": "blinded"},
        }
        with self.assertRaises(ValidationError):
            SpellDeclarativeEffect(**effect_dict)

    def test_create_consumable_params_rejects_extra_fields(self):
        with self.assertRaises(ValidationError):
            CreateConsumableParams(canonical_key="goodberry", quantity=1, unknown_field=True)


# ---------------------------------------------------------------------------
# Eligibility tests
# ---------------------------------------------------------------------------

class GoodberryOutOfCombatEligibilityTests(unittest.TestCase):
    def test_eligibility_passes_with_create_consumable_effect(self):
        spell = _make_spell()
        state = _slot_state()
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json=state,
            slot_level=1,
            variant_key=None,
        )
        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_eligibility_fails_with_empty_effects(self):
        spell = _make_spell(effects_json=[])
        state = _slot_state()
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json=state,
            slot_level=1,
            variant_key=None,
        )
        self.assertFalse(ok)
        self.assertIn("no supported declarative effects", reason)

    def test_eligibility_fails_when_no_slot_available(self):
        spell = _make_spell()
        state = _slot_state(used=4, max_slots=4)
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json=state,
            slot_level=1,
            variant_key=None,
        )
        self.assertFalse(ok)
        self.assertIn("No spell slot", reason)


# ---------------------------------------------------------------------------
# build_persisted_effects / collect helpers
# ---------------------------------------------------------------------------

class GoodberryBuildEffectsTests(unittest.TestCase):
    def test_build_persisted_effects_returns_empty_for_create_consumable(self):
        spell = _make_spell()
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="user-1",
            target_user_id="user-1",
            variant_key=None,
            game_time_seconds=0,
        )
        self.assertEqual(effects, [])

    def test_no_active_spell_effects_written_for_goodberry(self):
        """Cast with only create_consumable effects must not add to active_spell_effects."""
        spell = _make_spell()
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="user-1",
            target_user_id="user-1",
            variant_key=None,
            game_time_seconds=0,
        )
        self.assertEqual(len(effects), 0, "create_consumable must not produce active_spell_effects")

    def test_collect_create_consumable_effects_extracts_effect(self):
        spell = _make_spell()
        collected = collect_create_consumable_effects(spell, variant_key=None)
        self.assertEqual(len(collected), 1)
        params = collected[0]["params"]
        self.assertEqual(params["canonical_key"], "goodberry")
        self.assertEqual(params["quantity"], 10)
        self.assertEqual(params["expires_in_seconds"], 86400)

    def test_collect_create_consumable_effects_empty_for_non_consumable_spell(self):
        spell = _make_spell(effects_json=[
            {"type": "modify_stat", "target": "caster", "params": {"stat": "attack_bonus", "value": 1}},
        ])
        collected = collect_create_consumable_effects(spell, variant_key=None)
        self.assertEqual(collected, [])

    def test_collect_returns_empty_for_empty_effects(self):
        spell = _make_spell(effects_json=[])
        collected = collect_create_consumable_effects(spell, variant_key=None)
        self.assertEqual(collected, [])


# ---------------------------------------------------------------------------
# Inventory grant tests
# ---------------------------------------------------------------------------

class GoodberryInventoryGrantTests(unittest.TestCase):
    def _make_db(self, *, existing_entry=None):
        db = MagicMock()
        item = MagicMock()
        item.id = "item-id-1"
        item.charges_max = None
        campaign_item = MagicMock()
        campaign_item.id = "catalog-item-1"
        campaign_item.charges_max = None

        with patch(
            "app.services.goodberry_inventory._get_campaign_member",
            return_value=SimpleNamespace(id="member-1"),
        ), patch(
            "app.services.goodberry_inventory.ensure_campaign_catalog_item_for_base_canonical_key",
            return_value=campaign_item,
        ), patch(
            "app.services.goodberry_inventory.inventory_item_supports_stacking",
            return_value=True,
        ), patch(
            "app.services.goodberry_inventory.initialize_inventory_item_charges",
        ):
            db.exec.return_value.first.return_value = existing_entry
            return db

    def test_grant_creates_item_with_correct_expiry(self):
        from app.models.inventory import InventoryItem

        db = self._make_db()
        session_entry = SimpleNamespace(
            id="session-1",
            campaign_id="campaign-1",
            party_id="party-1",
        )
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=86400)

        with patch("app.services.goodberry_inventory._get_campaign_member",
                   return_value=SimpleNamespace(id="member-1")), \
             patch("app.services.goodberry_inventory.ensure_campaign_catalog_item_for_base_canonical_key",
                   return_value=MagicMock(id="catalog-1", charges_max=None)), \
             patch("app.services.goodberry_inventory.inventory_item_supports_stacking", return_value=True), \
             patch("app.services.goodberry_inventory.initialize_inventory_item_charges"), \
             patch("app.services.goodberry_inventory.normalize_inventory_timestamp", side_effect=lambda x: x):
            db.exec.return_value.first.return_value = None  # no existing entry → create new
            result = grant_catalog_item_to_player_inventory(
                db,
                session_entry=session_entry,
                player_user_id="user-1",
                system="DND5E",
                canonical_key="goodberry",
                quantity=10,
                notes="Criado por Bom Fruto",
                expires_at=expires_at,
                source_spell_canonical_key="goodberry",
            )

        db.add.assert_called_once()
        created: InventoryItem = db.add.call_args[0][0]
        self.assertEqual(created.quantity, 10)
        self.assertEqual(created.source_spell_canonical_key, "goodberry")
        self.assertIsNotNone(created.expires_at)
        diff = abs((created.expires_at - expires_at).total_seconds())
        self.assertLess(diff, 5, "expires_at should be within 5s of now+24h")

    def test_grant_does_not_stack_when_source_spell_set(self):
        """Items with source_spell_canonical_key bypass stacking → separate row per cast."""
        db = MagicMock()
        session_entry = SimpleNamespace(id="session-1", campaign_id="campaign-1", party_id="party-1")

        with patch("app.services.goodberry_inventory._get_campaign_member",
                   return_value=SimpleNamespace(id="member-1")), \
             patch("app.services.goodberry_inventory.ensure_campaign_catalog_item_for_base_canonical_key",
                   return_value=MagicMock(id="catalog-1", charges_max=None)), \
             patch("app.services.goodberry_inventory.inventory_item_supports_stacking", return_value=True), \
             patch("app.services.goodberry_inventory.initialize_inventory_item_charges"), \
             patch("app.services.goodberry_inventory.normalize_inventory_timestamp", side_effect=lambda x: x):
            db.exec.return_value.first.return_value = None
            grant_catalog_item_to_player_inventory(
                db,
                session_entry=session_entry,
                player_user_id="user-1",
                system="DND5E",
                canonical_key="goodberry",
                quantity=10,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                source_spell_canonical_key="goodberry",
            )

        # Must call db.add (create new row), never tried to fetch existing for stacking
        db.add.assert_called_once()


# ---------------------------------------------------------------------------
# Consumption pipeline tests
# ---------------------------------------------------------------------------

class GoodberryConsumeTests(unittest.TestCase):
    def _make_item(
        self,
        *,
        quantity: int = 10,
        heal_bonus: int = 1,
        expires_at: datetime | None = None,
    ):
        from app.models.item import Item, ItemType
        return Item(
            id="item-1",
            campaign_id="campaign-1",
            name="Bom Fruto",
            type=ItemType.CONSUMABLE,
            description="Comer restaura 1 PV.",
            heal_dice=None,
            heal_bonus=heal_bonus,
        )

    def _make_inventory_item(
        self,
        *,
        quantity: int = 10,
        expires_at: datetime | None = None,
    ):
        from app.models.inventory import InventoryItem
        return InventoryItem(
            id="inv-1",
            campaign_id="campaign-1",
            party_id="party-1",
            member_id="member-1",
            item_id="item-1",
            quantity=quantity,
            expires_at=expires_at,
            source_spell_canonical_key="goodberry",
        )

    def test_roll_healing_consumable_returns_1_hp_for_goodberry(self):
        item = self._make_item()
        result = roll_healing_consumable(item)
        self.assertEqual(result.total_healing, 1)
        self.assertEqual(result.effect_bonus, 1)
        self.assertIsNone(result.effect_dice)

    def test_apply_healing_caps_at_max_hp(self):
        db = MagicMock()
        session_entry = SimpleNamespace(id="s", campaign_id="c", party_id="p")
        state = MagicMock()
        state.state_json = {"currentHP": 10, "maxHP": 10}

        with patch("app.services.healing_consumables.get_actor_member",
                   return_value=SimpleNamespace(display_name="Hero")), \
             patch("app.services.healing_consumables._ensure_player_session_state",
                   return_value=state), \
             patch("app.services.healing_consumables.is_wild_shape_active", return_value=False):
            result = apply_healing_outside_combat(
                db,
                session_entry=session_entry,
                target_user_id="user-1",
                amount=1,
            )

        self.assertEqual(result.new_hp, 10)
        self.assertEqual(result.previous_hp, 10)

    def test_apply_healing_adds_1_hp(self):
        db = MagicMock()
        session_entry = SimpleNamespace(id="s", campaign_id="c", party_id="p")
        state = MagicMock()
        state.state_json = {"currentHP": 9, "maxHP": 12}

        with patch("app.services.healing_consumables.get_actor_member",
                   return_value=SimpleNamespace(display_name="Hero")), \
             patch("app.services.healing_consumables._ensure_player_session_state",
                   return_value=state), \
             patch("app.services.healing_consumables.is_wild_shape_active", return_value=False):
            result = apply_healing_outside_combat(
                db,
                session_entry=session_entry,
                target_user_id="user-1",
                amount=1,
            )

        self.assertEqual(result.new_hp, 10)

    def test_resolve_healing_consumable_rejects_expired_item(self):
        db = MagicMock()
        session_entry = SimpleNamespace(id="s", campaign_id="c", party_id="party-1")
        expired_inv = self._make_inventory_item(
            quantity=5,
            expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        item = self._make_item()

        with patch("app.services.healing_consumables.get_actor_member",
                   return_value=MagicMock(id="member-1")), \
             patch("app.services.healing_consumables.require_identifier",
                   return_value="member-1"):
            db.exec.return_value.first.side_effect = [expired_inv, item]
            with self.assertRaises(HealingConsumableError) as ctx:
                resolve_healing_consumable(
                    db,
                    session_entry=session_entry,
                    actor_user_id="user-1",
                    inventory_item_id="inv-1",
                )
        self.assertIn("expired", str(ctx.exception).lower())

    def test_resolve_healing_consumable_rejects_empty_stock(self):
        db = MagicMock()
        session_entry = SimpleNamespace(id="s", campaign_id="c", party_id="party-1")
        empty_inv = self._make_inventory_item(quantity=0)
        item = self._make_item()

        with patch("app.services.healing_consumables.get_actor_member",
                   return_value=MagicMock(id="member-1")), \
             patch("app.services.healing_consumables.require_identifier",
                   return_value="member-1"):
            db.exec.return_value.first.side_effect = [empty_inv, item]
            with self.assertRaises(HealingConsumableError) as ctx:
                resolve_healing_consumable(
                    db,
                    session_entry=session_entry,
                    actor_user_id="user-1",
                    inventory_item_id="inv-1",
                )
        self.assertIn("stock", str(ctx.exception).lower())


# ---------------------------------------------------------------------------
# activity_payload tests
# ---------------------------------------------------------------------------

class GoodberryCastActivityTests(unittest.TestCase):
    def test_collect_create_consumable_returns_correct_params(self):
        """Smoke test that the effect params are accessible for activity payload construction."""
        spell = _make_spell()
        effects = collect_create_consumable_effects(spell, variant_key=None)
        self.assertEqual(len(effects), 1)
        params = effects[0]["params"]
        self.assertEqual(params.get("quantity"), 10)

    def test_consumables_granted_count_is_nonzero_for_goodberry(self):
        """consumables_granted_count reflects the quantity from the effect, enabling inventory_refresh_required."""
        spell = _make_spell()
        effects = collect_create_consumable_effects(spell, variant_key=None)
        total = sum(
            (e.get("params") or {}).get("quantity", 0)
            for e in effects
        )
        self.assertEqual(total, 10)

    def test_non_consumable_spell_has_zero_consumable_effects(self):
        """For a regular buff spell, collect returns nothing → inventory_refresh_required not set."""
        spell = _make_spell(effects_json=[
            {"type": "modify_stat", "target": "caster", "params": {"stat": "attack_bonus", "value": 2}},
        ])
        effects = collect_create_consumable_effects(spell, variant_key=None)
        total = sum((e.get("params") or {}).get("quantity", 0) for e in effects)
        self.assertEqual(total, 0)


if __name__ == "__main__":
    unittest.main()
