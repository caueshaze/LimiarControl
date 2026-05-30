from __future__ import annotations

from .exceptions import CombatServiceError, _parse_dice
from .host_protocol import CombatServiceHostProtocol
from .spell_automation_metadata import _RESOLUTION_TYPE_TO_SPELL_MODE as _SPELL_MODE_MAP


class CombatSpellDiceMathMixin(CombatServiceHostProtocol):
    _SAVE_SUCCESS_OUTCOME_VALUES = {"none", "half_damage"}
    _ATTACK_MISS_OUTCOME_VALUES = {"none", "half_damage"}
    _COMBAT_SPELL_ACTION_COSTS = {"action", "bonus_action", "reaction"}
    _RESOLUTION_TYPE_TO_SPELL_MODE: dict[str, str] = dict(_SPELL_MODE_MAP)

    @classmethod
    def _map_resolution_type_to_spell_mode(cls, resolution_type: object) -> str | None:
        if not isinstance(resolution_type, str):
            return None
        return cls._RESOLUTION_TYPE_TO_SPELL_MODE.get(resolution_type)

    @classmethod
    def _resolve_spell_action_cost(cls, casting_time_type: object) -> str:
        normalized = cls._normalize_lookup(casting_time_type).replace(" ", "_")
        if not normalized:
            return "action"
        if normalized in cls._COMBAT_SPELL_ACTION_COSTS:
            return normalized
        raise CombatServiceError(
            "This spell cannot be cast through the combat action flow because its casting time is longer than a combat action.",
            400,
        )

    @classmethod
    def _get_structured_spell_upcast(cls, raw_upcast: object) -> dict | None:
        if not isinstance(raw_upcast, dict):
            return None
        mode = raw_upcast.get("mode")
        if not isinstance(mode, str) or not mode.strip():
            return None
        normalized: dict[str, object] = {"mode": mode.strip()}
        dice = raw_upcast.get("dice")
        if isinstance(dice, str) and dice.strip():
            normalized["dice"] = dice.strip()
        flat = raw_upcast.get("flat")
        if isinstance(flat, int):
            normalized["flat"] = flat
        per_level = raw_upcast.get("perLevel")
        if isinstance(per_level, int) and per_level > 0:
            normalized["perLevel"] = per_level
        max_level = raw_upcast.get("maxLevel")
        if isinstance(max_level, int) and max_level > 0:
            normalized["maxLevel"] = max_level
        base_instances = raw_upcast.get("baseEffectInstances")
        if isinstance(base_instances, int) and base_instances >= 1:
            normalized["baseEffectInstances"] = base_instances
        level_step = raw_upcast.get("levelStep")
        if isinstance(level_step, int) and level_step >= 2:
            normalized["levelStep"] = level_step
        return normalized

    @classmethod
    def _get_structured_cantrip_scaling(cls, raw_scaling: object) -> dict | None:
        if not isinstance(raw_scaling, dict):
            return None
        # Accept both legacy "mode" and new "scalingMode"
        scaling_mode = raw_scaling.get("scalingMode") or raw_scaling.get("mode")
        if scaling_mode != "character_level":
            return None
        thresholds = raw_scaling.get("thresholds")
        if not isinstance(thresholds, list):
            return None

        # Infer scalingEffectType
        raw_effect_type = raw_scaling.get("scalingEffectType")
        if not isinstance(raw_effect_type, str):
            has_instances = any(
                isinstance(t, dict) and ("instances" in t or "instanceDamage" in t)
                for t in thresholds
            )
            raw_effect_type = "effect_instances" if has_instances else "damage_dice"
        scaling_effect_type = raw_effect_type

        normalized_thresholds: list[dict[str, object]] = []
        for threshold in thresholds:
            if not isinstance(threshold, dict):
                continue
            character_level = threshold.get("characterLevel")
            if not isinstance(character_level, int):
                continue
            if scaling_effect_type == "effect_instances":
                instances = threshold.get("instances")
                instance_damage = threshold.get("instanceDamage")
                dice = instance_damage.get("dice") if isinstance(instance_damage, dict) else None
                if isinstance(instances, int) and instances >= 1 and isinstance(dice, str) and dice.strip():
                    normalized_thresholds.append({
                        "characterLevel": character_level,
                        "instances": instances,
                        "instanceDamage": {"dice": dice.strip()},
                    })
            else:
                damage = threshold.get("damage")
                dice = damage.get("dice") if isinstance(damage, dict) else None
                if isinstance(dice, str) and dice.strip():
                    normalized_thresholds.append(
                        {"characterLevel": character_level, "damage": {"dice": dice.strip()}}
                    )
        if not normalized_thresholds:
            return None
        def _threshold_sort_key(entry: dict[str, object]) -> int:
            raw_level = entry.get("characterLevel")
            if isinstance(raw_level, (int, float, str)):
                return int(raw_level)
            return 0

        normalized_thresholds.sort(key=_threshold_sort_key)
        return {
            "scalingMode": "character_level",
            "scalingEffectType": scaling_effect_type,
            "thresholds": normalized_thresholds,
        }

    @classmethod
    def _build_dice_expression(
        cls,
        *,
        dice_count: int,
        dice_size: int,
        bonus: int = 0,
    ) -> str:
        if dice_count <= 0:
            return str(bonus) if bonus else "0"
        expression = f"{dice_count}d{dice_size}"
        if bonus > 0:
            expression += f"+{bonus}"
        elif bonus < 0:
            expression += str(bonus)
        return expression

    @classmethod
    def _merge_dice_expressions(
        cls,
        base_expression: str | None,
        extra_expression: str | None,
        repeats: int = 1,
    ) -> str | None:
        if (
            repeats <= 0
            or not isinstance(extra_expression, str)
            or not extra_expression.strip()
        ):
            return base_expression

        _, base_count, base_sides, base_mod = _parse_dice(base_expression or "")
        _, extra_count, extra_sides, extra_mod = _parse_dice(extra_expression)
        if extra_count <= 0 and extra_mod == 0:
            return base_expression

        scaled_count = extra_count * repeats
        scaled_mod = extra_mod * repeats

        if base_count > 0 and scaled_count > 0 and base_sides != extra_sides:
            raise CombatServiceError(
                "Structured upcast dice must use the same die size as the base spell effect.",
                400,
            )

        total_sides = base_sides or extra_sides
        total_count = base_count + scaled_count
        total_mod = base_mod + scaled_mod
        return cls._build_dice_expression(dice_count=total_count, dice_size=total_sides, bonus=total_mod)

    @classmethod
    def _apply_structured_spell_upcast(
        cls,
        *,
        spell_level: int,
        slot_level: int | None,
        effect_kind: str | None,
        effect_dice: str | None,
        effect_bonus: int,
        upcast: dict | None,
    ) -> dict[str, object]:
        if (
            slot_level is None
            or spell_level <= 0
            or slot_level <= spell_level
            or not isinstance(upcast, dict)
        ):
            return {
                "effect_dice": effect_dice,
                "effect_bonus": effect_bonus,
                "upcast_levels": 0,
                "upcast_applied": False,
                "upcast_added_instances": 0,
                "upcast_instance_effect_dice": None,
            }

        mode = str(upcast.get("mode") or "").strip()
        if not mode or mode == "custom":
            return {
                "effect_dice": effect_dice,
                "effect_bonus": effect_bonus,
                "upcast_levels": 0,
                "upcast_applied": False,
                "upcast_added_instances": 0,
                "upcast_instance_effect_dice": None,
            }

        max_level = upcast.get("maxLevel")
        effective_slot_level = (
            min(slot_level, max_level)
            if isinstance(max_level, int) and max_level > 0
            else slot_level
        )
        extra_levels = max(0, effective_slot_level - spell_level)
        if extra_levels <= 0:
            return {
                "effect_dice": effect_dice,
                "effect_bonus": effect_bonus,
                "upcast_levels": 0,
                "upcast_applied": False,
                "upcast_added_instances": 0,
                "upcast_instance_effect_dice": None,
            }

        per_level = upcast.get("perLevel")
        level_step = upcast.get("levelStep")
        effective_extra_levels = (
            extra_levels // level_step
            if isinstance(level_step, int) and level_step >= 2
            else extra_levels
        )
        repeats = effective_extra_levels * (
            per_level if isinstance(per_level, int) and per_level > 0 else 1
        )
        dice = upcast.get("dice") if isinstance(upcast.get("dice"), str) else None
        flat = upcast.get("flat") if isinstance(upcast.get("flat"), int) else 0

        if mode in {"extra_heal_dice", "add_heal"} and effect_kind != "healing":
            return {
                "effect_dice": effect_dice,
                "effect_bonus": effect_bonus,
                "upcast_levels": 0,
                "upcast_applied": False,
                "upcast_added_instances": 0,
                "upcast_instance_effect_dice": None,
            }
        if mode in {"extra_damage_dice", "add_damage"} and effect_kind == "healing":
            return {
                "effect_dice": effect_dice,
                "effect_bonus": effect_bonus,
                "upcast_levels": 0,
                "upcast_applied": False,
                "upcast_added_instances": 0,
                "upcast_instance_effect_dice": None,
            }

        next_effect_dice = effect_dice
        next_effect_bonus = effect_bonus
        added_instances = 0
        instance_effect_dice = None

        if mode in {
            "extra_damage_dice",
            "extra_heal_dice",
            "additional_effect_instances",
            "additional_targets",
            "add_damage",
            "add_heal",
            "increase_targets",
            "extra_temp_hp",
        }:
            if dice:
                next_effect_dice = cls._merge_dice_expressions(
                    effect_dice,
                    dice,
                    repeats,
                )
            if flat:
                next_effect_bonus += flat * repeats
            if mode in {
                "additional_effect_instances",
                "additional_targets",
                "increase_targets",
            }:
                added_instances = repeats
                instance_effect_dice = dice

        return {
            "effect_dice": next_effect_dice,
            "effect_bonus": next_effect_bonus,
            "upcast_levels": extra_levels,
            "upcast_applied": next_effect_dice != effect_dice
            or next_effect_bonus != effect_bonus,
            "upcast_added_instances": added_instances,
            "upcast_instance_effect_dice": instance_effect_dice,
        }

    @classmethod
    def _apply_character_level_cantrip_scaling(
        cls,
        *,
        spell_level: int,
        caster_level: int | None,
        effect_dice: str | None,
        cantrip_scaling: dict | None = None,
    ) -> dict[str, object]:
        """Returns {"effect_dice", "cantrip_instance_count", "cantrip_instance_dice"}.

        effect_dice is always the aggregated dice expression for display/roll resolution.
        cantrip_instance_count and cantrip_instance_dice are populated only for
        effect_instances cantrips so consumers can dispatch per-instance rolls.
        """
        _no_change: dict[str, object] = {
            "effect_dice": effect_dice,
            "cantrip_instance_count": None,
            "cantrip_instance_dice": None,
        }
        if spell_level != 0 or caster_level is None:
            return _no_change
        if not isinstance(cantrip_scaling, dict):
            return _no_change

        scaling_effect_type = cantrip_scaling.get("scalingEffectType", "damage_dice")
        selected_dice = effect_dice
        selected_instances: int | None = None
        instance_dice: str | None = None

        for threshold in cantrip_scaling.get("thresholds", []):
            if not isinstance(threshold, dict):
                continue
            threshold_level = threshold.get("characterLevel")
            if not isinstance(threshold_level, int) or caster_level < threshold_level:
                continue
            if scaling_effect_type == "effect_instances":
                instances = threshold.get("instances")
                inst_dmg = threshold.get("instanceDamage")
                dice = inst_dmg.get("dice") if isinstance(inst_dmg, dict) else None
                if isinstance(instances, int) and isinstance(dice, str) and dice.strip():
                    selected_instances = instances
                    instance_dice = dice.strip()
            else:
                damage = threshold.get("damage")
                dice = damage.get("dice") if isinstance(damage, dict) else None
                if isinstance(dice, str) and dice.strip():
                    selected_dice = dice.strip()

        if scaling_effect_type == "effect_instances" and selected_instances is not None and instance_dice:
            _, count, sides, mod = _parse_dice(instance_dice)
            total_count = count * selected_instances
            total_mod = mod * selected_instances
            return {
                "effect_dice": cls._build_dice_expression(dice_count=total_count, dice_size=sides, bonus=total_mod),
                "cantrip_instance_count": selected_instances,
                "cantrip_instance_dice": instance_dice,
            }

        return {"effect_dice": selected_dice, "cantrip_instance_count": None, "cantrip_instance_dice": None}

    @classmethod
    def _normalize_save_success_outcome(cls, value: object) -> str | None:
        normalized = cls._normalize_lookup(value).replace(" ", "_")
        if normalized in cls._SAVE_SUCCESS_OUTCOME_VALUES:
            return normalized
        return None

    @classmethod
    def _normalize_attack_miss_outcome(cls, value: object) -> str | None:
        normalized = cls._normalize_lookup(value).replace(" ", "_")
        if normalized in cls._ATTACK_MISS_OUTCOME_VALUES:
            return normalized
        return None
