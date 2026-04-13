import type { Armor, CharacterSheet } from "../model/characterSheet.types";
import { getModifier } from "./calculations";

export type ArmorCategory = "light" | "medium" | "heavy";

export type AcArmor = {
  name: string;
  category: ArmorCategory;
  baseAc: number;
  allowsDex: boolean;
  dexCap: number | null;
  stealthDisadvantage?: boolean;
  minStrength?: number | null;
};

export type ActiveAcEffect = {
  id: string;
  label: string;
  bonus: number;
  active: boolean;
};

export type CharacterAcState = {
  dexMod: number;
  conMod: number;
  wisMod: number;
  armorEquipped: AcArmor | null;
  shieldEquipped: boolean;
  hasBarbarianUnarmoredDefense: boolean;
  hasMonkUnarmoredDefense: boolean;
  hasMageArmor: boolean;
  activeAcEffects: ActiveAcEffect[];
};

export type AcBreakdownPart = {
  label: string;
  value: number;
};

export type AcBaseSource =
  | "default"
  | "light_armor"
  | "medium_armor"
  | "heavy_armor"
  | "barbarian_unarmored_defense"
  | "monk_unarmored_defense"
  | "mage_armor";

export type AcBaseBreakdown = {
  source: AcBaseSource;
  value: number;
  formula: string;
  parts: AcBreakdownPart[];
};

export type AcCalculationResult = {
  base: AcBaseBreakdown;
  bonuses: {
    shield: number;
    effects: Array<{ id: string; label: string; bonus: number }>;
    totalBonus: number;
  };
  total: number;
  candidateBases: AcBaseBreakdown[];
};

type BuildCharacterAcStateOptions = {
  activeAcEffects?: ActiveAcEffect[];
  hasBarbarianUnarmoredDefense?: boolean;
  hasMageArmor?: boolean;
  hasMonkUnarmoredDefense?: boolean;
};

const SHIELD_BONUS = 2;

const BASE_PRIORITY: Record<AcBaseSource, number> = {
  heavy_armor: 70,
  medium_armor: 60,
  light_armor: 50,
  mage_armor: 40,
  barbarian_unarmored_defense: 30,
  monk_unarmored_defense: 20,
  default: 10,
};

const sortAcBases = (left: AcBaseBreakdown, right: AcBaseBreakdown) =>
  right.value - left.value ||
  BASE_PRIORITY[right.source] - BASE_PRIORITY[left.source] ||
  left.source.localeCompare(right.source);

const createBaseBreakdown = (
  source: AcBaseSource,
  formula: string,
  parts: AcBreakdownPart[],
): AcBaseBreakdown => ({
  source,
  formula,
  parts,
  value: parts.reduce((sum, part) => sum + part.value, 0),
});

const getArmorDexContribution = (armor: AcArmor, dexMod: number) => {
  if (!armor.allowsDex || armor.category === "heavy") return 0;
  if (armor.dexCap === null) return dexMod;
  return Math.min(dexMod, armor.dexCap);
};

const createArmorBaseBreakdown = (
  armor: AcArmor,
  dexMod: number,
): AcBaseBreakdown => {
  const dexContribution = getArmorDexContribution(armor, dexMod);

  if (armor.category === "heavy") {
    return createBaseBreakdown("heavy_armor", `${armor.baseAc}`, [
      { label: armor.name, value: armor.baseAc },
    ]);
  }

  if (armor.category === "medium") {
    return createBaseBreakdown(
      "medium_armor",
      armor.dexCap !== null
        ? `${armor.baseAc} + min(DEX, +${armor.dexCap})`
        : `${armor.baseAc} + DEX`,
      [
        { label: armor.name, value: armor.baseAc },
        {
          label: armor.dexCap !== null ? `DEX (max +${armor.dexCap})` : "DEX",
          value: dexContribution,
        },
      ],
    );
  }

  return createBaseBreakdown("light_armor", `${armor.baseAc} + DEX`, [
    { label: armor.name, value: armor.baseAc },
    { label: "DEX", value: dexContribution },
  ]);
};

const createDefaultBase = (dexMod: number) =>
  createBaseBreakdown("default", "10 + DEX", [
    { label: "Base", value: 10 },
    { label: "DEX", value: dexMod },
  ]);

const createMageArmorBase = (dexMod: number) =>
  createBaseBreakdown("mage_armor", "13 + DEX", [
    { label: "Mage Armor", value: 13 },
    { label: "DEX", value: dexMod },
  ]);

