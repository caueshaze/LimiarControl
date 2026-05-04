import type {
  AbilityName,
  CharacterSheet,
  ProficiencyLevel,
  SkillName,
  Weapon,
} from "../model/characterSheet.types";
import type { ActiveEffect } from "../../../shared/api/combatRepo";
import { SKILL_ABILITY_MAP, STANDARD_ARRAY } from "../constants";
import { getFightingStyleAttackBonus } from "../data/classFeatures";

// ── Core Math ───────────────────────────────────────────────────────────────

export const getModifier = (value: number): number =>
  Math.floor((value - 10) / 2);

export const getProficiencyBonus = (level: number): number =>
  Math.ceil(level / 4) + 1;

export const formatMod = (mod: number): string =>
  mod >= 0 ? `+${mod}` : `${mod}`;

export const safeParseInt = (value: string, fallback = 0): number => {
  const n = parseInt(value, 10);
  return isNaN(n) ? fallback : n;
};

export const clampHP = (current: number, max: number): number =>
  Math.max(0, Math.min(current, max));

export const computeAbilityScoreTotal = (
  abilities: Record<AbilityName, number>,
): number => Object.values(abilities).reduce((sum, score) => sum + score, 0);

export const isStandardArrayDistribution = (
  abilities: Record<AbilityName, number>,
): boolean => {
  const scores = Object.values(abilities).slice().sort((a, b) => b - a);
  const standard = [...STANDARD_ARRAY].sort((a, b) => b - a);
  return scores.every((score, idx) => score === standard[idx]);
};

export const computeMaxHpAtLevel = (
  hitDiceType: string,
  level: number,
  constitutionScore: number,
): number => {
  const dieMax = safeParseInt(hitDiceType.replace("d", ""), 0);
  if (!dieMax || level <= 0) return 0;
  // Level 1 uses max hit die. Additional levels use average rounding-up progression.
  const conMod = getModifier(constitutionScore);
  const averagePerLevel = Math.floor(dieMax / 2) + 1;
  const extraLevels = Math.max(0, level - 1);
  return Math.max(1, dieMax + conMod + extraLevels * (averagePerLevel + conMod));
};

// ── Derived Stats ───────────────────────────────────────────────────────────

export const computeInitiative = (dexMod: number): number => dexMod;

export type PassiveSkillBonusSource = { label: string; value: number; groupKey: string };

export function declarativeEffectGroupKey(
  metadata: Record<string, unknown>,
  effect: ActiveEffect,
  effectType: string,
  paramsKey: string,
  fallbackIndex: number,
): string {
  const groupId = metadata.declarative_effect_group_id;
  if (typeof groupId === "string" && groupId) return groupId;
  const source = (metadata.source_spell_key as string) || (metadata.source_spell_name as string);
  if (typeof source === "string" && source) {
    const variant = (metadata.selected_variant_key as string) || "";
    return `${source}|${variant}|${effectType}|${paramsKey}`;
  }
  if (typeof effect.id === "string" && effect.id) return effect.id;
  return `__unknown_${fallbackIndex}`;
}

function passiveBonusGroupKey(
  metadata: Record<string, unknown>,
  effect: ActiveEffect,
  params: Record<string, unknown>,
  index: number,
): string {
  const sk = (params.skill as string) || "";
  const bonus = params.bonus ?? "";
  return declarativeEffectGroupKey(metadata, effect, "passive_skill_bonus", `${sk}|${bonus}`, index);
}

export const computePassiveSkillBonusSources = (
  activeEffects: ActiveEffect[],
  skill: string,
): PassiveSkillBonusSource[] => {
  const groupBest = new Map<string, PassiveSkillBonusSource>();
  for (let i = 0; i < activeEffects.length; i++) {
    const effect = activeEffects[i];
    const metadata = effect.metadata;
    if (!metadata || typeof metadata !== "object") continue;
    const declarative = metadata.declarative_effect;
    if (!declarative || typeof declarative !== "object") continue;
    if ((declarative as Record<string, unknown>).type !== "passive_skill_bonus") continue;
    const params = (declarative as Record<string, unknown>).params;
    if (!params || typeof params !== "object") continue;
    const p = params as Record<string, unknown>;
    if (p.skill !== skill || typeof p.bonus !== "number") continue;
    const label =
      (typeof effect.display_label === "string" && effect.display_label) ||
      (typeof metadata.source_spell_name === "string" && metadata.source_spell_name) ||
      "Passive skill bonus";
    const key = passiveBonusGroupKey(metadata as Record<string, unknown>, effect, p, i);
    const existing = groupBest.get(key);
    if (!existing || p.bonus > existing.value) {
      groupBest.set(key, { label, value: p.bonus, groupKey: key });
    }
  }
  return Array.from(groupBest.values());
};

