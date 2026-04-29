import type { UpcastMode } from "../../../entities/base-spell";

export type UpcastPreviewRow = {
  slotLevel: number;
  isBase: boolean;
  label: string;
  value: string;
};

export type UpcastPreviewParams = {
  spellLevel: number;
  upcastMode: UpcastMode | "";
  upcastDice: string | null;
  upcastFlat: number | null;
  perLevel: number;
  maxLevel: number | null;
  baseEffectInstances: number | null;
  baseDice: string | null;
  baseMaxTargets: number | null;
};

const ORDINAL_SUFFIXES = ["th", "st", "nd", "rd"] as const;

function ordinal(n: number): string {
  const v = n % 100;
  if (v >= 11 && v <= 13) return `${n}th`;
  const s = v % 10;
  if (s >= 1 && s <= 3) return `${n}${ORDINAL_SUFFIXES[s]}`;
  return `${n}th`;
}

function parseDice(expression: string): { count: number; sides: number; modifier: number } {
  const match = expression.match(/^\s*(?:(\d*)d(\d+)|(\d+))\s*(?:([+-])\s*(\d+))?\s*$/i);
  if (!match) return { count: 0, sides: 0, modifier: 0 };
  const count = match[1] ? parseInt(match[1], 10) : match[2] ? 1 : 0;
  const sides = match[2] ? parseInt(match[2], 10) : 0;
  const modifier =
    match[3] && match[4] ? parseInt(match[4], 10) * (match[3] === "-" ? -1 : 1) : 0;
  return { count, sides, modifier };
}

function buildDiceExpression(count: number, sides: number, modifier: number): string | null {
  if (count > 0) {
    let result = `${count}d${sides}`;
    if (modifier > 0) result += `+${modifier}`;
    else if (modifier < 0) result += `${modifier}`;
    return result;
  }
  if (modifier !== 0) return `${modifier}`;
  return null;
}

function mergeDice(
  baseExpression: string,
  extraExpression: string,
  repeats: number,
): string {
  if (repeats <= 0 || !extraExpression) return baseExpression;
  const base = parseDice(baseExpression);
  const extra = parseDice(extraExpression);
  const scaledCount = extra.count * repeats;
  const scaledMod = extra.modifier * repeats;

  let totalCount = base.count + scaledCount;
  let totalSides = base.sides || extra.sides;
  let totalMod = base.modifier + scaledMod;

  const result = buildDiceExpression(totalCount, totalSides, totalMod);
  return result ?? baseExpression;
}

export function computeUpcastPreviewRows(params: UpcastPreviewParams): UpcastPreviewRow[] {
  const {
    spellLevel,
    upcastMode,
    upcastDice,
    upcastFlat,
    perLevel,
    maxLevel,
    baseEffectInstances,
    baseDice,
    baseMaxTargets,
  } = params;

  if (!upcastMode || spellLevel <= 0) return [];

  const effectiveMax = Math.min(maxLevel ?? 9, 9);
  const rows: UpcastPreviewRow[] = [];
  const upperBound = Math.min(spellLevel + 3, effectiveMax);

  for (let level = spellLevel; level <= upperBound; level++) {
    const isBase = level === spellLevel;
    const extraLevels = level - spellLevel;
    const repeats = extraLevels * perLevel;

    let value = "";

    switch (upcastMode) {
      case "extra_damage_dice":
      case "extra_heal_dice": {
        if (isBase) {
          value = baseDice || "—";
        } else if (upcastDice) {
          value = mergeDice(baseDice || "", upcastDice, repeats);
        } else if (upcastFlat && upcastFlat > 0) {
          value = baseDice
            ? `${baseDice}+${upcastFlat * repeats}`
            : `+${upcastFlat * repeats}`;
        } else {
          value = baseDice || "—";
        }
        break;
      }
      case "flat_bonus": {
        if (isBase) {
          value = "—";
        } else {
          value = `+${(upcastFlat ?? 0) * repeats}`;
        }
        break;
      }
      case "additional_effect_instances": {
        const base = baseEffectInstances ?? 0;
        const total = base + repeats;
        if (isBase) {
          value = "no change";
        } else {
          const suffix = total === 1 ? "instance" : "instances";
          value = `+${repeats} (${total} ${suffix})`;
        }
        break;
      }
      case "additional_targets": {
        const base = baseMaxTargets ?? 0;
        const total = base + repeats;
        if (isBase) {
          value = "no change";
        } else {
          const suffix = total === 1 ? "target" : "targets";
          value = `+${repeats} (${total} ${suffix})`;
        }
        break;
      }
      case "duration_scaling": {
        value = isBase ? "Base duration" : `+${extraLevels} level${extraLevels > 1 ? "s" : ""}`;
        break;
      }
      case "effect_scaling": {
        value = isBase ? "Base effect" : `Scales at +${extraLevels} level${extraLevels > 1 ? "s" : ""}`;
        break;
      }
      case "extra_effect": {
        value = isBase ? "Base effect" : "Additional effect unlocked";
        break;
      }
    }

    rows.push({
      slotLevel: level,
      isBase,
      label: isBase ? `${ordinal(level)} (base)` : ordinal(level),
      value,
    });
  }

  return rows;
}

