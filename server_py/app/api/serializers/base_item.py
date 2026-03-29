from __future__ import annotations

from app.models.base_item import BaseItem
from app.schemas.base_item import BaseItemCreate, BaseItemRead
from app.services.item_properties import normalize_item_properties


def _normalize_weapon_properties(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
        candidates = list(value)
    elif value:
        candidates = [str(value)]
    else:
        candidates = []
    normalized_properties, _invalid_properties = normalize_item_properties(candidates)
    return normalized_properties


def to_base_item_read(item: BaseItem) -> BaseItemRead:
    return BaseItemRead(
        id=item.id,
        system=item.system,
        canonicalKey=item.canonical_key,
        nameEn=item.name_en,
        namePt=item.name_pt,
        descriptionEn=item.description_en,
        descriptionPt=item.description_pt,
        itemKind=item.item_kind,
        equipmentCategory=item.equipment_category,
        costQuantity=item.cost_quantity,
        costUnit=item.cost_unit,
        weight=item.weight,
        weaponCategory=item.weapon_category,
        weaponRangeType=item.weapon_range_type,
        damageDice=item.damage_dice,
        damageType=item.damage_type,
        healDice=item.heal_dice,
        healBonus=item.heal_bonus,
        chargesMax=item.charges_max,
        rechargeType=item.recharge_type,
        magicEffect=item.magic_effect_json,
        rangeNormalMeters=item.range_normal_meters,
        rangeLongMeters=item.range_long_meters,
        versatileDamage=item.versatile_damage,
        weaponPropertiesJson=_normalize_weapon_properties(item.weapon_properties_json),
        armorCategory=item.armor_category,
        armorClassBase=item.armor_class_base,
        dexBonusRule=item.dex_bonus_rule,
        strengthRequirement=item.strength_requirement,
        stealthDisadvantage=item.stealth_disadvantage,
        isShield=item.is_shield,
        source=item.source,
        sourceRef=item.source_ref,
        isSrd=item.is_srd,
        isActive=item.is_active,
        aliases=[],
    )


def to_base_item_seed_entry(item: BaseItem) -> BaseItemCreate:
    return BaseItemCreate(
        system=item.system,
        canonicalKey=item.canonical_key,
        nameEn=item.name_en,
        namePt=item.name_pt,
        descriptionEn=item.description_en,
        descriptionPt=item.description_pt,
        itemKind=item.item_kind,
        equipmentCategory=item.equipment_category,
        costQuantity=item.cost_quantity,
        costUnit=item.cost_unit,
        weight=item.weight,
        weaponCategory=item.weapon_category,
        weaponRangeType=item.weapon_range_type,
        damageDice=item.damage_dice,
        damageType=item.damage_type,
        healDice=item.heal_dice,
        healBonus=item.heal_bonus,
        chargesMax=item.charges_max,
        rechargeType=item.recharge_type,
        magicEffect=item.magic_effect_json,
        rangeNormalMeters=item.range_normal_meters,
        rangeLongMeters=item.range_long_meters,
        versatileDamage=item.versatile_damage,
        weaponPropertiesJson=_normalize_weapon_properties(item.weapon_properties_json),
        armorCategory=item.armor_category,
        armorClassBase=item.armor_class_base,
        dexBonusRule=item.dex_bonus_rule,
        strengthRequirement=item.strength_requirement,
        stealthDisadvantage=bool(item.stealth_disadvantage),
        isShield=item.is_shield,
        source=item.source,
        sourceRef=item.source_ref,
        isSrd=item.is_srd,
        isActive=item.is_active,
    )
