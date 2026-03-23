from app.models.item import Item
from app.schemas.item import ItemRead
from app.services.money import to_copper


def to_item_read(item: Item) -> ItemRead:
    return ItemRead(
        id=item.id,
        campaignId=item.campaign_id,
        name=item.name,
        type=item.type,
        description=item.description,
        price=item.price,
        priceCopperValue=(
            to_copper(item.price, item.cost_unit.value if item.cost_unit else "gp")
            if item.price is not None
            else None
        ),
        weight=item.weight,
        damageDice=item.damage_dice,
        damageType=item.damage_type,
        rangeMeters=item.range_meters,
        rangeLongMeters=item.range_long_meters,
        versatileDamage=item.versatile_damage,
        weaponCategory=item.weapon_category,
        weaponRangeType=item.weapon_range_type,
        armorCategory=item.armor_category,
        armorClassBase=item.armor_class_base,
        dexBonusRule=item.dex_bonus_rule,
        strengthRequirement=item.strength_requirement,
        stealthDisadvantage=item.stealth_disadvantage,
        isShield=item.is_shield,
        properties=item.properties,
        baseItemId=item.base_item_id,
        canonicalKeySnapshot=item.canonical_key_snapshot,
        nameEnSnapshot=item.name_en_snapshot,
        namePtSnapshot=item.name_pt_snapshot,
        itemKind=item.item_kind,
        costUnit=item.cost_unit,
        isCustom=item.is_custom,
        isEnabled=item.is_enabled,
        createdAt=item.created_at,
        updatedAt=item.updated_at,
    )
