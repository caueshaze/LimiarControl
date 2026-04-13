import { formatDamageDiceExpression } from "../../../shared/utils/diceExpression";
import type { CombatSpellResult } from "../../../shared/api/combatRepo";

export const D20_VALUES = Array.from({ length: 20 }, (_, i) => i + 1);

export const parseBonus = (value: string) => {
  const parsed = Number.parseInt(value.trim(), 10);
  return Number.isFinite(parsed) ? parsed : 0;
};

export const getSpellRolledTotal = (result: CombatSpellResult) =>
  Math.max(0, (result.base_effect ?? 0) + (result.effect_bonus ?? 0));

export const formatSpellEffectBreakdown = (result: CombatSpellResult) => {
  const rolls = result.effect_rolls ?? [];
  const effectDiceLabel =
    formatDamageDiceExpression(result.effect_dice, Boolean(result.is_critical)) ??
    result.effect_dice;
  const effectTotal = result.effect_kind === "healing" ? result.healing : result.damage;
  const rolledTotal = getSpellRolledTotal(result);
  const isHalfDamageSave =
    result.action_kind === "saving_throw" &&
    result.is_saved &&
    result.save_success_outcome === "half_damage" &&
    result.effect_kind !== "healing";

  if (!rolls.length) {
    const baseText = `Base ${result.base_effect ?? 0}${result.effect_bonus ? ` ${result.effect_bonus >= 0 ? "+" : "-"} ${Math.abs(result.effect_bonus)}` : ""}`;
    return isHalfDamageSave
      ? `${baseText} = ${rolledTotal}; metade aplicada = ${effectTotal}`
      : `${baseText} = ${effectTotal}`;
  }
  const rollText = `${effectDiceLabel}: [${rolls.join(", ")}]${result.effect_bonus ? ` ${result.effect_bonus >= 0 ? "+" : "-"} ${Math.abs(result.effect_bonus)}` : ""}`;
  return isHalfDamageSave
    ? `${rollText} = ${rolledTotal}; metade aplicada = ${effectTotal}`
    : `${rollText} = ${effectTotal}`;
};
