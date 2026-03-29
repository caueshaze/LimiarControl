export const DRACONIC_ANCESTRIES = [
  { id: "black", label: "Negro", damageLabel: "Ácido", damageType: "acid", resistanceType: "acid", breathWeaponShape: "line", breathWeaponSaveType: "dexterity", breathWeaponAreaSize: "1.5m x 9m" },
  { id: "blue", label: "Azul", damageLabel: "Elétrico", damageType: "lightning", resistanceType: "lightning", breathWeaponShape: "line", breathWeaponSaveType: "dexterity", breathWeaponAreaSize: "1.5m x 9m" },
  { id: "brass", label: "Latão", damageLabel: "Fogo", damageType: "fire", resistanceType: "fire", breathWeaponShape: "line", breathWeaponSaveType: "dexterity", breathWeaponAreaSize: "1.5m x 9m" },
  { id: "bronze", label: "Bronze", damageLabel: "Elétrico", damageType: "lightning", resistanceType: "lightning", breathWeaponShape: "line", breathWeaponSaveType: "dexterity", breathWeaponAreaSize: "1.5m x 9m" },
  { id: "copper", label: "Cobre", damageLabel: "Ácido", damageType: "acid", resistanceType: "acid", breathWeaponShape: "line", breathWeaponSaveType: "dexterity", breathWeaponAreaSize: "1.5m x 9m" },
  { id: "gold", label: "Ouro", damageLabel: "Fogo", damageType: "fire", resistanceType: "fire", breathWeaponShape: "cone", breathWeaponSaveType: "constitution", breathWeaponAreaSize: "4.5m" },
  { id: "green", label: "Verde", damageLabel: "Veneno", damageType: "poison", resistanceType: "poison", breathWeaponShape: "cone", breathWeaponSaveType: "constitution", breathWeaponAreaSize: "4.5m" },
  { id: "red", label: "Vermelho", damageLabel: "Fogo", damageType: "fire", resistanceType: "fire", breathWeaponShape: "cone", breathWeaponSaveType: "constitution", breathWeaponAreaSize: "4.5m" },
  { id: "silver", label: "Prata", damageLabel: "Frio", damageType: "cold", resistanceType: "cold", breathWeaponShape: "cone", breathWeaponSaveType: "constitution", breathWeaponAreaSize: "4.5m" },
  { id: "white", label: "Branco", damageLabel: "Frio", damageType: "cold", resistanceType: "cold", breathWeaponShape: "cone", breathWeaponSaveType: "constitution", breathWeaponAreaSize: "4.5m" },
] as const;

export type DraconicAncestry = (typeof DRACONIC_ANCESTRIES)[number];
export type DraconicAncestryId = DraconicAncestry["id"];
export type DraconicDamageType = DraconicAncestry["damageType"];
export type DraconicResistanceType = DraconicAncestry["resistanceType"];
export type DraconicBreathWeaponShape = DraconicAncestry["breathWeaponShape"];
export type DraconicBreathWeaponSaveType = DraconicAncestry["breathWeaponSaveType"];
export type DraconicLineageState = {
  ancestry: DraconicAncestryId | null;
  ancestryLabel: string | null;
  damageType: DraconicDamageType | null;
  resistanceType: DraconicResistanceType | null;
  hasElementalAffinity: boolean;
  resistances: DraconicResistanceType[];
};

type DraconicLineageInput = {
  classId?: string | null | undefined;
  subclass?: string | null | undefined;
  level?: number | null | undefined;
  subclassConfig?: Record<string, string> | null | undefined;
};

const DRACONIC_ANCESTRY_BY_ID = Object.fromEntries(
  DRACONIC_ANCESTRIES.map((ancestry) => [ancestry.id, ancestry]),
) as Record<DraconicAncestryId, DraconicAncestry>;

export const DRACONIC_ANCESTRY_DAMAGE_TYPES = Object.fromEntries(
  DRACONIC_ANCESTRIES.map((ancestry) => [ancestry.id, ancestry.damageType]),
) as Record<DraconicAncestryId, DraconicDamageType>;

export const DRACONIC_ANCESTRY_OPTIONS: Array<{
  id: DraconicAncestryId;
  name: string;
}> = DRACONIC_ANCESTRIES.map((ancestry) => ({
  id: ancestry.id,
  name: `${ancestry.label} (${ancestry.damageLabel})`,
}));

export const DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY = "draconicAncestry";
export const LEGACY_DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY = "dragonAncestor";

export const isValidDraconicAncestry = (
  value: string | null | undefined,
): value is DraconicAncestryId =>
  !!value && value in DRACONIC_ANCESTRY_DAMAGE_TYPES;

