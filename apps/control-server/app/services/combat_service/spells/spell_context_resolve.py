from __future__ import annotations

from app.schemas.base_spell import SpellVariant, SpellVariantSummary
from app.services.draconic_ancestry import resolve_elemental_affinity
from app.services.magic_item_effects import get_magic_item_spell_key
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics

from ..exceptions import CombatServiceError, _parse_dice
from ..targeting_requirements import (
    TargetingRequirements,
    resolve_spell_targeting_requirements,
)


class SpellContextResolveMixin:
    _PRODUCE_FLAME_UTILITY_META = {
        "type": "produce_flame",
        "creates_light": True,
        "bright_light_meters": 3,
        "dim_light_meters": 3,
        "can_throw": True,
        "throw_range_meters": 9,
        "throw_attack_type": "ranged_spell",
    }

    _NARRATIVE_UTILITY_META_BY_SPELL: dict[str, dict] = {
        "thaumaturgy": {
            "type": "narrative_effect",
            "subtype": "thaumaturgy",
            "mechanical": False,
            "narrative": True,
            "allowedEffects": sorted([
                "alter_eyes",
                "booming_voice",
                "flame_omen",
                "harmless_tremor",
                "instantaneous_sound",
                "open_or_close_unlocked_door",
            ]),
        },
        "comprehend_languages": {
            "type": "narrative_effect",
            "subtype": "comprehend_languages",
            "mechanical": False,
            "narrative": True,
            "durationSeconds": 3600,
            "understandsSpokenLanguages": True,
            "understandsWrittenLanguages": True,
            "requiresTouchForWrittenText": True,
            "literalMeaningOnly": True,
            "deciphersSecretMessages": False,
        },
        "detect_poison_disease": {
            "type": "narrative_effect",
            "subtype": "detect_poison_disease",
            "mechanical": False,
            "narrative": True,
            "durationSeconds": 600,
            "radiusMeters": 9,
            "detectsPoisons": True,
            "detectsPoisonousCreatures": True,
            "detectsDiseases": True,
            "canIdentifyPoisonOrDiseaseWithAction": True,
            "blockedBy": {
                "stoneCm": 30,
                "commonMetalCm": 2.5,
                "leadSheet": True,
                "woodOrEarthMeters": 1,
            },
        },
        "detect_evil_and_good": {
            "type": "narrative_detection",
            "subtype": "detect_evil_and_good",
            "mechanical": False,
            "narrative": True,
            "durationSeconds": 600,
            "radiusMeters": 9,
            "detectsCreatureTypes": [
                "aberration", "celestial", "elemental",
                "fey", "fiend", "undead",
            ],
            "detectsConsecratedOrDesecrated": True,
            "blockedBy": {
                "stoneCm": 30,
                "commonMetalCm": 2.5,
                "leadSheet": True,
                "woodOrEarthMeters": 1,
            },
        },
    }

    @classmethod
    def _normalize_spell_variants(cls, raw_variants: object) -> list[SpellVariant]:
        if not isinstance(raw_variants, list):
            return []
        normalized: list[SpellVariant] = []
        for entry in raw_variants:
            if not isinstance(entry, dict):
                continue
            normalized.append(SpellVariant.model_validate(entry))
        return normalized

    @classmethod
    def _build_spell_variant_summaries(cls, raw_variants: object) -> list[dict] | None:
        variants = cls._normalize_spell_variants(raw_variants)
        if not variants:
            return None
        summaries: list[dict] = []
        for variant in variants:
            label = variant.labelPt or variant.labelEn or variant.key
            description = variant.descriptionPt or variant.descriptionEn
            summaries.append(
                SpellVariantSummary(
                    key=variant.key,
                    label=label,
                    description=description,
                    manualNotes=variant.manualNotes,
                ).model_dump(mode="json")
            )
        return summaries

    @classmethod
    def _validate_selected_variant_key(
        cls,
        *,
        catalog_spell,
        variant_key: str | None,
    ) -> str | None:
        if not isinstance(variant_key, str) or not variant_key.strip():
            return None
        normalized_key = variant_key.strip()
        variants = cls._normalize_spell_variants(getattr(catalog_spell, "variants_json", None))
        if not variants:
            raise CombatServiceError("This spell does not define variants.", 400)
        if not any(variant.key == normalized_key for variant in variants):
            raise CombatServiceError(
                f"Unknown spell variant '{normalized_key}' for this spell.",
                400,
            )
        return normalized_key

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
            "selected_variant_key": cls._validate_selected_variant_key(
                catalog_spell=catalog_spell,
                variant_key=getattr(req, "variant_key", None),
            ),
        }

    @classmethod
    def _resolve_spell_mode_and_targeting(
        cls,
        req,
        catalog_spell,
        requested_canonical_key: str,
        spell_level: int,
        prof_bonus: int,
        spell_mod: int,
        source_kind: str,
        attacker_data: dict,
    ) -> dict:
        catalog_resolution = getattr(catalog_spell, "resolution_type", None)
        catalog_spell_mode = cls._map_resolution_type_to_spell_mode(catalog_resolution)
        targeting_semantics = resolve_spell_targeting_semantics(catalog_spell)
        normalized_key = cls._normalize_lookup(
            catalog_spell.canonical_key or requested_canonical_key
        ).replace(" ", "_")
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
            or ("spell_attack" if targeting_semantics.attack_type in ("melee_spell", "ranged_spell") else None)
            or ("utility" if targeting_semantics.effect_timing in ("persistent", "triggered") else None)
            or automation_default_mode
            or ("saving_throw" if catalog_save_ability else None)
            or catalog_spell_mode
            or legacy_mode
        )
        if spell_mode not in ("spell_attack", "saving_throw", "direct_damage", "heal", "utility", "teleport"):
            raise CombatServiceError("Spell cast mode is required for this spell.", 400)
        if normalized_key == "produce_flame":
            if spell_mode == "spell_attack":
                targeting_semantics = targeting_semantics.__class__(
                    selection_type="creature",
                    origin_type="caster",
                    target_anchor="selected_target",
                    attack_type="ranged_spell",
                    range_kind="distance",
                    effect_timing="immediate",
                )
            else:
                targeting_semantics = targeting_semantics.__class__(
                    selection_type="self",
                    origin_type="caster",
                    target_anchor="caster",
                    attack_type="none",
                    range_kind="self",
                    effect_timing="persistent",
                )
        if spell_mode == "direct_damage" and catalog_save_ability:
            raise CombatServiceError(
                "This spell is structured as a saving throw spell. direct_damage is only allowed as an explicit fallback for spells without attack/save automation.",
                400,
            )
        targeting_requirements = resolve_spell_targeting_requirements(
            catalog_spell,
            spell_mode=spell_mode,
        )
        if normalized_key == "produce_flame":
            if spell_mode == "spell_attack":
                targeting_requirements = TargetingRequirements(
                    requires_target_sight=True,
                    requires_target_effect=True,
                    requires_point_sight=False,
                    requires_point_effect=False,
                )
            else:
                targeting_requirements = TargetingRequirements(
                    requires_target_sight=False,
                    requires_target_effect=False,
                    requires_point_sight=False,
                    requires_point_effect=False,
                )
        slot_level = None
        if spell_level > 0:
            if source_kind == "magic_item":
                slot_level = spell_level
            else:
                slot_level = req.slot_level or spell_level
                if slot_level < spell_level:
                    raise CombatServiceError("Spell slot level cannot be lower than the spell level.", 400)
                spellcasting = cls._as_dict(attacker_data.get("spellcasting"))
                slots = cls._as_dict(spellcasting.get("slots"))
                slot_data = cls._as_dict(slots.get(str(slot_level)))
                if cls._safe_int(slot_data.get("max"), 0) <= 0:
                    raise CombatServiceError(
                        f"Spell slot level {slot_level} is not available for this caster.",
                        400,
                    )
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
            "targeting_semantics": targeting_semantics,
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

        effect_kind = None if spell_mode in ("utility", "teleport") else ("healing" if spell_mode == "heal" else "damage")
        effect_dice = None
        effect_bonus = 0
        damage_type = None
        save_ability = None
        save_dc = None
        save_success_outcome = None
        attack_miss_outcome = None
        attack_bonus = None

        if spell_mode == "heal":
            effect_dice = catalog_spell.heal_dice
            if not isinstance(effect_dice, str) or not effect_dice.strip():
                effect_dice = req.heal_dice or (legacy_expression if req.is_heal else None)
            effect_bonus = req.heal_bonus if isinstance(req.heal_bonus, int) else 0
        elif (
            spell_mode == "utility"
            and cls._normalize_lookup(getattr(catalog_spell, "canonical_key", None)).replace(" ", "_")
            == "produce_flame"
        ):
            effect_dice = catalog_spell.damage_dice
            damage_type = catalog_spell.damage_type
        elif spell_mode not in ("utility", "teleport"):
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
            _, count, sides, _ = _parse_dice(effect_dice)
            if count <= 0 or sides <= 0:
                raise CombatServiceError("Spell effect dice must use a valid dice expression.", 400)
        elif spell_mode not in ("utility", "teleport") and requires_effect_payload and effect_bonus <= 0:
            raise CombatServiceError("Spell effect is missing structured dice or a fixed bonus.", 400)

        if spell_mode == "spell_attack":
            attack_bonus = req.spell_attack_bonus if isinstance(req.spell_attack_bonus, int) else None
            if not isinstance(attack_bonus, int):
                attack_bonus = spell_mod + prof_bonus
            attack_miss_outcome = cls._normalize_attack_miss_outcome(
                getattr(catalog_spell, "attack_miss_outcome", None)
            ) or "none"
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
            "attack_miss_outcome": attack_miss_outcome,
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
        caster_level: int | None,
    ) -> dict:
        structured_upcast = cls._get_structured_spell_upcast(
            getattr(catalog_spell, "upcast_json", None)
        ) if spell_level > 0 else None
        structured_cantrip_scaling = cls._get_structured_cantrip_scaling(
            getattr(catalog_spell, "cantrip_scaling_json", None)
        )
        cantrip_result = cls._apply_character_level_cantrip_scaling(
            spell_level=spell_level,
            caster_level=caster_level,
            effect_dice=effect_dice,
            cantrip_scaling=structured_cantrip_scaling,
        )
        upcast_result = cls._apply_structured_spell_upcast(
            spell_level=spell_level,
            slot_level=slot_level,
            effect_kind=effect_kind,
            effect_dice=cantrip_result["effect_dice"],
            effect_bonus=effect_bonus,
            upcast=structured_upcast,
        )
        base_effect_instance_count: int | None = None
        base_effect_instance_dice: str | None = None
        if isinstance(structured_upcast, dict) and structured_upcast.get("mode") == "additional_effect_instances":
            raw_base = structured_upcast.get("baseEffectInstances")
            base_effect_instance_count = raw_base if isinstance(raw_base, int) and raw_base >= 1 else None
            inst_dice = structured_upcast.get("dice")
            base_effect_instance_dice = inst_dice if isinstance(inst_dice, str) else None
            if base_effect_instance_count is None and base_effect_instance_dice and effect_dice:
                # Fallback: derive base count from aggregate/instance dice ratio.
                # TODO: prefer explicit baseEffectInstances in seed over this derivation.
                _, inst_c, inst_s, inst_mod = _parse_dice(base_effect_instance_dice)
                _, base_c, base_s, base_mod = _parse_dice(effect_dice)
                if (
                    inst_c > 0 and inst_s == base_s and base_c > 0
                    and base_c % inst_c == 0
                    and (inst_mod == 0 or base_mod == (base_c // inst_c) * inst_mod)
                ):
                    base_effect_instance_count = base_c // inst_c
        elemental_affinity = resolve_elemental_affinity(attacker_data, damage_type)
        return {
            "elemental_affinity": elemental_affinity,
            "cantrip_scaling": structured_cantrip_scaling,
            "cantrip_instance_count": cantrip_result["cantrip_instance_count"],
            "cantrip_instance_dice": cantrip_result["cantrip_instance_dice"],
            "base_effect_instance_count": base_effect_instance_count,
            "base_effect_instance_dice": base_effect_instance_dice,
            "structured_upcast": structured_upcast,
            "upcast_result": upcast_result,
        }

    @classmethod
    def _build_temp_hp_preview(cls, catalog_spell, upcast_result: dict) -> dict | None:
        effects_list = getattr(catalog_spell, "effects_json", None) or []
        temp_hp_effects = [
            e for e in effects_list
            if isinstance(e, dict) and e.get("type") == "grant_temp_hp"
        ]
        if not temp_hp_effects:
            return None
        base_dice = (temp_hp_effects[0].get("params") or {}).get("dice", "")
        if not base_dice:
            return None
        upcast_bonus_val = cls._safe_int(upcast_result.get("effect_bonus"), 0)
        if upcast_bonus_val > 0:
            _, count, sides, mod = _parse_dice(base_dice)
            total_mod = mod + upcast_bonus_val
            resolved_formula = cls._build_dice_expression(count, sides, total_mod) or base_dice
        else:
            resolved_formula = base_dice
        return {
            "base_dice": base_dice,
            "effect_bonus": upcast_bonus_val,
            "resolved_formula": resolved_formula,
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
        spell_level: int,
        caster_spell_mod: int = 0,
    ) -> dict:
        upcast_result = resolved_upcast["upcast_result"]
        base_max_targets = getattr(catalog_spell, "max_targets", None)
        upcast_added_instances = cls._safe_int(
            upcast_result.get("upcast_added_instances"), 0
        )

        temp_hp_preview = cls._build_temp_hp_preview(catalog_spell, upcast_result)
        effective_max_targets = (
            base_max_targets + upcast_added_instances
            if isinstance(base_max_targets, int)
            else None
        )
        cantrip_instance_count = resolved_upcast.get("cantrip_instance_count")
        cantrip_instance_dice = resolved_upcast.get("cantrip_instance_dice")
        base_effect_instance_count = resolved_upcast.get("base_effect_instance_count")
        base_effect_instance_dice = resolved_upcast.get("base_effect_instance_dice")
        if cantrip_instance_count is not None:
            effect_instance_count = cantrip_instance_count
            effect_instance_dice = cantrip_instance_dice
        elif base_effect_instance_count is not None:
            effect_instance_count = base_effect_instance_count + upcast_added_instances
            effect_instance_dice = base_effect_instance_dice
        else:
            effect_instance_count = 1
            effect_instance_dice = None
        spell_key = cls._normalize_lookup(catalog_spell.canonical_key).replace(" ", "_")
        range_meters = getattr(catalog_spell, "range_meters", None)
        target_type = getattr(catalog_spell, "target_type", None)
        if spell_key == "produce_flame" and resolved_mode["spell_mode"] == "spell_attack":
            range_meters = 9
            target_type = "ranged"
        delayed_damage_preview = None
        effects = getattr(catalog_spell, "effects_json", None)
        if isinstance(effects, list):
            for effect in effects:
                if not isinstance(effect, dict) or effect.get("type") != "delayed_damage":
                    continue
                params = effect.get("params")
                if not isinstance(params, dict):
                    continue
                base_delayed_dice = params.get("dice")
                if not isinstance(base_delayed_dice, str) or not base_delayed_dice.strip():
                    continue
                delayed_damage_preview = base_delayed_dice.strip()
                structured_upcast = resolved_upcast.get("structured_upcast")
                upcast_levels = cls._safe_int(upcast_result.get("upcast_levels"), 0)
                if isinstance(structured_upcast, dict) and upcast_levels > 0:
                    upcast_dice = structured_upcast.get("dice")
                    per_level = structured_upcast.get("perLevel")
                    repeats = upcast_levels * (
                        per_level if isinstance(per_level, int) and per_level > 0 else 1
                    )
                    if isinstance(upcast_dice, str) and upcast_dice.strip() and repeats > 0:
                        delayed_damage_preview = cls._merge_dice_expressions(
                            delayed_damage_preview,
                            upcast_dice,
                            repeats=repeats,
                        )
                break
        return {
            "spell_name": source_context["spell_name"],
            "spell_canonical_key": catalog_spell.canonical_key or source_context["requested_canonical_key"],
            "spell_level": spell_level,
            "spell_mode": resolved_mode["spell_mode"],
            "target_type": target_type,
            "max_targets": effective_max_targets,
            "base_max_targets": base_max_targets,
            "selection_type": resolved_mode["targeting_semantics"].selection_type,
            "origin_type": resolved_mode["targeting_semantics"].origin_type,
            "target_anchor": resolved_mode["targeting_semantics"].target_anchor,
            "attack_type": resolved_mode["targeting_semantics"].attack_type,
            "range_kind": resolved_mode["targeting_semantics"].range_kind,
            "effect_timing": resolved_mode["targeting_semantics"].effect_timing,
            "area_shape": getattr(catalog_spell, "area_shape", None),
            "range_meters": range_meters,
            "radius_meters": getattr(catalog_spell, "radius_meters", None),
            "length_meters": getattr(catalog_spell, "length_meters", None),
            "side_meters": getattr(catalog_spell, "side_meters", None),
            "duration": getattr(catalog_spell, "duration", None),
            "concentration": getattr(catalog_spell, "concentration", None),
            "requires_target_sight": resolved_mode["targeting_requirements"].requires_target_sight,
            "requires_target_hearing": getattr(catalog_spell, "requires_target_hearing", None),
            "requires_target_effect": resolved_mode["targeting_requirements"].requires_target_effect,
            "requires_point_sight": resolved_mode["targeting_requirements"].requires_point_sight,
            "requires_point_effect": resolved_mode["targeting_requirements"].requires_point_effect,
            "effect_kind": resolved_math["effect_kind"],
            "effect_dice": upcast_result["effect_dice"]
            if isinstance(upcast_result.get("effect_dice"), str) or upcast_result.get("effect_dice") is None
            else resolved_math["effect_dice"],
            "effect_bonus": cls._safe_int(upcast_result.get("effect_bonus"), resolved_math["effect_bonus"]),
            "temp_hp_preview": temp_hp_preview,
            "damage_type": resolved_math["damage_type"],
            "save_ability": resolved_math["save_ability"],
            "save_dc": resolved_math["save_dc"],
            "save_success_outcome": resolved_math["save_success_outcome"],
            "attack_miss_outcome": resolved_math["attack_miss_outcome"],
            "effects": getattr(catalog_spell, "effects_json", None),
            "delayed_damage_preview": delayed_damage_preview,
            "attack_advantage_condition": getattr(catalog_spell, "attack_advantage_condition_json", None),
            "on_end_effects": getattr(catalog_spell, "on_end_effects_json", None),
            "variant_definitions": getattr(catalog_spell, "variants_json", None),
            "variants": cls._build_spell_variant_summaries(
                getattr(catalog_spell, "variants_json", None)
            ),
            "selected_variant_key": source_context.get("selected_variant_key"),
            "target_variant_assignments": [
                assignment.model_dump(mode="json")
                for assignment in (getattr(source_context.get("request"), "target_variant_assignments", None) or [])
            ]
            or None,
            "persistent_area": getattr(catalog_spell, "persistent_area_json", None),
            "cover_applies_to_save": getattr(catalog_spell, "cover_applies_to_save", None),
            "attack_bonus": resolved_math["attack_bonus"],
            "slot_level": resolved_mode["slot_level"],
            "action_cost": resolved_mode["action_cost"],
            "upcast": resolved_upcast["structured_upcast"],
            "cantrip_scaling": resolved_upcast["cantrip_scaling"],
            "upcast_applied": bool(upcast_result.get("upcast_applied")),
            "upcast_levels": cls._safe_int(upcast_result.get("upcast_levels"), 0),
            "upcast_added_instances": upcast_added_instances,
            "upcast_instance_effect_dice": upcast_result.get("upcast_instance_effect_dice"),
            "effect_instance_count": effect_instance_count,
            "effect_instance_dice": effect_instance_dice,
            "base_effect_instance_count": base_effect_instance_count,
            "utility": cls._PRODUCE_FLAME_UTILITY_META if spell_key == "produce_flame"
                       else cls._NARRATIVE_UTILITY_META_BY_SPELL.get(spell_key),
            "throw_attack": (
                {
                    "attack_type": "ranged_spell",
                    "range_meters": 9,
                    "damage_preview": {
                        "dice": upcast_result["effect_dice"]
                        if isinstance(upcast_result.get("effect_dice"), str)
                        else resolved_math["effect_dice"],
                        "damage_type": resolved_math["damage_type"] or "Fire",
                    },
                }
                if spell_key == "produce_flame"
                else None
            ),
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
            "caster_spell_mod": caster_spell_mod,
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
        source_context["request"] = req
        catalog_context = cls._resolve_catalog_spell_context(
            db, session_id, req, attacker_data, source_context
        )
        source_context["spell_name"] = catalog_context["spell_name"]
        source_context["selected_variant_key"] = catalog_context["selected_variant_key"]
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
            attacker_data,
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
            cls._safe_int(attacker_data.get("level"), 1),
        )
        return cls._build_spell_context_response(
            catalog_spell=catalog_context["catalog_spell"],
            source_context=source_context,
            resolved_mode=resolved_mode,
            resolved_math=resolved_math,
            resolved_upcast=resolved_upcast,
            spell_level=catalog_context["spell_level"],
            caster_spell_mod=spell_mod,
        )
