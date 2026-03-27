import type { AbilityName, SkillName } from "../model/characterSheet.types";
import { SKILL_NAMES } from "../constants";
import { getDragonbornAncestry, isDragonbornAncestryId } from "./dragonbornAncestries";
import {
  RACE_DEFINITIONS,
  type RaceConfigField,
  type RaceDefinition,
  type RaceDefinitionVariant,
  type RaceStructuredFeature,
  type RaceToolProficiencyChoice,
} from "./raceDefinitions";

type RaceConfig = {
  dragonbornAncestry?: string | null;
  gnomeSubrace?: string | null;
  halfElfAbilityChoices?: AbilityName[];
  halfElfSkillChoices?: SkillName[];
} | null | undefined;

export type Race = {
  id: string;
  name: string;
  size: "Pequeno" | "Médio";
  darkvisionMeters: number | null;
  languages: string[];
  abilityBonuses: Partial<Record<AbilityName, number>>;
  speedMeters: number;
  traits: string[];
  weaponProficiencies?: string[];
  armorProficiencies?: string[];
  skillProficiencies?: SkillName[];
  toolProficiencyChoices?: RaceToolProficiencyChoice;
  structuredFeatures: RaceStructuredFeature[];
};

type NormalizedRaceState = {
  raceId: string;
  raceConfig: NonNullable<RaceConfig> | null;
};

const LEGACY_RACE_ALIASES: Record<string, { raceId: string; raceConfig: NonNullable<RaceConfig> }> = {
  "forest-gnome": { raceId: "gnome", raceConfig: { gnomeSubrace: "forest" } },
  "rock-gnome": { raceId: "gnome", raceConfig: { gnomeSubrace: "rock" } },
};

const TOOL_LABELS_BY_CANONICAL_KEY: Record<string, string> = {
  tinkers_tools: "Ferramentas de Engenhoqueiro",
};

const mergeAbilityBonuses = (
  base: Partial<Record<AbilityName, number>>,
  extra?: Partial<Record<AbilityName, number>>,
) => {
  const next = { ...base };
  if (!extra) return next;
  for (const [key, bonus] of Object.entries(extra)) {
    const abilityKey = key as AbilityName;
    next[abilityKey] = (next[abilityKey] ?? 0) + (bonus ?? 0);
  }
  return next;
};

const getBaseRaceDefinition = (raceId: string): RaceDefinition | undefined => {
  const normalizedId = LEGACY_RACE_ALIASES[raceId]?.raceId ?? raceId;
  return RACE_DEFINITIONS.find((race) => race.id === normalizedId);
};

const getGnomeSubraceId = (raceConfig: RaceConfig): string | null => {
  const subrace = raceConfig?.gnomeSubrace;
  return subrace === "forest" || subrace === "rock" ? subrace : null;
};

const HALF_ELF_ABILITY_OPTIONS: AbilityName[] = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
];

const normalizeHalfElfAbilityChoices = (choices: unknown): AbilityName[] => {
  if (!Array.isArray(choices)) return [];
  const unique = new Set<AbilityName>();
  for (const entry of choices) {
    if (typeof entry !== "string") continue;
    if (!HALF_ELF_ABILITY_OPTIONS.includes(entry as AbilityName)) continue;
    unique.add(entry as AbilityName);
  }
  return [...unique].slice(0, 2);
};

const normalizeHalfElfSkillChoices = (choices: unknown): SkillName[] => {
  if (!Array.isArray(choices)) return [];
  const unique = new Set<SkillName>();
  for (const entry of choices) {
    if (typeof entry !== "string") continue;
    if (!SKILL_NAMES.includes(entry as SkillName)) continue;
    unique.add(entry as SkillName);
  }
  return [...unique].slice(0, 2);
};

export const normalizeRaceState = (
  raceId: string,
  raceConfig: RaceConfig,
): NormalizedRaceState => {
  const alias = LEGACY_RACE_ALIASES[raceId];
  const normalizedRaceId = alias?.raceId ?? raceId;
  const mergedConfig = alias ? { ...(raceConfig ?? {}), ...alias.raceConfig } : (raceConfig ?? null);

  if (normalizedRaceId === "dragonborn") {
    return {
      raceId: normalizedRaceId,
      raceConfig: {
        dragonbornAncestry: isDragonbornAncestryId(mergedConfig?.dragonbornAncestry)
          ? mergedConfig?.dragonbornAncestry
          : null,
      },
    };
  }

  if (normalizedRaceId === "gnome") {
    return {
      raceId: normalizedRaceId,
      raceConfig: {
        gnomeSubrace: getGnomeSubraceId(mergedConfig),
      },
    };
  }

  if (normalizedRaceId === "half-elf") {
    return {
      raceId: normalizedRaceId,
      raceConfig: {
        halfElfAbilityChoices: normalizeHalfElfAbilityChoices(mergedConfig?.halfElfAbilityChoices),
        halfElfSkillChoices: normalizeHalfElfSkillChoices(mergedConfig?.halfElfSkillChoices),
      },
    };
  }

  return { raceId: normalizedRaceId, raceConfig: null };
};