export const getDraconicAncestry = (
  ancestry: string | null | undefined,
): DraconicAncestry | null =>
  isValidDraconicAncestry(ancestry) ? DRACONIC_ANCESTRY_BY_ID[ancestry] : null;

export const getDraconicAncestryLabel = (
  ancestry: string | null | undefined,
): string | null =>
  getDraconicAncestry(ancestry)?.label ?? null;

export const getDraconicDamageType = (
  ancestry: string | null | undefined,
): DraconicDamageType | null =>
  getDraconicAncestry(ancestry)?.damageType ?? null;

export const getDraconicResistanceType = (
  ancestry: string | null | undefined,
): DraconicResistanceType | null =>
  getDraconicAncestry(ancestry)?.resistanceType ?? null;

export const getDraconicBreathWeaponShape = (
  ancestry: string | null | undefined,
): DraconicBreathWeaponShape | null =>
  getDraconicAncestry(ancestry)?.breathWeaponShape ?? null;

export const getDraconicBreathWeaponSaveType = (
  ancestry: string | null | undefined,
): DraconicBreathWeaponSaveType | null =>
  getDraconicAncestry(ancestry)?.breathWeaponSaveType ?? null;

export const getDraconicBreathWeaponAreaSize = (
  ancestry: string | null | undefined,
): string | null =>
  getDraconicAncestry(ancestry)?.breathWeaponAreaSize ?? null;

export const getDraconicLineageState = ({
  classId,
  subclass,
  level,
  subclassConfig,
}: DraconicLineageInput): DraconicLineageState => {
  const normalizedSubclass = String(subclass ?? "").trim().toLowerCase();
  const normalizedClassId = String(classId ?? "").trim().toLowerCase();
  if (normalizedClassId && normalizedClassId !== "sorcerer") {
    return {
      ancestry: null,
      ancestryLabel: null,
      damageType: null,
      resistanceType: null,
      hasElementalAffinity: false,
      resistances: [],
    };
  }
  if (normalizedSubclass !== "draconic_bloodline") {
    return {
      ancestry: null,
      ancestryLabel: null,
      damageType: null,
      resistanceType: null,
      hasElementalAffinity: false,
      resistances: [],
    };
  }

  const ancestryValue = subclassConfig?.[DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY];
  const ancestry = isValidDraconicAncestry(ancestryValue) ? ancestryValue : null;
  const ancestryData = ancestry ? getDraconicAncestry(ancestry) : null;
  const damageType = ancestryData?.damageType ?? null;
  const resistanceType = ancestryData?.resistanceType ?? null;
  const hasElementalAffinity = Number(level ?? 0) >= 6 && !!damageType;

  return {
    ancestry,
    ancestryLabel: ancestryData?.label ?? null,
    damageType,
    resistanceType,
    hasElementalAffinity,
    resistances: hasElementalAffinity && resistanceType ? [resistanceType] : [],
  };
};

export const resolveElementalAffinityEligibility = ({
  classId,
  subclass,
  level,
  subclassConfig,
  spellDamageType,
  charismaScore,
}: DraconicLineageInput & {
  spellDamageType?: string | null | undefined;
  charismaScore?: number | null | undefined;
}) => {
  const lineage = getDraconicLineageState({ classId, subclass, level, subclassConfig });
  const normalizedSpellDamageType = String(spellDamageType ?? "").trim().toLowerCase() || null;
  const eligible = Boolean(
    lineage.hasElementalAffinity &&
    lineage.damageType &&
    normalizedSpellDamageType &&
    lineage.damageType === normalizedSpellDamageType,
  );

  return {
    eligible,
    damageType: eligible ? lineage.damageType : lineage.damageType,
    bonus:
      eligible && typeof charismaScore === "number"
        ? Math.floor((charismaScore - 10) / 2)
        : null,
  };
};

export const normalizeSubclassConfig = (
  subclass: string | null | undefined,
  subclassConfig: Record<string, string> | null | undefined,
): Record<string, string> | null => {
  if (!subclassConfig) {
    return null;
  }

  const nextConfig = Object.fromEntries(
    Object.entries(subclassConfig)
      .map(([key, value]) => [
        key === LEGACY_DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY
          ? DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY
          : key,
        value,
      ])
      .filter(([, value]) => typeof value === "string" && value.trim().length > 0),
  ) as Record<string, string>;

  if (subclass !== "draconic_bloodline") {
    delete nextConfig[DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY];
  }

  return Object.keys(nextConfig).length > 0 ? nextConfig : null;
};
