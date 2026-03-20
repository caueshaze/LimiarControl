import type { CampaignSystemType } from "../campaign";

export const BaseItemKind = {
  WEAPON: "weapon",
  ARMOR: "armor",
  GEAR: "gear",
  TOOL: "tool",
  CONSUMABLE: "consumable",
  FOCUS: "focus",
  AMMO: "ammo",
  PACK: "pack",
} as const;

export type BaseItemKind = (typeof BaseItemKind)[keyof typeof BaseItemKind];

export const BaseItemCostUnit = {
  CP: "cp",
  SP: "sp",
  EP: "ep",
  GP: "gp",
  PP: "pp",
} as const;

export type BaseItemCostUnit =
  (typeof BaseItemCostUnit)[keyof typeof BaseItemCostUnit];

export const BaseItemWeaponCategory = {
  SIMPLE: "simple",
  MARTIAL: "martial",
} as const;

export type BaseItemWeaponCategory =
  (typeof BaseItemWeaponCategory)[keyof typeof BaseItemWeaponCategory];

export const BaseItemWeaponRangeType = {
  MELEE: "melee",
  RANGED: "ranged",
} as const;

export type BaseItemWeaponRangeType =
  (typeof BaseItemWeaponRangeType)[keyof typeof BaseItemWeaponRangeType];

export const BaseItemArmorCategory = {
  LIGHT: "light",
  MEDIUM: "medium",
  HEAVY: "heavy",
  SHIELD: "shield",
} as const;

export type BaseItemArmorCategory =
  (typeof BaseItemArmorCategory)[keyof typeof BaseItemArmorCategory];

export type BaseItemAlias = {
  id: string;
  alias: string;
  locale?: string | null;
  aliasType?: string | null;
};

export type BaseItem = {
  id: string;
  system: CampaignSystemType;
  canonicalKey: string;
  nameEn: string;
  namePt: string;
  descriptionEn?: string | null;
  descriptionPt?: string | null;
  itemKind: BaseItemKind;
  equipmentCategory?: string | null;
  costQuantity?: number | null;
  costUnit?: BaseItemCostUnit | null;
  weight?: number | null;
  weaponCategory?: BaseItemWeaponCategory | null;
  weaponRangeType?: BaseItemWeaponRangeType | null;
  damageDice?: string | null;
  damageType?: string | null;
  rangeNormal?: number | null;
  rangeLong?: number | null;
  versatileDamage?: string | null;
  weaponPropertiesJson?: unknown;
  armorCategory?: BaseItemArmorCategory | null;
  armorClassBase?: number | null;
  dexBonusRule?: string | null;
  strengthRequirement?: number | null;
  stealthDisadvantage?: boolean | null;
  isShield: boolean;
  source?: string | null;
  sourceRef?: string | null;
  isSrd: boolean;
  isActive: boolean;
  aliases: BaseItemAlias[];
};

export type BaseItemFilters = {
  system?: CampaignSystemType;
  itemKind?: BaseItemKind;
  canonicalKey?: string;
};
