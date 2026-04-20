from __future__ import annotations

from app.models.base_item import BaseItemKind, BaseItemProperty, BaseItemWeaponRangeType
from app.models.item import ItemType

from .exceptions import CombatServiceError


class CombatEntityWeaponActionMixin:
    @staticmethod
    def _has_reach_property(properties: list[str] | None) -> bool:
        return BaseItemProperty.REACH.value in {str(value).strip().lower() for value in (properties or []) if isinstance(value, str)}

    @staticmethod
    def _normalize_weapon_range_type_value(value: object) -> str | None:
        if isinstance(value, BaseItemWeaponRangeType):
            return value.value
        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized or None
        return None

    @classmethod
    def _resolve_weapon_combat_action(cls, db, session_id: str, action) -> dict:
        from . import entity_actions as entity_actions_module

        campaign_weapon = None
        if action.campaignItemId:
            campaign_weapon = cls._get_campaign_item_for_session(db, session_id, action.campaignItemId)
            if campaign_weapon.item_kind != BaseItemKind.WEAPON and campaign_weapon.type != ItemType.WEAPON:
                raise CombatServiceError("Referenced campaign item is not a weapon.")
        catalog_weapon = None
        if action.weaponCanonicalKey and campaign_weapon is None:
            catalog_weapon = entity_actions_module.get_base_item_by_canonical_key(
                db=db,
                system=cls._get_campaign_system_for_session(db, session_id),
                canonical_key=action.weaponCanonicalKey,
            )
            if not catalog_weapon:
                raise CombatServiceError("Referenced weaponCanonicalKey was not found in the catalog.")
            if catalog_weapon.item_kind != BaseItemKind.WEAPON:
                raise CombatServiceError("Referenced weaponCanonicalKey is not a weapon.")
        damage_dice = action.damageDice or (campaign_weapon.damage_dice if campaign_weapon else (catalog_weapon.damage_dice if catalog_weapon else None))
        damage_type = action.damageType or cls._normalize_damage_type(campaign_weapon.damage_type if campaign_weapon else (catalog_weapon.damage_type if catalog_weapon else None))
        range_meters = action.rangeMeters if action.rangeMeters is not None else (int(campaign_weapon.range_meters) if campaign_weapon and campaign_weapon.range_meters is not None else (catalog_weapon.range_normal_meters if catalog_weapon else None))
        range_long_meters = action.rangeLongMeters if action.rangeLongMeters is not None else (int(campaign_weapon.range_long_meters) if campaign_weapon and campaign_weapon.range_long_meters is not None else (catalog_weapon.range_long_meters if catalog_weapon else None))
        range_type = action.rangeType.strip().lower() if isinstance(action.rangeType, str) and action.rangeType.strip() else (
            cls._normalize_weapon_range_type_value(campaign_weapon.weapon_range_type)
            if campaign_weapon and campaign_weapon.weapon_range_type is not None
            else (cls._normalize_weapon_range_type_value(catalog_weapon.weapon_range_type) if catalog_weapon and catalog_weapon.weapon_range_type is not None else ("melee" if action.isMelee else None))
        )
        has_reach = action.hasReach if isinstance(action.hasReach, bool) else (
            cls._has_reach_property(campaign_weapon.properties)
            if campaign_weapon
            else (cls._has_reach_property(catalog_weapon.weapon_properties_json) if catalog_weapon else False)
        )
        is_melee = action.isMelee if action.isMelee is not None else (
            campaign_weapon.weapon_range_type == BaseItemWeaponRangeType.MELEE
            if campaign_weapon and campaign_weapon.weapon_range_type is not None
            else (catalog_weapon.weapon_range_type == BaseItemWeaponRangeType.MELEE if catalog_weapon and catalog_weapon.weapon_range_type is not None else None)
        )
        if not damage_dice or not damage_type or is_melee is None:
            raise CombatServiceError("Weapon attack is missing damage profile. Provide a valid catalog weapon or manual overrides.")
        return {
            "name": action.name,
            "kind": action.kind,
            "description": action.description,
            "campaignItemId": action.campaignItemId,
            "weaponCanonicalKey": action.weaponCanonicalKey,
            "toHitBonus": action.toHitBonus,
            "damageDice": damage_dice,
            "damageBonus": action.damageBonus or 0,
            "damageType": damage_type,
            "rangeMeters": range_meters,
            "rangeLongMeters": range_long_meters,
            "rangeType": range_type,
            "hasReach": has_reach,
            "isMelee": is_melee,
        }
