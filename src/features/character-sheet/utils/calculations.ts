import type {
  AbilityName,
  CharacterSheet,
  ProficiencyLevel,
  SkillName,
  Weapon,
} from "../model/characterSheet.types";
import { SKILL_ABILITY_MAP, STANDARD_ARRAY } from "../constants";

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
): number => {
  const abilityMod = getModifier(abilities[weapon.ability]);
  const profBonus = weapon.proficient ? getProficiencyBonus(level) : 0;
  return abilityMod + profBonus + weapon.magicBonus;
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
