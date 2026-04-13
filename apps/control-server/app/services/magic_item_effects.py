from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.base_spell import BaseSpell
from app.models.campaign import Campaign, SystemType
from app.models.campaign_spell import CampaignSpell
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.services.base_spells import get_base_spell_by_canonical_key


def get_magic_item_effect(item_like: object) -> dict | None:
    raw = getattr(item_like, "magic_effect_json", None)
    if not isinstance(raw, dict):
        return None
    effect_type = raw.get("type")
    if not isinstance(effect_type, str) or not effect_type.strip():
        return None
    return raw


def has_cast_spell_magic_effect(item_like: object) -> bool:
    effect = get_magic_item_effect(item_like)
    return bool(effect and effect.get("type") == "cast_spell")


def get_magic_item_spell_key(item_like: object) -> str | None:
    effect = get_magic_item_effect(item_like)
    if not effect or effect.get("type") != "cast_spell":
        return None
    value = effect.get("spellCanonicalKey")
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def get_item_charge_capacity(item: Item | None) -> int | None:
    if item is None:
        return None
    value = getattr(item, "charges_max", None)
    if not isinstance(value, int) or value <= 0:
        return None
    return value


def get_inventory_item_charges_current(
    entry: InventoryItem,
    item: Item | None,
) -> int | None:
    capacity = get_item_charge_capacity(item)
    if capacity is None:
        return None
    current = entry.charges_current if isinstance(entry.charges_current, int) else capacity
    return max(0, min(current, capacity))


def initialize_inventory_item_charges(entry: InventoryItem, item: Item | None) -> None:
    current = get_inventory_item_charges_current(entry, item)
    if current is None:
        entry.charges_current = None
        return
    entry.charges_current = current


def consume_inventory_item_charge(entry: InventoryItem, item: Item | None) -> int | None:
    current = get_inventory_item_charges_current(entry, item)
    if current is None:
        return None
    if current <= 0:
        raise ValueError("This item has no charges remaining.")
    entry.charges_current = current - 1
    return entry.charges_current


def inventory_item_supports_stacking(item: Item | None) -> bool:
    return get_item_charge_capacity(item) is None


def _validate_cast_level(*, cast_level: int | None, spell_level: int, label: str) -> None:
    if cast_level is None:
        return
    if cast_level < spell_level:
        raise HTTPException(
            status_code=400,
            detail=f"{label} castLevel cannot be lower than the spell level.",
        )


def _spell_key_from_magic_effect(magic_effect: dict | None) -> str | None:
    if not isinstance(magic_effect, dict):
        return None
    value = magic_effect.get("spellCanonicalKey")
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def validate_base_magic_item_effect_reference(
    db: Session,
    *,
    system: SystemType,
    magic_effect: dict | None,
) -> None:
    if not magic_effect:
        return
    if magic_effect.get("type") != "cast_spell":
        raise HTTPException(status_code=400, detail="Unsupported magicEffect type.")
    spell_key = _spell_key_from_magic_effect(magic_effect)
    if not spell_key:
        raise HTTPException(status_code=400, detail="magicEffect.spellCanonicalKey is required.")
    base_spell = get_base_spell_by_canonical_key(
        db=db,
        system=system,
        canonical_key=spell_key,
    )
    if not base_spell:
        raise HTTPException(
            status_code=400,
            detail=f"magicEffect.spellCanonicalKey '{spell_key}' was not found in the base spell catalog.",
        )
    _validate_cast_level(
        cast_level=magic_effect.get("castLevel"),
        spell_level=base_spell.level,
        label="magicEffect",
    )


def validate_campaign_magic_item_effect_reference(
    db: Session,
    *,
    campaign_id: str,
    magic_effect: dict | None,
) -> None:
    if not magic_effect:
        return
    if magic_effect.get("type") != "cast_spell":
        raise HTTPException(status_code=400, detail="Unsupported magicEffect type.")
    spell_key = _spell_key_from_magic_effect(magic_effect)
    if not spell_key:
        raise HTTPException(status_code=400, detail="magicEffect.spellCanonicalKey is required.")

    campaign = db.exec(select(Campaign).where(Campaign.id == campaign_id)).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign_spell = db.exec(
        select(CampaignSpell).where(
            CampaignSpell.campaign_id == campaign_id,
            func.lower(CampaignSpell.canonical_key) == spell_key,
            CampaignSpell.is_enabled == True,  # noqa: E712
        )
    ).first()
    if campaign_spell:
        _validate_cast_level(
            cast_level=magic_effect.get("castLevel"),
            spell_level=campaign_spell.level,
            label="magicEffect",
        )
        return

    base_spell = get_base_spell_by_canonical_key(
        db=db,
        system=campaign.system,
        canonical_key=spell_key,
    )
    if not base_spell:
        raise HTTPException(
            status_code=400,
            detail=f"magicEffect.spellCanonicalKey '{spell_key}' was not found in the campaign/base spell catalog.",
        )
    _validate_cast_level(
        cast_level=magic_effect.get("castLevel"),
        spell_level=base_spell.level,
        label="magicEffect",
    )