export const computePassiveSkillBonus = (
  activeEffects: ActiveEffect[],
  skill: string,
): number =>
  computePassiveSkillBonusSources(activeEffects, skill).reduce(
    (sum, s) => sum + s.value,
    0,
  );

export const computePassivePerception = (sheet: CharacterSheet): number => {
  const wisMod = getModifier(sheet.abilities.wisdom);
  const profLevel = sheet.skillProficiencies.perception;
  const profBonus = getProficiencyBonus(sheet.level);
  return 10 + wisMod + Math.floor(profBonus * profLevel);
};

export const computeSpellSaveDC = (
  level: number,
  abilityScore: number,
): number => 8 + getProficiencyBonus(level) + getModifier(abilityScore);

export const computeSpellAttack = (
  level: number,
  abilityScore: number,
): number => getProficiencyBonus(level) + getModifier(abilityScore);

// ── Skill & Save Modifiers ──────────────────────────────────────────────────

export const computeSkillMod = (
  skill: SkillName,
  abilities: Record<AbilityName, number>,
  proficiencies: Record<SkillName, ProficiencyLevel>,
  level: number,
): number => {
  const ability = SKILL_ABILITY_MAP[skill];
  const mod = getModifier(abilities[ability]);
  const profLevel = proficiencies[skill];
  const profBonus = getProficiencyBonus(level);
  return mod + Math.floor(profBonus * profLevel);
};

export const computeSaveMod = (
  ability: AbilityName,
  score: number,
  proficient: boolean,
  level: number,
): number => {
  const mod = getModifier(score);
  return proficient ? mod + getProficiencyBonus(level) : mod;
};

// ── Weapon Computations ─────────────────────────────────────────────────────

export const computeWeaponAttack = (
  weapon: Weapon,
  abilities: Record<AbilityName, number>,
  level: number,
  fightingStyle: string | null = null,
): number => {
  const abilityMod = getModifier(abilities[weapon.ability]);
  const profBonus = weapon.proficient ? getProficiencyBonus(level) : 0;
  const fightingStyleBonus = getFightingStyleAttackBonus({
    fightingStyle,
    rangeType: weapon.rangeType,
    properties: weapon.properties,
  });
  return abilityMod + profBonus + weapon.magicBonus + fightingStyleBonus;
};

export const computeWeaponDamage = (
  weapon: Weapon,
  abilities: Record<AbilityName, number>,
): string => {
  const abilityMod = getModifier(abilities[weapon.ability]);
  const total = abilityMod + weapon.magicBonus;
  const sign = total >= 0 ? "+" : "";
  return total !== 0
    ? `${weapon.damageDice}${sign}${total}`
    : weapon.damageDice;
};

// ── Inventory Weight ────────────────────────────────────────────────────────

export const computeTotalWeight = (
  items: CharacterSheet["inventory"],
): number =>
  items.reduce((sum, item) => sum + item.weight * item.quantity, 0);

// ── Carrying Capacity ────────────────────────────────────────────────────────

export const LB_TO_KG = 0.45359237;

// ── Encumbrance Tier (Variant: Encumbrance) ─────────────────────────────────

export type EncumbranceTier = "normal" | "encumbered" | "heavily_encumbered" | "overloaded";

export type EncumbranceResult = {
  tier: EncumbranceTier;
  normalMaxKg: number;
  encumberedMaxKg: number;
  heavilyEncumberedMaxKg: number;
  remainingKg: number;
  nextThresholdKg: number | null;
};

