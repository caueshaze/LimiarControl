import type { CombatEntityActionResult } from "../../shared/api/combatRepo";
import { formatDamageDiceExpression } from "../../shared/utils/diceExpression";

export const D20_VALUES = Array.from({ length: 20 }, (_, i) => i + 1);

export const formatSigned = (value: number) => `${value >= 0 ? "+" : ""}${value}`;

export const formatDamageBreakdown = (result: CombatEntityActionResult) => {
  // Structured breakdown (canonical source)
  if (result.damage_breakdown) {
    const bd = result.damage_breakdown;
    const lines = bd.components.map((c) => {
      const sign = c.signed_total >= 0 ? "+" : "-";
      const abs = Math.abs(c.signed_total);
      const diceHint = c.dice ? ` (${c.dice})` : "";
      if (c.kind === "base_weapon") {
        return `${c.source_label}${diceHint}: ${c.signed_total}`;
      }
      return `${c.source_label}${diceHint}: ${sign}${abs}`;
    });
    if (bd.minimum_applied != null) {
      lines.push(`Dano mínimo aplicado: ${bd.minimum_applied}`);
    }
    lines.push(`Total: ${bd.total}`);
    return lines.join("\n");
  }
  // Legacy fallback
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