export type UpcastValidationParams = {
  resolutionType: string;
  upcastMode: UpcastMode | "";
  upcastDiceCount: string;
  upcastDieSize: string;
  upcastFlat: string;
  upcastScalingKey: string;
  upcastScalingSummary: string;
  upcastUnlockKey: string;
  upcastUnlockSummary: string;
};

export type UpcastWarning = {
  key: string;
};

export function computeUpcastValidationWarnings(params: UpcastValidationParams): UpcastWarning[] {
  const warnings: UpcastWarning[] = [];
  const {
    resolutionType,
    upcastMode,
    upcastDiceCount,
    upcastDieSize,
    upcastFlat,
    upcastScalingKey,
    upcastScalingSummary,
    upcastUnlockKey,
    upcastUnlockSummary,
  } = params;

  if (!upcastMode) return warnings;

  if (upcastMode === "extra_damage_dice" && resolutionType !== "damage") {
    warnings.push({ key: "catalog.spells.validation.upcastModeRequiresDamage" });
  }

  if (upcastMode === "extra_heal_dice" && resolutionType !== "heal") {
    warnings.push({ key: "catalog.spells.validation.upcastModeRequiresHeal" });
  }

  const hasDice = Boolean(upcastDiceCount && upcastDieSize);
  const hasFlat = Boolean(upcastFlat);

  if (
    (upcastMode === "extra_damage_dice" ||
      upcastMode === "extra_heal_dice" ||
      upcastMode === "additional_effect_instances") &&
    !hasDice &&
    !hasFlat
  ) {
    warnings.push({ key: "catalog.spells.validation.upcastDiceOrBonusRequired" });
  }

  if (upcastMode === "flat_bonus" && !hasFlat) {
    warnings.push({ key: "catalog.spells.validation.upcastFlatRequired" });
  }

  if (upcastMode === "effect_scaling" && !upcastScalingKey.trim()) {
    warnings.push({ key: "catalog.spells.validation.upcastScalingKeyRequired" });
  }

  if (upcastMode === "effect_scaling" && !upcastScalingSummary.trim()) {
    warnings.push({ key: "catalog.spells.validation.upcastScalingSummaryRequired" });
  }

  if (upcastMode === "extra_effect" && !upcastUnlockKey.trim()) {
    warnings.push({ key: "catalog.spells.validation.upcastUnlockKeyRequired" });
  }

  if (upcastMode === "extra_effect" && !upcastUnlockSummary.trim()) {
    warnings.push({ key: "catalog.spells.validation.upcastUnlockSummaryRequired" });
  }

  return warnings;
}
