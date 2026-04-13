import {
  DRACONIC_ANCESTRIES,
  getDraconicAncestry,
  getDraconicDamageType,
  getDraconicResistanceType,
  getDraconicBreathWeaponAreaSize,
  getDraconicBreathWeaponSaveType,
  getDraconicBreathWeaponShape,
  type DraconicAncestry,
  type DraconicAncestryId,
  type DraconicBreathWeaponSaveType,
  type DraconicBreathWeaponShape,
  type DraconicDamageType,
  type DraconicResistanceType,
} from "./draconicAncestry";
import { getModifier, getProficiencyBonus } from "../utils/calculations";

export type DragonbornAncestry = DraconicAncestry;
export type DragonbornAncestryId = DraconicAncestryId;
export type DragonbornDamageType = DraconicDamageType;
export type DragonbornResistanceType = DraconicResistanceType;
export type DragonbornBreathWeaponShape = DraconicBreathWeaponShape;
export type DragonbornBreathWeaponSaveType = DraconicBreathWeaponSaveType;

type DragonbornRaceConfig = {
  draconicAncestry?: string | null;
  dragonbornAncestry?: string | null;
  dragonAncestor?: string | null;
} | null | undefined;

export type DragonbornLineageState = {
  ancestry: DragonbornAncestryId | null;
  ancestryLabel: string | null;
  damageType: DragonbornDamageType | null;
  resistanceType: DragonbornResistanceType | null;
  breathWeaponShape: DragonbornBreathWeaponShape | null;
  breathWeaponSaveType: DragonbornBreathWeaponSaveType | null;
  breathWeaponAreaSize: string | null;
  resistances: DragonbornResistanceType[];
};

export const DRAGONBORN_DRACONIC_ANCESTRY_RACE_CONFIG_KEY = "draconicAncestry";
export const LEGACY_DRAGONBORN_ANCESTRY_RACE_CONFIG_KEY = "dragonbornAncestry";
export const LEGACY_DRAGONBORN_DRAGON_ANCESTOR_RACE_CONFIG_KEY = "dragonAncestor";

export const DRAGONBORN_ANCESTRIES = DRACONIC_ANCESTRIES;

export const getDragonbornAncestry = (id: string | null | undefined): DragonbornAncestry | undefined =>
  getDraconicAncestry(id) ?? undefined;

export const isDragonbornAncestryId = (id: string | null | undefined): id is DragonbornAncestryId =>
  !!getDragonbornAncestry(id);

export const getDragonbornDamageType = (
  ancestry: string | null | undefined,
): DragonbornDamageType | null => getDraconicDamageType(ancestry);

export const getDragonbornResistanceType = (
  ancestry: string | null | undefined,
): DragonbornResistanceType | null => getDraconicResistanceType(ancestry);

export const getDragonbornBreathWeaponShape = (
  ancestry: string | null | undefined,
): DragonbornBreathWeaponShape | null => getDraconicBreathWeaponShape(ancestry);

export const getDragonbornBreathWeaponSaveType = (
  ancestry: string | null | undefined,
): DragonbornBreathWeaponSaveType | null => getDraconicBreathWeaponSaveType(ancestry);

export const getDragonbornBreathWeaponAreaSize = (
  ancestry: string | null | undefined,
): string | null => getDraconicBreathWeaponAreaSize(ancestry);

export const getDragonbornBreathWeaponDamageDice = (level: number): string => {
  const normalizedLevel = Math.max(1, Math.trunc(level || 1));
  if (normalizedLevel >= 17) return "5d6";
  if (normalizedLevel >= 11) return "4d6";
  if (normalizedLevel >= 5) return "3d6";
  return "2d6";
};

export const getDragonbornBreathWeaponDC = (character: {
  level: number;
  abilities?: Partial<Record<"constitution", number>> | null;
}): number => {
  const constitutionScore = character.abilities?.constitution ?? 10;
  return 8 + getProficiencyBonus(character.level) + getModifier(constitutionScore);
};

export const normalizeDragonbornRaceConfig = (
  raceConfig: DragonbornRaceConfig,
): { draconicAncestry: DragonbornAncestryId | null } | null => {
  if (!raceConfig) {
    return { draconicAncestry: null };
  }

  const rawAncestry =
    raceConfig[DRAGONBORN_DRACONIC_ANCESTRY_RACE_CONFIG_KEY]
    ?? raceConfig[LEGACY_DRAGONBORN_ANCESTRY_RACE_CONFIG_KEY]
    ?? raceConfig[LEGACY_DRAGONBORN_DRAGON_ANCESTOR_RACE_CONFIG_KEY];
  const ancestry = isDragonbornAncestryId(rawAncestry) ? rawAncestry : null;

  return { draconicAncestry: ancestry };
};

export const resolveDragonbornLineageState = ({
  raceId,
  raceConfig,
}: {
  raceId?: string | null | undefined;
  raceConfig?: DragonbornRaceConfig;
}): DragonbornLineageState => {
  if (String(raceId ?? "").trim().toLowerCase() !== "dragonborn") {
    return {
      ancestry: null,
      ancestryLabel: null,
      damageType: null,
      resistanceType: null,
      breathWeaponShape: null,
      breathWeaponSaveType: null,
      breathWeaponAreaSize: null,
      resistances: [],
    };
  }

  const ancestry = normalizeDragonbornRaceConfig(raceConfig)?.draconicAncestry ?? null;
  const ancestryData = ancestry ? getDragonbornAncestry(ancestry) : undefined;

  return {
    ancestry,
    ancestryLabel: ancestryData?.label ?? null,
    damageType: ancestryData?.damageType ?? null,
    resistanceType: ancestryData?.resistanceType ?? null,
    breathWeaponShape: ancestryData?.breathWeaponShape ?? null,
    breathWeaponSaveType: ancestryData?.breathWeaponSaveType ?? null,
    breathWeaponAreaSize: ancestryData?.breathWeaponAreaSize ?? null,
    resistances: ancestryData?.resistanceType ? [ancestryData.resistanceType] : [],
  };
};