export const computeEncumbranceTier = ({
  strengthScore,
  totalWeightKg,
}: {
  strengthScore: number;
  totalWeightKg: number;
}): EncumbranceResult => {
  const totalWeightLb = totalWeightKg / LB_TO_KG;

  const normalMaxLb = strengthScore * 5;
  const encumberedMaxLb = strengthScore * 10;
  const heavilyMaxLb = strengthScore * 15;

  let tier: EncumbranceTier = "normal";
  if (totalWeightLb > heavilyMaxLb) {
    tier = "overloaded";
  } else if (totalWeightLb > encumberedMaxLb) {
    tier = "heavily_encumbered";
  } else if (totalWeightLb > normalMaxLb) {
    tier = "encumbered";
  }

  let remainingKg: number;
  let nextThresholdKg: number | null;
  if (tier === "normal") {
    remainingKg = Math.max(0, normalMaxLb * LB_TO_KG - totalWeightKg);
    nextThresholdKg = Math.round(normalMaxLb * LB_TO_KG);
  } else if (tier === "encumbered") {
    remainingKg = Math.max(0, encumberedMaxLb * LB_TO_KG - totalWeightKg);
    nextThresholdKg = Math.round(encumberedMaxLb * LB_TO_KG);
  } else if (tier === "heavily_encumbered") {
    remainingKg = Math.max(0, heavilyMaxLb * LB_TO_KG - totalWeightKg);
    nextThresholdKg = Math.round(heavilyMaxLb * LB_TO_KG);
  } else {
    remainingKg = 0;
    nextThresholdKg = null;
  }

  return {
    tier,
    normalMaxKg: Math.round(normalMaxLb * LB_TO_KG),
    encumberedMaxKg: Math.round(encumberedMaxLb * LB_TO_KG),
    heavilyEncumberedMaxKg: Math.round(heavilyMaxLb * LB_TO_KG),
    remainingKg: Math.round(remainingKg * 10) / 10,
    nextThresholdKg,
  };
};

export const computeProjectedEncumbranceTier = ({
  strengthScore,
  currentWeightKg,
  addedWeightLb,
}: {
  strengthScore: number;
  currentWeightKg: number;
  addedWeightLb: number;
}): EncumbranceResult => {
  const addedKg = addedWeightLb * LB_TO_KG;
  return computeEncumbranceTier({
    strengthScore,
    totalWeightKg: currentWeightKg + addedKg,
  });
};

export const applyEncumbranceMovementPenalty = (
  baseSpeedMeters: number,
  tier: EncumbranceTier,
): number => {
  if (tier === "overloaded") return 0;
  if (tier === "heavily_encumbered") return Math.max(0, baseSpeedMeters - 6);
  if (tier === "encumbered") return Math.max(0, baseSpeedMeters - 3);
  return baseSpeedMeters;
};

export type CarryingCapacitySource = { label: string; multiplier: number; groupKey: string };

function carryingCapacityGroupKey(
  metadata: Record<string, unknown>,
  effect: ActiveEffect,
  params: Record<string, unknown>,
  index: number,
): string {
  const mult = params.multiplier ?? "";
  return declarativeEffectGroupKey(metadata, effect, "carrying_capacity_multiplier", `${mult}`, index);
}

export const computeCarryingCapacityMultiplierSources = (
  activeEffects: ActiveEffect[],
): CarryingCapacitySource[] => {
  const groupBest = new Map<string, CarryingCapacitySource>();
  for (let i = 0; i < activeEffects.length; i++) {
    const effect = activeEffects[i];
    const metadata = effect.metadata;
    if (!metadata || typeof metadata !== "object") continue;
    const declarative = metadata.declarative_effect;
    if (!declarative || typeof declarative !== "object") continue;
    if ((declarative as Record<string, unknown>).type !== "carrying_capacity_multiplier") continue;
    const params = (declarative as Record<string, unknown>).params;
    if (!params || typeof params !== "object") continue;
    const p = params as Record<string, unknown>;
    if (typeof p.multiplier !== "number") continue;
    const label =
      (typeof effect.display_label === "string" && effect.display_label) ||
      (typeof metadata.source_spell_name === "string" && metadata.source_spell_name) ||
      "Carrying capacity bonus";
    const key = carryingCapacityGroupKey(metadata as Record<string, unknown>, effect, p, i);
    const existing = groupBest.get(key);
    if (!existing || p.multiplier > existing.multiplier) {
      groupBest.set(key, { label, multiplier: p.multiplier, groupKey: key });
    }
  }
  return Array.from(groupBest.values());
};

export const computeCarryingCapacityMultiplier = (activeEffects: ActiveEffect[]): number => {
  const sources = computeCarryingCapacityMultiplierSources(activeEffects);
  if (sources.length === 0) return 1.0;
  return Math.max(...sources.map((s) => s.multiplier));
};

export const computeCarryingCapacity = (
  strengthScore: number,
  activeEffects: ActiveEffect[],
) => {
  const multiplier = computeCarryingCapacityMultiplier(activeEffects);
  const baseKg = strengthScore * 15 * LB_TO_KG;
  const effectiveKg = baseKg * multiplier;
  const carryingCapacityKg = Math.round(effectiveKg);
  const pushDragLiftKg = Math.round(effectiveKg * 2);
  const baseCarryingCapacityKg = Math.round(baseKg);

  return {
    baseCarryingCapacityKg,
    carryingCapacityKg,
    pushDragLiftKg,
    multiplier,
    sources: computeCarryingCapacityMultiplierSources(activeEffects),
  };
};