const getVariantData = (raceId: string, raceConfig: RaceConfig) => {
  if (raceId === "dragonborn") {
    const ancestry = getDragonbornAncestry(raceConfig?.dragonbornAncestry);
    if (!ancestry) return null;
    return {
      name: `Draconato (${ancestry.label})`,
      traits: [
        `Ancestralidade Dracônica: ${ancestry.label}`,
        `Resistência: ${ancestry.resistanceType}`,
        `Sopro de Dragão: ${ancestry.damageType}, ${ancestry.area.shape} ${ancestry.area.size}, teste ${ancestry.saveAbility}`,
      ],
      structuredFeatures: [
        { id: "dragonborn-ancestry", label: `Ancestralidade Dracônica: ${ancestry.label}`, kind: "passive" as const },
        { id: "dragonborn-resistance", label: `Resistência: ${ancestry.resistanceType}`, kind: "passive" as const },
        { id: "dragonborn-breath", label: `Sopro de Dragão: ${ancestry.damageType}, ${ancestry.area.shape} ${ancestry.area.size}, teste ${ancestry.saveAbility}`, kind: "passive" as const },
      ],
    };
  }

  if (raceId === "gnome") {
    const definition = getBaseRaceDefinition(raceId);
    const subraceId = getGnomeSubraceId(raceConfig);
    return subraceId ? definition?.variants?.[subraceId] ?? null : null;
  }

  if (raceId === "half-elf") {
    const abilityChoices = normalizeHalfElfAbilityChoices(raceConfig?.halfElfAbilityChoices);
    const skillChoices = normalizeHalfElfSkillChoices(raceConfig?.halfElfSkillChoices);
    return {
      abilityBonuses: abilityChoices.reduce<Partial<Record<AbilityName, number>>>((acc, ability) => {
        acc[ability] = (acc[ability] ?? 0) + 1;
        return acc;
      }, {}),
      skillProficiencies: skillChoices,
    };
  }

  return null;
};

export const getRace = (raceId: string, raceConfig: RaceConfig = null): Race | undefined => {
  const normalized = normalizeRaceState(raceId, raceConfig);
  const base = getBaseRaceDefinition(normalized.raceId);
  if (!base) return undefined;

  const variant = getVariantData(normalized.raceId, normalized.raceConfig);
  const variantData = variant as Partial<RaceDefinitionVariant> | null;
  const variantFeatures = variantData?.structuredFeatures ?? [];
  const variantTraits = variantData?.traits ?? [];
  const variantAbilityBonuses = variantData?.abilityBonuses;
  const variantWeaponProficiencies = variantData?.weaponProficiencies ?? [];
  const variantArmorProficiencies = variantData?.armorProficiencies ?? [];
  const variantSkillProficiencies = variantData?.skillProficiencies ?? [];
  const variantToolChoices = variantData?.toolProficiencyChoices;

  const structuredFeatures = [
    ...(base.structuredFeatures ?? []),
    ...variantFeatures,
  ];
  const traits = structuredFeatures.length > 0
    ? structuredFeatures.map((feature) => feature.label)
    : [...base.traits, ...variantTraits];

  return {
    id: base.id,
    name: variantData?.name ?? base.name,
    size: base.size,
    darkvisionMeters: base.darkvisionMeters,
    languages: base.languages,
    abilityBonuses: mergeAbilityBonuses(base.abilityBonuses, variantAbilityBonuses),
    speedMeters: base.speedMeters,
    traits,
    weaponProficiencies: [...new Set([...(base.weaponProficiencies ?? []), ...variantWeaponProficiencies])],
    armorProficiencies: [...new Set([...(base.armorProficiencies ?? []), ...variantArmorProficiencies])],
    skillProficiencies: [...new Set([...(base.skillProficiencies ?? []), ...variantSkillProficiencies])],
    toolProficiencyChoices: variantToolChoices ?? base.toolProficiencyChoices,
    structuredFeatures,
  };
};

export const getRaceConfigFields = (raceId: string): RaceConfigField[] =>
  getBaseRaceDefinition(normalizeRaceState(raceId, null).raceId)?.configFields ?? [];

export const getRaceFixedToolProficiencies = (
  raceId: string,
  raceConfig: RaceConfig = null,
): string[] => {
  const race = getRace(raceId, raceConfig);
  if (!race) return [];
  return race.structuredFeatures
    .filter((feature): feature is Extract<RaceStructuredFeature, { kind: "tool_proficiency" }> => feature.kind === "tool_proficiency")
    .map((feature) => TOOL_LABELS_BY_CANONICAL_KEY[feature.toolCanonicalKey] ?? feature.label);
};

export const isRaceConfigValid = (raceId: string, raceConfig: RaceConfig = null) =>
  getRaceConfigFields(raceId).every((field) => {
    const value = raceConfig?.[field.key];
    if (field.kind === "ability_multi") {
      if (!Array.isArray(value)) return !field.required;
      if (value.length !== field.count) return false;
      const unique = new Set(value);
      if (unique.size !== value.length) return false;
      const excluded = new Set(field.exclude ?? []);
      return value.every((entry) =>
        HALF_ELF_ABILITY_OPTIONS.includes(entry as AbilityName) && !excluded.has(entry as AbilityName),
      );
    }
    if (field.kind === "skill_multi") {
      if (!Array.isArray(value)) return !field.required;
      if (value.length !== field.count) return false;
      return new Set(value).size === value.length && value.every((entry) => SKILL_NAMES.includes(entry as SkillName));
    }
    if (!field.required && !value) return true;
    return field.options.some((option) => option.id === value);
  });

export const RACES = RACE_DEFINITIONS
  .filter((race) => race.selectable !== false && !LEGACY_RACE_ALIASES[race.id])
  .map((race) => getRace(race.id)!)
  .filter(Boolean);
