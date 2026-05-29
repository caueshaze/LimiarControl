from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session, select

from app.models.campaign_member import CampaignMember
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.models.session import Session as CampaignSession
from app.services.healing_consumables_types import consume_inventory_item


class SpellMaterialError(ValueError):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass
class MaterialConsumptionResult:
    required: bool
    consumed: bool
    material_key: str | None
    material_label: str | None
    quantity: int
    inventory_item_id: str | None


def _normalize_key(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def _resolve_options(spell) -> list[dict]:
    options = getattr(spell, "consumable_material_options_json", None)
    if not isinstance(options, list):
        return []
    return [opt for opt in options if isinstance(opt, dict)]


def _resolve_selection_key(spell, requested_key: str | None) -> tuple[str, dict]:
    options = _resolve_options(spell)
    if not getattr(spell, "material_component_consumed", False):
        return "", {}
    if not options:
        raise SpellMaterialError("This spell requires consumed material but has no configured options.")
    normalized_key = _normalize_key(requested_key)
    if len(options) > 1 and normalized_key is None:
        raise SpellMaterialError("This spell requires consumableMaterialKey.")
    if normalized_key is None:
        normalized_key = _normalize_key(options[0].get("key"))
    if normalized_key is None:
        raise SpellMaterialError("Invalid consumable material option configuration.")
    for option in options:
        option_key = _normalize_key(option.get("key"))
        if option_key == normalized_key:
            return normalized_key, option
    raise SpellMaterialError(f"Invalid consumable material key: {requested_key!r}")


def _resolve_inventory_item_for_material(
    db: Session,
    *,
    session_id: str,
    caster_user_id: str,
    material_key: str,
    required_quantity: int,
) -> tuple[InventoryItem, Item]:
    session_entry = db.exec(
        select(CampaignSession).where(CampaignSession.id == session_id)
    ).first()
    if session_entry is None:
        raise SpellMaterialError("Session not found.", status_code=404)
    member = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == session_entry.campaign_id,
            CampaignMember.user_id == caster_user_id,
        )
    ).first()
    if member is None or not member.id:
        raise SpellMaterialError("Caster is not a campaign member in this session.")

    inventory_rows = db.exec(
        select(InventoryItem, Item)
        .join(Item, Item.id == InventoryItem.item_id)
        .where(
            InventoryItem.campaign_id == session_entry.campaign_id,
            InventoryItem.member_id == member.id,
            Item.campaign_id == session_entry.campaign_id,
            Item.canonical_key_snapshot == material_key,
            Item.is_enabled == True,  # noqa: E712
        )
    ).all()
    if not inventory_rows:
        raise SpellMaterialError(f"Missing required spell material: {material_key}.")

    inventory_item, item = inventory_rows[0]
    if inventory_item.quantity < required_quantity:
        raise SpellMaterialError(f"Insufficient quantity for material: {material_key}.")
    return inventory_item, item


def validate_spell_material(
    db: Session,
    *,
    session_id: str,
    caster_user_id: str,
    spell,
    consumable_material_key: str | None,
) -> MaterialConsumptionResult:
    if not getattr(spell, "material_component_consumed", False):
        return MaterialConsumptionResult(False, False, None, None, 0, None)
    selected_key, option = _resolve_selection_key(spell, consumable_material_key)
    required_quantity = int(option.get("quantity") or 1)
    inventory_item, item = _resolve_inventory_item_for_material(
        db,
        session_id=session_id,
        caster_user_id=caster_user_id,
        material_key=selected_key,
        required_quantity=required_quantity,
    )
    label = option.get("namePt") or option.get("nameEn") or item.name
    return MaterialConsumptionResult(
        required=True,
        consumed=False,
        material_key=selected_key,
        material_label=label if isinstance(label, str) else selected_key,
        quantity=required_quantity,
        inventory_item_id=inventory_item.id,
    )


def consume_spell_material(
    db: Session,
    *,
    session_id: str,
    caster_user_id: str,
    spell,
    consumable_material_key: str | None,
) -> MaterialConsumptionResult:
    validated = validate_spell_material(
        db,
        session_id=session_id,
        caster_user_id=caster_user_id,
        spell=spell,
        consumable_material_key=consumable_material_key,
    )
    if not validated.required:
        return validated
    inventory_item, _ = _resolve_inventory_item_for_material(
        db,
        session_id=session_id,
        caster_user_id=caster_user_id,
        material_key=validated.material_key or "",
        required_quantity=validated.quantity,
    )
    for _ in range(validated.quantity):
        consume_inventory_item(db, inventory_item)
    return MaterialConsumptionResult(
        required=True,
        consumed=True,
        material_key=validated.material_key,
        material_label=validated.material_label,
        quantity=validated.quantity,
        inventory_item_id=validated.inventory_item_id,
    )
