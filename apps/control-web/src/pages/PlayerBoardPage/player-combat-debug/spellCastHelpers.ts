import type { CombatSpellResult } from "../../../shared/api/combatRepo";
import { formatDamageDiceExpression } from "../../../shared/utils/diceExpression";
import { getInstanceLabel } from "./InstanceTargetSelector";

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

export const getOutcomeLabel = (result: CombatSpellResult) =>
  result.action_kind === "saving_throw"
    ? result.is_saved
      ? "Save bem-sucedido"
      : "Save falhou"
    : result.is_critical
      ? "Acerto critico"
      : result.is_hit
        ? "Acerto"
        : result.action_kind === "spell_attack"
          ? "Errou"
          : result.effect_kind === "healing"
            ? "Cura"
            : "Resultado";

export const formatEffectInstanceOutcome = (
  result: CombatSpellResult,
  outcome: NonNullable<CombatSpellResult["effect_instance_outcomes"]>[number],
) => {
  const label = getInstanceLabel(result.spell_canonical_key, outcome.instance_index);
  const details: string[] = [];

  const coverLabel = outcome.cover === "half" ? "meia cobertura" : outcome.cover === "three_quarters" || outcome.cover === "threeQuarters" ? "três-quartos" : null;

  if (outcome.is_hit === true) {
    details.push(outcome.is_critical ? "acerto crítico" : "acerto");
  } else if (outcome.is_hit === false) {
    if (outcome.effective_ac) {
      const coverPart = coverLabel ? ` (${coverLabel})` : "";
      details.push(`erro contra AC efetiva ${outcome.effective_ac}${coverPart}`);
    } else {
      details.push("erro");
    }
  }

  if (outcome.is_saved === true) {
    if (outcome.effective_save_dc && outcome.effective_save_dc !== outcome.base_save_dc) {
      details.push(`passou no save DC efetiva ${outcome.effective_save_dc}`);
    } else if (outcome.base_save_dc) {
      details.push(`passou no save DC ${outcome.base_save_dc}`);
    } else {
      details.push("passou no save");
    }
  } else if (outcome.is_saved === false) {
    if (outcome.effective_save_dc && outcome.effective_save_dc !== outcome.base_save_dc) {
      details.push(`falhou no save DC efetiva ${outcome.effective_save_dc}`);
    } else if (outcome.base_save_dc) {
      details.push(`falhou no save DC ${outcome.base_save_dc}`);
    } else {
      details.push("falhou no save");
    }
  }

  if (typeof outcome.damage === "number" && outcome.damage > 0) {
    details.push(`${outcome.damage} dano`);
  }

  if (typeof outcome.healing === "number" && outcome.healing > 0) {
    details.push(`${outcome.healing} cura`);
  }

  if (typeof outcome.new_hp === "number") {
    details.push(`PV ${outcome.new_hp}`);
  }

  return `${label} -> ${outcome.target_display_name}: ${details.length > 0 ? details.join(", ") : "sem efeito"}`;
};

export const formatAreaTargetOutcome = (
  outcome: NonNullable<CombatSpellResult["area_target_outcomes"]>[number],
) => {
  if (outcome.excluded_by_guardrail) {
    return `${outcome.target_display_name}: excluído por regra mecânica${outcome.guardrail_reason ? ` (${outcome.guardrail_reason})` : ""}`;
  }

  const details: string[] = [];
  const coverLabel = outcome.cover === "half" ? "meia cobertura" : outcome.cover === "three_quarters" || outcome.cover === "threeQuarters" ? "três-quartos" : null;

  if (coverLabel && outcome.cover_modifier && outcome.cover_modifier > 0) {
    details.push(coverLabel);
  }

  if (outcome.is_saved === true) {
    if (outcome.effective_save_dc && outcome.effective_save_dc !== outcome.base_save_dc) {
      details.push(`passou no save DC efetiva ${outcome.effective_save_dc}`);
    } else if (outcome.base_save_dc) {
      details.push(`passou no save DC ${outcome.base_save_dc}`);
    } else {
      details.push("passou no save");
    }
  } else if (outcome.is_saved === false) {
    if (outcome.effective_save_dc && outcome.effective_save_dc !== outcome.base_save_dc) {
      details.push(`falhou no save DC efetiva ${outcome.effective_save_dc}`);
    } else if (outcome.base_save_dc) {
      details.push(`falhou no save DC ${outcome.base_save_dc}`);
    } else {
      details.push("falhou no save");
    }
  }

  if (typeof outcome.damage_applied === "number" && outcome.damage_applied > 0) {
    details.push(`${outcome.damage_applied} dano`);
  }

  if (typeof outcome.healing_applied === "number" && outcome.healing_applied > 0) {
    details.push(`${outcome.healing_applied} cura`);
  }

  if (typeof outcome.new_hp === "number") {
    details.push(`PV ${outcome.new_hp}`);
  }

  return `${outcome.target_display_name}: ${details.length > 0 ? details.join(", ") : "sem efeito"}`;
};
