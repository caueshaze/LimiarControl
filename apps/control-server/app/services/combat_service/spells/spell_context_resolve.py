from __future__ import annotations

from app.services.draconic_ancestry import resolve_elemental_affinity
from app.services.magic_item_effects import get_magic_item_spell_key

from ..exceptions import CombatServiceError, _parse_dice
from ..targeting_requirements import resolve_spell_targeting_requirements


class SpellContextResolveMixin:
    @classmethod
    def _resolve_spell_source_context(cls, db, session_id: str, attacker: dict, req, attacker_data: dict) -> dict:
        inventory_item = None
        source_item = None
        source_kind = "spellcasting"
        source_item_name = None
        ignore_components = False
        no_free_hand_required = False

        if isinstance(req.inventory_item_id, str) and req.inventory_item_id.strip():
            source_kind = "magic_item"
            inventory_item, source_item, magic_effect = cls._resolve_player_inventory_spell_item(
                db,
                session_id,
                player_user_id=str(attacker.get("actor_user_id") or attacker.get("ref_id") or "").strip(),
                inventory_item_id=req.inventory_item_id.strip(),
            )
            requested_canonical_key = get_magic_item_spell_key(source_item)
            if (
                isinstance(req.spell_canonical_key, str)
                and req.spell_canonical_key.strip()
                and requested_canonical_key
                and req.spell_canonical_key.strip().lower() != requested_canonical_key
            ):
                raise CombatServiceError("Selected spell does not match the magic item.", 400)
            source_item_name = source_item.name
            ignore_components = bool(magic_effect.get("ignoreComponents"))
            no_free_hand_required = bool(magic_effect.get("noFreeHandRequired"))
        else:
            requested_canonical_key = (
                req.spell_canonical_key.strip()
                if isinstance(req.spell_canonical_key, str) and req.spell_canonical_key.strip()
                else (
                    req.spell_id.strip()
                    if isinstance(req.spell_id, str) and req.spell_id.strip()
                    else None
                )
            )
        if not requested_canonical_key:
            raise CombatServiceError("Spell canonical key is required.", 400)

        return {
            "requested_canonical_key": requested_canonical_key,
            "inventory_item": inventory_item,
            "source_item": source_item,
            "source_item_name": source_item_name,
            "source_kind": source_kind,
            "ignore_components": ignore_components,
            "no_free_hand_required": no_free_hand_required,
        }

    @classmethod
    def _resolve_catalog_spell_context(cls, db, session_id: str, req, attacker_data: dict, source_context: dict) -> dict:
        requested_canonical_key = source_context["requested_canonical_key"]
        catalog_spell = cls._get_spell_catalog_entry_for_session(db, session_id, requested_canonical_key)
        spell_name = catalog_spell.name_pt or catalog_spell.name_en or requested_canonical_key

        if source_context["source_kind"] == "magic_item":
            player_spell = None
            spell_level = cls._safe_int(
                cls._as_dict(source_context["source_item"].magic_effect_json).get("castLevel"),
                catalog_spell.level,
            )
        else:
            player_spell = cls._resolve_player_spell_entry(
                attacker_data,
                spell_canonical_key=catalog_spell.canonical_key or requested_canonical_key,
                spell_name=spell_name,
                campaign_spell_id=req.campaign_spell_id or None,
            )
            spell_level = cls._safe_int(player_spell.get("level"), catalog_spell.level)
            if spell_level > 0 and player_spell.get("prepared") is False:
                raise CombatServiceError("Spell is not prepared.", 400)

        return {
            "catalog_spell": catalog_spell,
            "player_spell": player_spell,
            "spell_level": spell_level,
            "spell_name": spell_name,
        }

    @classmethod
    def _resolve_spell_mode_and_targeting(cls, req, catalog_spell, requested_canonical_key: str, spell_level: int, prof_bonus: int, spell_mod: int, source_kind: str) -> dict:
        catalog_resolution = getattr(catalog_spell, "resolution_type", None)
        catalog_spell_mode = cls._map_resolution_type_to_spell_mode(catalog_resolution)
        automation_default_mode = cls._spell_default_mode_override(
            catalog_spell.canonical_key or requested_canonical_key
        )
        requires_effect_payload = cls._spell_requires_effect_payload(
            catalog_spell.canonical_key or requested_canonical_key
        )
        catalog_save_ability = cls._normalize_ability_name(catalog_spell.saving_throw)
        legacy_mode = "heal" if req.is_heal else ("spell_attack" if req.is_attack else None)
        spell_mode = (
            req.spell_mode
            or automation_default_mode
            or catalog_spell_mode
            or legacy_mode
            or ("saving_throw" if catalog_save_ability else None)
        )
        if spell_mode not in ("spell_attack", "saving_throw", "direct_damage", "heal", "utility"):
            raise CombatServiceError("Spell cast mode is required for this spell.", 400)
        if spell_mode == "direct_damage" and catalog_save_ability:
            raise CombatServiceError(
                "This spell is structured as a saving throw spell. direct_damage is only allowed as an explicit fallback for spells without attack/save automation.",
                400,
            )
        targeting_requirements = resolve_spell_targeting_requirements(
            catalog_spell,
            spell_mode=spell_mode,
        )
        slot_level = None
        if spell_level > 0:
            if source_kind == "magic_item":
                slot_level = spell_level
            else:
                slot_level = req.slot_level or spell_level
                if slot_level < spell_level:
                    raise CombatServiceError("Spell slot level cannot be lower than the spell level.", 400)
        action_cost = cls._resolve_spell_action_cost(
            getattr(catalog_spell, "casting_time_type", None)
        )
        return {
            "action_cost": action_cost,
            "catalog_save_ability": catalog_save_ability,
            "legacy_expression": req.dice_expression.strip() if isinstance(req.dice_expression, str) and req.dice_expression.strip() else None,
            "requires_effect_payload": requires_effect_payload,
            "slot_level": slot_level,
            "spell_mode": spell_mode,
            "targeting_requirements": targeting_requirements,
        }

    @classmethod
    def _resolve_spell_effect_math(
        cls,
        req,
        catalog_spell,
        resolved_mode: dict,
        prof_bonus: int,
        spell_mod: int,
    ) -> dict:
        spell_mode = resolved_mode["spell_mode"]
        requires_effect_payload = resolved_mode["requires_effect_payload"]
        legacy_expression = resolved_mode["legacy_expression"]
        catalog_save_ability = resolved_mode["catalog_save_ability"]

        effect_kind = None if spell_mode == "utility" else ("healing" if spell_mode == "heal" else "damage")
        effect_dice = None
        effect_bonus = 0
        damage_type = None
        save_ability = None
        save_dc = None
        save_success_outcome = None
        attack_bonus = None

        if spell_mode == "heal":
            effect_dice = catalog_spell.heal_dice
            if not isinstance(effect_dice, str) or not effect_dice.strip():
                effect_dice = req.heal_dice or (legacy_expression if req.is_heal else None)
            effect_bonus = req.heal_bonus if isinstance(req.heal_bonus, int) else 0
        elif spell_mode != "utility":
            effect_dice = catalog_spell.damage_dice
            if not isinstance(effect_dice, str) or not effect_dice.strip():
                effect_dice = req.damage_dice or (legacy_expression if not req.is_heal else None)
            effect_bonus = req.damage_bonus if isinstance(req.damage_bonus, int) else 0
            should_require_damage_type = bool(requires_effect_payload or effect_dice or effect_bonus > 0)
            damage_type = cls._normalize_damage_type(catalog_spell.damage_type or req.damage_type)
            if should_require_damage_type and not damage_type:
                raise CombatServiceError("Spell damage type is missing a structured value.", 400)

        if isinstance(effect_dice, str):
            effect_dice = effect_dice.strip() or None
        if effect_dice:
            count, sides, _ = _parse_dice(effect_dice)
            if count <= 0 or sides <= 0:
                raise CombatServiceError("Spell effect dice must use a valid dice expression.", 400)
        elif spell_mode != "utility" and requires_effect_payload and effect_bonus <= 0:
            raise CombatServiceError("Spell effect is missing structured dice or a fixed bonus.", 400)

        if spell_mode == "spell_attack":
            attack_bonus = req.spell_attack_bonus if isinstance(req.spell_attack_bonus, int) else None
            if not isinstance(attack_bonus, int):
                attack_bonus = spell_mod + prof_bonus
        elif spell_mode == "saving_throw":
            save_ability = cls._normalize_ability_name(req.save_ability or catalog_save_ability)
            save_dc = req.save_dc if isinstance(req.save_dc, int) else None
            if not isinstance(save_dc, int):
                save_dc = 8 + prof_bonus + spell_mod
            save_success_outcome = (
                cls._normalize_save_success_outcome(catalog_spell.save_success_outcome)
                or "none"
            )
            if not save_ability or save_dc <= 0:
                raise CombatServiceError("Saving throw spells require save ability and save DC.", 400)

        return {
            "attack_bonus": attack_bonus,
            "damage_type": damage_type,
            "effect_bonus": effect_bonus,
            "effect_dice": effect_dice,
            "effect_kind": effect_kind,
            "save_ability": save_ability,
            "save_dc": save_dc,
            "save_success_outcome": save_success_outcome,
        }

    @classmethod
    def _resolve_upcast_and_affinity(
        cls,
        attacker_data: dict,
        catalog_spell,
        damage_type: str | None,
        effect_bonus: int,
        effect_dice: str | None,
        effect_kind: str | None,
        slot_level: int | None,
        spell_level: int,
    ) -> dict:
        structured_upcast = cls._get_structured_spell_upcast(
            getattr(catalog_spell, "upcast_json", None)
        )
        upcast_result = cls._apply_structured_spell_upcast(
            spell_level=spell_level,
            slot_level=slot_level,
            effect_kind=effect_kind,
            effect_dice=effect_dice,
            effect_bonus=effect_bonus,
            upcast=structured_upcast,
        )
        elemental_affinity = resolve_elemental_affinity(attacker_data, damage_type)
        return {
            "elemental_affinity": elemental_affinity,
            "structured_upcast": structured_upcast,
            "upcast_result": upcast_result,
        }

    @classmethod
    def _build_spell_context_response(
        cls,
        *,
        catalog_spell,
        source_context: dict,
        resolved_mode: dict,
        resolved_math: dict,
        resolved_upcast: dict,
    ) -> dict:
        upcast_result = resolved_upcast["upcast_result"]
        return {
            "spell_name": source_context["spell_name"],
            "spell_canonical_key": catalog_spell.canonical_key or source_context["requested_canonical_key"],
            "spell_mode": resolved_mode["spell_mode"],
            "target_mode": getattr(catalog_spell, "target_mode", None),
            "range_meters": getattr(catalog_spell, "range_meters", None),
            "area_size_meters": getattr(catalog_spell, "area_size_meters", None),
            "requires_target_sight": resolved_mode["targeting_requirements"].requires_target_sight,
            "requires_target_effect": resolved_mode["targeting_requirements"].requires_target_effect,
            "requires_point_sight": resolved_mode["targeting_requirements"].requires_point_sight,
            "requires_point_effect": resolved_mode["targeting_requirements"].requires_point_effect,
            "effect_kind": resolved_math["effect_kind"],
            "effect_dice": upcast_result["effect_dice"]
            if isinstance(upcast_result.get("effect_dice"), str) or upcast_result.get("effect_dice") is None
            else resolved_math["effect_dice"],
            "effect_bonus": cls._safe_int(upcast_result.get("effect_bonus"), resolved_math["effect_bonus"]),
            "damage_type": resolved_math["damage_type"],
            "save_ability": resolved_math["save_ability"],
            "save_dc": resolved_math["save_dc"],
            "save_success_outcome": resolved_math["save_success_outcome"],
            "cover_applies_to_save": getattr(catalog_spell, "cover_applies_to_save", None),
            "attack_bonus": resolved_math["attack_bonus"],
            "slot_level": resolved_mode["slot_level"],
            "action_cost": resolved_mode["action_cost"],
            "upcast": resolved_upcast["structured_upcast"],
            "upcast_applied": bool(upcast_result.get("upcast_applied")),
            "upcast_levels": cls._safe_int(upcast_result.get("upcast_levels"), 0),
            "elemental_affinity_eligible": bool(resolved_upcast["elemental_affinity"].get("eligible")),
            "elemental_affinity_damage_type": resolved_upcast["elemental_affinity"].get("damageType"),
            "elemental_affinity_bonus": resolved_upcast["elemental_affinity"].get("bonus"),
            "source_kind": source_context["source_kind"],
            "source_item_name": source_context["source_item_name"],
            "inventory_item": source_context["inventory_item"],
            "inventory_item_id": getattr(source_context["inventory_item"], "id", None),
            "ignore_components": source_context["ignore_components"],
            "no_free_hand_required": source_context["no_free_hand_required"],
            "source_item": source_context["source_item"],
        }

    @classmethod
    def _resolve_player_spell_context(
        cls,
        db,
        session_id: str,
        attacker: dict,
        attacker_model,
        req,
    ) -> dict:
        attacker_data = cls._as_dict(attacker_model.state_json)
        source_context = cls._resolve_spell_source_context(
            db, session_id, attacker, req, attacker_data
        )
        catalog_context = cls._resolve_catalog_spell_context(
            db, session_id, req, attacker_data, source_context
        )
        source_context["spell_name"] = catalog_context["spell_name"]
        _, _, _, _, prof_bonus, spell_mod = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        resolved_mode = cls._resolve_spell_mode_and_targeting(
            req,
            catalog_context["catalog_spell"],
            source_context["requested_canonical_key"],
            catalog_context["spell_level"],
            prof_bonus,
            spell_mod,
            source_context["source_kind"],
        )
        resolved_math = cls._resolve_spell_effect_math(
            req,
            catalog_context["catalog_spell"],
            resolved_mode,
            prof_bonus,
            spell_mod,
        )
        resolved_upcast = cls._resolve_upcast_and_affinity(
            attacker_data,
            catalog_context["catalog_spell"],
            resolved_math["damage_type"],
            resolved_math["effect_bonus"],
            resolved_math["effect_dice"],
            resolved_math["effect_kind"],
            resolved_mode["slot_level"],
            catalog_context["spell_level"],
        )
        return cls._build_spell_context_response(
            catalog_spell=catalog_context["catalog_spell"],
            source_context=source_context,
            resolved_mode=resolved_mode,
            resolved_math=resolved_math,
            resolved_upcast=resolved_upcast,
        )
