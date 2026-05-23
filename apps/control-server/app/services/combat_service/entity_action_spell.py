from __future__ import annotations

from .exceptions import CombatServiceError


class CombatEntitySpellActionMixin:
    @classmethod
    def _resolve_spell_combat_action(cls, db, session_id: str, npc, action) -> dict:
        from . import entity_actions as entity_actions_module

        if not action.spellCanonicalKey:
            raise CombatServiceError("Automated spell actions require spellCanonicalKey.")
        base_spell = cls._get_spell_catalog_entry_for_session(db, session_id, action.spellCanonicalKey)
        if base_spell is None:
            base_spell = entity_actions_module.get_base_spell_by_canonical_key(
                db=db,
                system=cls._get_campaign_system_for_session(db, session_id),
                canonical_key=action.spellCanonicalKey,
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
            "rangeMeters": action.rangeMeters if action.rangeMeters is not None else base_spell.range_meters,
            "damageType": damage_type,
        }
        structured_upcast = cls._get_structured_spell_upcast(getattr(base_spell, "upcast_json", None))
        if action.kind == "spell_attack":
            attack_bonus = action.spellAttackBonus
            if attack_bonus is None:
                attack_bonus = action.toHitBonus
            if attack_bonus is None and isinstance(spellcasting.get("attackBonus"), int):
                attack_bonus = spellcasting.get("attackBonus")
            damage_dice = action.damageDice or base_spell.damage_dice
            damage_bonus = action.damageBonus
            if not isinstance(attack_bonus, int):
                raise CombatServiceError("Spell attack is missing an attack bonus. Set spellAttackBonus on the action or attackBonus on the creature.")
            if not isinstance(damage_dice, str) or not damage_dice.strip():
                raise CombatServiceError("Spell attack is missing structured damage dice. Provide damageDice on the action or in the spell catalog.")
            if not damage_type:
                raise CombatServiceError("Spell attack is missing damageType. Provide it in the catalog or override it on the action.")
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
                    "attackMissOutcome": (
                        cls._normalize_attack_miss_outcome(
                            getattr(base_spell, "attack_miss_outcome", None)
                        )
                        or "none"
                    ),
                }
            )
            return resolved
        if action.kind == "saving_throw":
            save_dc = action.saveDc if action.saveDc is not None else (spellcasting.get("saveDc") if isinstance(spellcasting.get("saveDc"), int) else None)
            damage_dice = action.damageDice or base_spell.damage_dice
            damage_bonus = action.damageBonus
            if not save_ability or not isinstance(save_dc, int) or save_dc <= 0:
                raise CombatServiceError("Saving throw action is missing saveAbility/saveDc. Provide overrides or configure the creature spellcasting block.")
            if not isinstance(damage_dice, str) or not damage_dice.strip():
                raise CombatServiceError("Saving throw spell is missing structured damage dice. Provide damageDice on the action or in the spell catalog.")
            if not damage_type:
                raise CombatServiceError("Saving throw action is missing damageType. Provide it in the catalog or override it on the action.")
            upcast_result = cls._apply_structured_spell_upcast(
                spell_level=base_spell.level,
                slot_level=action.castAtLevel,
                effect_kind="damage",
                effect_dice=damage_dice,
                effect_bonus=damage_bonus if isinstance(damage_bonus, int) else 0,
                upcast=structured_upcast,
            )
            resolved.update({
                "saveAbility": save_ability,
                "saveDc": save_dc,
                "saveSuccessOutcome": cls._normalize_save_success_outcome(base_spell.save_success_outcome) or "none",
                "damageDice": upcast_result.get("effect_dice"),
                "damageBonus": cls._safe_int(upcast_result.get("effect_bonus"), damage_bonus if isinstance(damage_bonus, int) else 0),
                "coverAppliesToSave": getattr(base_spell, "cover_applies_to_save", None),
            })
            return resolved
        if action.kind == "heal":
            heal_dice = action.healDice or base_spell.heal_dice
            heal_bonus = action.healBonus
            if not isinstance(heal_dice, str) or not heal_dice.strip():
                raise CombatServiceError("Heal spell is missing structured healing dice. Provide healDice on the action or in the spell catalog.")
            upcast_result = cls._apply_structured_spell_upcast(
                spell_level=base_spell.level,
                slot_level=action.castAtLevel,
                effect_kind="healing",
                effect_dice=heal_dice,
                effect_bonus=heal_bonus if isinstance(heal_bonus, int) else 0,
                upcast=structured_upcast,
            )
            resolved.update({"healDice": upcast_result.get("effect_dice"), "healBonus": cls._safe_int(upcast_result.get("effect_bonus"), heal_bonus if isinstance(heal_bonus, int) else 0)})
            return resolved
        raise CombatServiceError("Unsupported spell-based combat action kind.")