const createBarbarianBase = (dexMod: number, conMod: number) =>
  createBaseBreakdown("barbarian_unarmored_defense", "10 + DEX + CON", [
    { label: "Base", value: 10 },
    { label: "DEX", value: dexMod },
    { label: "CON", value: conMod },
  ]);

const createMonkBase = (dexMod: number, wisMod: number) =>
  createBaseBreakdown("monk_unarmored_defense", "10 + DEX + WIS", [
    { label: "Base", value: 10 },
    { label: "DEX", value: dexMod },
    { label: "WIS", value: wisMod },
  ]);

const toAcArmor = (armor: Armor): AcArmor | null => {
  if (armor.armorType === "none") return null;
  return {
    name: armor.name,
    category: armor.armorType,
    baseAc: armor.baseAC,
    allowsDex: armor.allowsDex ?? armor.armorType !== "heavy",
    dexCap: armor.armorType === "heavy" ? 0 : armor.dexCap,
    stealthDisadvantage: armor.stealthDisadvantage ?? false,
    minStrength: armor.minStrength ?? null,
  };
};

const getIntrinsicAcEffects = (
  sheet: CharacterSheet,
  armorEquipped: AcArmor | null,
): ActiveAcEffect[] => {
  const effects: ActiveAcEffect[] = [];

  if (sheet.miscACBonus !== 0) {
    effects.push({
      id: "legacy_misc_ac_bonus",
      label: "Misc",
      bonus: sheet.miscACBonus,
      active: true,
    });
  }

  if (sheet.fightingStyle === "defense" && armorEquipped) {
    effects.push({
      id: "fighting_style_defense",
      label: "Defense",
      bonus: 1,
      active: true,
    });
  }

  return effects;
};

export const getValidAcBases = (state: CharacterAcState): AcBaseBreakdown[] => {
  const candidates: AcBaseBreakdown[] = [];

  if (state.armorEquipped) {
    candidates.push(createArmorBaseBreakdown(state.armorEquipped, state.dexMod));
    return candidates.sort(sortAcBases);
  }

  candidates.push(createDefaultBase(state.dexMod));

  if (state.hasMageArmor) {
    candidates.push(createMageArmorBase(state.dexMod));
  }

  if (state.hasBarbarianUnarmoredDefense) {
    candidates.push(createBarbarianBase(state.dexMod, state.conMod));
  }

  if (state.hasMonkUnarmoredDefense && !state.shieldEquipped) {
    candidates.push(createMonkBase(state.dexMod, state.wisMod));
  }

  return candidates.sort(sortAcBases);
};

export const calculateArmorClass = (
  state: CharacterAcState,
): AcCalculationResult => {
  const candidateBases = getValidAcBases(state);
  const [base = createDefaultBase(state.dexMod)] = candidateBases;
  const activeEffects = state.activeAcEffects
    .filter((effect) => effect.active && effect.bonus !== 0)
    .map(({ id, label, bonus }) => ({ id, label, bonus }));
  const shield = state.shieldEquipped ? SHIELD_BONUS : 0;
  const totalBonus =
    shield + activeEffects.reduce((sum, effect) => sum + effect.bonus, 0);

  return {
    base,
    bonuses: {
      shield,
      effects: activeEffects,
      totalBonus,
    },
    total: base.value + totalBonus,
    candidateBases,
  };
};

export const getArmorClassBreakdownRows = (
  result: AcCalculationResult,
): AcBreakdownPart[] => [
  ...result.base.parts,
  ...(result.bonuses.shield > 0
    ? [{ label: "Shield", value: result.bonuses.shield }]
    : []),
  ...result.bonuses.effects.map((effect) => ({
    label: effect.label,
    value: effect.bonus,
  })),
];

export const buildCharacterAcStateFromSheet = (
  sheet: CharacterSheet,
  options: BuildCharacterAcStateOptions = {},
): CharacterAcState => {
  const armorEquipped = toAcArmor(sheet.equippedArmor);

  return {
    dexMod: getModifier(sheet.abilities.dexterity),
    conMod: getModifier(sheet.abilities.constitution),
    wisMod: getModifier(sheet.abilities.wisdom),
    armorEquipped,
    shieldEquipped: Boolean(sheet.equippedShield),
    hasBarbarianUnarmoredDefense:
      options.hasBarbarianUnarmoredDefense ?? sheet.class === "barbarian",
    hasMonkUnarmoredDefense:
      options.hasMonkUnarmoredDefense ?? sheet.class === "monk",
    hasMageArmor: options.hasMageArmor ?? false,
    activeAcEffects: [
      ...getIntrinsicAcEffects(sheet, armorEquipped),
      ...(options.activeAcEffects ?? []),
    ],
  };
};
