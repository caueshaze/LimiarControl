import type { CombatEntityActionResult } from "../../shared/api/combatRepo";
import { formatDamageDiceExpression } from "../../shared/utils/diceExpression";

export const D20_VALUES = Array.from({ length: 20 }, (_, i) => i + 1);

export const formatSigned = (value: number) => `${value >= 0 ? "+" : ""}${value}`;

export const formatDamageBreakdown = (result: CombatEntityActionResult) => {
  const rolls = result.damage_rolls ?? [];
  const damageDiceLabel =
    formatDamageDiceExpression(result.damage_dice, Boolean(result.is_critical)) ??
    result.damage_dice;
  if (!rolls.length) {
    return `Base ${result.base_damage ?? 0}${result.damage_bonus ? ` ${result.damage_bonus >= 0 ? "+" : "-"} ${Math.abs(result.damage_bonus)}` : ""} = ${result.damage}`;
  }
  const rollText = rolls.join(", ");
  return `${damageDiceLabel}: [${rollText}]${result.damage_bonus ? ` ${result.damage_bonus >= 0 ? "+" : "-"} ${Math.abs(result.damage_bonus)}` : ""} = ${result.damage}`;
};
