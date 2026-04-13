from __future__ import annotations

from datetime import datetime, timezone
import random
from math import floor

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.base_item import BaseItemKind, BaseItemWeaponRangeType
from app.models.campaign import Campaign, SystemType
from app.models.combat import CombatPhase, CombatState
from app.models.session import Session as CampaignSession
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.models.campaign_entity import CampaignEntity
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.schemas.combat import (
    CombatApplyDamageRequest,
    CombatApplyHealingRequest,
    CombatAttackRequest,
    CombatCastSpellRequest,
    CombatEntityActionRequest,
    CombatSetInitiativeRequest,
    CombatStartRequest,
)
from app.schemas.campaign_entity import (
    SKILL_ABILITY_MAP,
    CombatAction,
    ability_modifier as derive_ability_modifier,
    resolve_initiative_bonus as resolve_entity_initiative_bonus,
    resolve_saving_throw_bonus as resolve_entity_saving_throw_bonus,
    resolve_skill_bonus as resolve_entity_skill_bonus,
)
from app.services.base_items import get_base_item_by_canonical_key
from app.services.base_spells import get_base_spell_by_canonical_key
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel

from .exceptions import CombatServiceError, _roll_dice_expression


class CombatEntityActionMixin:

    @classmethod
    def _resolve_weapon_combat_action(
        cls,
        db: Session,
        session_id: str,
        action: CombatAction,
    ) -> dict:
        campaign_weapon = None
        if action.campaignItemId:
            campaign_weapon = cls._get_campaign_item_for_session(db, session_id, action.campaignItemId)
            if campaign_weapon.item_kind != BaseItemKind.WEAPON and campaign_weapon.type != ItemType.WEAPON:
                raise CombatServiceError("Referenced campaign item is not a weapon.")

        catalog_weapon = None
        if action.weaponCanonicalKey and campaign_weapon is None:
            catalog_weapon = get_base_item_by_canonical_key(
                db=db,
                system=cls._get_campaign_system_for_session(db, session_id),
                canonical_key=action.weaponCanonicalKey,
            )
            if not catalog_weapon:
                raise CombatServiceError("Referenced weaponCanonicalKey was not found in the catalog.")
            if catalog_weapon.item_kind != BaseItemKind.WEAPON:
                raise CombatServiceError("Referenced weaponCanonicalKey is not a weapon.")

        damage_dice = action.damageDice or (
            campaign_weapon.damage_dice if campaign_weapon else (catalog_weapon.damage_dice if catalog_weapon else None)
        )
        damage_type = action.damageType or cls._normalize_damage_type(
            campaign_weapon.damage_type if campaign_weapon else (
                catalog_weapon.damage_type if catalog_weapon else None
            )
        )
        range_meters = (
            action.rangeMeters
            if action.rangeMeters is not None
            else (
                int(campaign_weapon.range_meters)
                if campaign_weapon and campaign_weapon.range_meters is not None
                else (catalog_weapon.range_normal_meters if catalog_weapon else None)
            )
        )
        is_melee = (
            action.isMelee
            if action.isMelee is not None
            else (
                campaign_weapon.weapon_range_type == BaseItemWeaponRangeType.MELEE
                if campaign_weapon and campaign_weapon.weapon_range_type is not None
                else (
                    catalog_weapon.weapon_range_type == BaseItemWeaponRangeType.MELEE
                    if catalog_weapon and catalog_weapon.weapon_range_type is not None
                    else None
                )
            )
        )

        if not damage_dice or not damage_type or is_melee is None:
            raise CombatServiceError(
                "Weapon attack is missing damage profile. "
                "Provide a valid catalog weapon or manual overrides."
            )

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
            "isMelee": is_melee,
        }

    @classmethod
    def _resolve_spell_combat_action(
        cls,
        db: Session,
        session_id: str,
        npc: CampaignEntity,
        action: CombatAction,
    ) -> dict:
        if not action.spellCanonicalKey:
            raise CombatServiceError("Automated spell actions require spellCanonicalKey.")

        base_spell = cls._get_spell_catalog_entry_for_session(
            db,
            session_id,
            action.spellCanonicalKey,
        )

        spellcasting = cls._as_dict(npc.spellcasting)
        damage_type = action.damageType or cls._normalize_damage_type(base_spell.damage_type)
        save_ability = cls._normalize_ability_name(action.saveAbility or base_spell.saving_throw)

        resolved = {
            "name": action.name,
            "kind": action.kind,
            "description": action.description,
            "spellCanonicalKey": action.spellCanonicalKey,
            "castAtLevel": action.castAtLevel,
            # Structured metric range is the only mechanical source for spell automation.
            # range_text stays descriptive/editorial and must never be parsed here.
            "rangeMeters": (
                action.rangeMeters
                if action.rangeMeters is not None
                else base_spell.range_meters
            ),
            "damageType": damage_type,
        }
        structured_upcast = cls._get_structured_spell_upcast(
            getattr(base_spell, "upcast_json", None)
        )

        if action.kind == "spell_attack":
            attack_bonus = action.spellAttackBonus
            if attack_bonus is None:
                attack_bonus = action.toHitBonus
            if attack_bonus is None and isinstance(spellcasting.get("attackBonus"), int):
                attack_bonus = spellcasting.get("attackBonus")
            damage_dice = action.damageDice or base_spell.damage_dice
            damage_bonus = action.damageBonus
            if not isinstance(attack_bonus, int):
                raise CombatServiceError(
                    "Spell attack is missing an attack bonus. "
                    "Set spellAttackBonus on the action or attackBonus on the creature."
                )
            if not isinstance(damage_dice, str) or not damage_dice.strip():
                raise CombatServiceError(
                    "Spell attack is missing structured damage dice. "
                    "Provide damageDice on the action or in the spell catalog."
                )
            if not damage_type:
                raise CombatServiceError(
                    "Spell attack is missing damageType. "
                    "Provide it in the catalog or override it on the action."
                )
            upcast_result = cls._apply_structured_spell_upcast(
                spell_level=base_spell.level,
                slot_level=action.castAtLevel,
                effect_kind="damage",
                effect_dice=damage_dice,
                effect_bonus=damage_bonus if isinstance(damage_bonus, int) else 0,
                upcast=structured_upcast,
            )
            resolved.update(
                {
                    "spellAttackBonus": attack_bonus,
                    "damageDice": upcast_result.get("effect_dice"),
                    "damageBonus": cls._safe_int(
                        upcast_result.get("effect_bonus"),
                        damage_bonus if isinstance(damage_bonus, int) else 0,
                    ),
                }
            )
            return resolved

        if action.kind == "saving_throw":
            save_dc = action.saveDc
            if save_dc is None and isinstance(spellcasting.get("saveDc"), int):
                save_dc = spellcasting.get("saveDc")
            damage_dice = action.damageDice or base_spell.damage_dice
            damage_bonus = action.damageBonus
            if not save_ability or not isinstance(save_dc, int) or save_dc <= 0:
                raise CombatServiceError(
                    "Saving throw action is missing saveAbility/saveDc. "
                    "Provide overrides or configure the creature spellcasting block."
                )
            if not isinstance(damage_dice, str) or not damage_dice.strip():
                raise CombatServiceError(
                    "Saving throw spell is missing structured damage dice. "
                    "Provide damageDice on the action or in the spell catalog."
                )
            if not damage_type:
                raise CombatServiceError(
                    "Saving throw action is missing damageType. "
                    "Provide it in the catalog or override it on the action."
                )
            upcast_result = cls._apply_structured_spell_upcast(
                spell_level=base_spell.level,
                slot_level=action.castAtLevel,
                effect_kind="damage",
                effect_dice=damage_dice,
                effect_bonus=damage_bonus if isinstance(damage_bonus, int) else 0,
                upcast=structured_upcast,
            )
            resolved.update(
                {
                    "saveAbility": save_ability,
                    "saveDc": save_dc,
                    "saveSuccessOutcome": (
                        cls._normalize_save_success_outcome(base_spell.save_success_outcome)
                        or "none"
                    ),
                    "damageDice": upcast_result.get("effect_dice"),
                    "damageBonus": cls._safe_int(
                        upcast_result.get("effect_bonus"),
                        damage_bonus if isinstance(damage_bonus, int) else 0,
                    ),
                }
            )
            return resolved

        if action.kind == "heal":
            heal_dice = action.healDice or base_spell.heal_dice
            heal_bonus = action.healBonus
            if not isinstance(heal_dice, str) or not heal_dice.strip():
                raise CombatServiceError(
                    "Heal spell is missing structured healing dice. "
                    "Provide healDice on the action or in the spell catalog."
                )
            upcast_result = cls._apply_structured_spell_upcast(
                spell_level=base_spell.level,
                slot_level=action.castAtLevel,
                effect_kind="healing",
                effect_dice=heal_dice,
                effect_bonus=heal_bonus if isinstance(heal_bonus, int) else 0,
                upcast=structured_upcast,
            )
            resolved.update(
                {
                    "healDice": upcast_result.get("effect_dice"),
                    "healBonus": cls._safe_int(
                        upcast_result.get("effect_bonus"),
                        heal_bonus if isinstance(heal_bonus, int) else 0,
                    ),
                }
            )
            return resolved

        raise CombatServiceError("Unsupported spell-based combat action kind.")

    @classmethod
    def _resolve_entity_combat_action(
        cls,
        db: Session,
        session_id: str,
        npc: CampaignEntity,
        action: CombatAction,
    ) -> dict:
        if action.kind == "utility":
            return {
                "name": action.name,
                "kind": action.kind,
                "description": action.description,
            }

        if action.kind == "weapon_attack":
            return cls._resolve_weapon_combat_action(db, session_id, action)

        if action.kind in ("spell_attack", "saving_throw"):
            return cls._resolve_spell_combat_action(db, session_id, npc, action)

        if action.kind == "heal":
            if action.spellCanonicalKey:
                return cls._resolve_spell_combat_action(db, session_id, npc, action)
            return {
                "name": action.name,
                "kind": action.kind,
                "description": action.description,
                "healDice": action.healDice,
                "healBonus": action.healBonus or 0,
            }

        raise CombatServiceError("Unsupported combat action kind.")

    @classmethod
    def _get_save_bonus(
        cls,
        db: Session,
        session_id: str,
        ref_id: str,
        kind: str,
        ability_name: str,
    ) -> int:
        normalized_ability = cls._normalize_ability_name(ability_name)
        if not normalized_ability:
            raise CombatServiceError("Invalid save ability")

        if kind == "player":
            target_model, *_ = cls._get_stats(db, ref_id, kind, session_id)
            data = cls._as_dict(target_model.state_json)
            abilities = cls._as_dict(data.get("abilities"))
            save_proficiencies = cls._as_dict(data.get("savingThrowProficiencies"))
            level = cls._safe_int(data.get("level"), 1)
            prof_bonus = floor((level - 1) / 4) + 2
            ability_score = cls._safe_int(abilities.get(normalized_ability), 10)
            save_bonus = cls._ability_modifier(ability_score)
            if save_proficiencies.get(normalized_ability) is True:
                save_bonus += prof_bonus
            return save_bonus

        session_entity, npc = cls._get_session_entity_and_campaign_entity(db, ref_id)
        overrides = cls._as_dict(session_entity.overrides)
        abilities = {
            ability_name: cls._get_entity_ability_score(cls._as_dict(npc.abilities), overrides, ability_name)
            for ability_name in cls._ENTITY_ABILITY_ALIASES
        }
        return resolve_entity_saving_throw_bonus(
            abilities,
            cls._get_entity_saving_throw_overrides(npc, overrides),
            normalized_ability,
        )
