from __future__ import annotations

from .exceptions import CombatServiceError, _parse_dice
from .spell_automation_metadata import _RESOLUTION_TYPE_TO_SPELL_MODE as _SPELL_MODE_MAP


class CombatSpellDiceMathMixin:
    _SAVE_SUCCESS_OUTCOME_VALUES = {"none", "half_damage"}
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
        return normalized

    @classmethod
    def _build_dice_expression(
        cls, count: int, sides: int, modifier: int
    ) -> str | None:
        if count <= 0:
            return str(modifier) if modifier else None
        expression = f"{count}d{sides}"
        if modifier > 0:
            expression += f"+{modifier}"
        elif modifier < 0:
            expression += str(modifier)
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

        base_count, base_sides, base_mod = _parse_dice(base_expression or "")
        extra_count, extra_sides, extra_mod = _parse_dice(extra_expression)
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
        return cls._build_dice_expression(total_count, total_sides, total_mod)

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
            }

        mode = str(upcast.get("mode") or "").strip()
        if not mode or mode == "custom":
            return {
                "effect_dice": effect_dice,
                "effect_bonus": effect_bonus,
                "upcast_levels": 0,
                "upcast_applied": False,
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
            }

        per_level = upcast.get("perLevel")
        repeats = extra_levels * (
            per_level if isinstance(per_level, int) and per_level > 0 else 1
        )
        dice = upcast.get("dice") if isinstance(upcast.get("dice"), str) else None
        flat = upcast.get("flat") if isinstance(upcast.get("flat"), int) else 0

        if mode == "add_heal" and effect_kind != "healing":
            return {
                "effect_dice": effect_dice,
                "effect_bonus": effect_bonus,
                "upcast_levels": 0,
                "upcast_applied": False,
            }
        if mode == "add_damage" and effect_kind == "healing":
            return {
                "effect_dice": effect_dice,
                "effect_bonus": effect_bonus,
                "upcast_levels": 0,
                "upcast_applied": False,
            }

        next_effect_dice = effect_dice
        next_effect_bonus = effect_bonus

        if mode in {"add_damage", "add_heal", "increase_targets"}:
            if dice:
                next_effect_dice = cls._merge_dice_expressions(
                    effect_dice,
                    dice,
                    repeats,
                )
            if flat:
                next_effect_bonus += flat * repeats

        return {
            "effect_dice": next_effect_dice,
            "effect_bonus": next_effect_bonus,
            "upcast_levels": extra_levels,
            "upcast_applied": next_effect_dice != effect_dice
            or next_effect_bonus != effect_bonus,
        }

    @classmethod
    def _normalize_save_success_outcome(cls, value: object) -> str | None:
        normalized = cls._normalize_lookup(value).replace(" ", "_")
        if normalized in cls._SAVE_SUCCESS_OUTCOME_VALUES:
            return normalized
        return None
