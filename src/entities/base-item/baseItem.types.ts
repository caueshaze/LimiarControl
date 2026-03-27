import type { CampaignSystemType } from "../campaign";
import type { ItemPropertySlug } from "../item/itemProperties";

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

export const BaseItemEquipmentCategory = {
  ADVENTURING_PACK: "adventuring_pack",
  AMMUNITION: "ammunition",
  BOOK: "book",
  CLOTHING: "clothing",
  CONSUMABLE_SUPPLY: "consumable_supply",
  CONTAINER: "container",
  DOCUMENT: "document",
  GAMING_SET: "gaming_set",
  INSIGNIA: "insignia",
  JEWELRY: "jewelry",
  MEMENTO: "memento",
  MUSICAL_INSTRUMENT: "musical_instrument",
  PET: "pet",
  ROPE: "rope",
  SAILING_GEAR: "sailing_gear",
  SPELLCASTING_FOCUS: "spellcasting_focus",
  SPELLCASTING_GEAR: "spellcasting_gear",
  SUPPLIES: "supplies",
  TOOLS: "tools",
  TROPHY: "trophy",
  UTILITY_TOOL: "utility_tool",
  VEHICLE_PROFICIENCY: "vehicle_proficiency",
  WRITING_SUPPLY: "writing_supply",
} as const;

export type BaseItemEquipmentCategory =
  (typeof BaseItemEquipmentCategory)[keyof typeof BaseItemEquipmentCategory];

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

export const BaseItemDamageType = {
  ACID: "acid",
  BLUDGEONING: "bludgeoning",
  COLD: "cold",
  FIRE: "fire",
  FORCE: "force",
  LIGHTNING: "lightning",
  NECROTIC: "necrotic",
  PIERCING: "piercing",
  POISON: "poison",
  PSYCHIC: "psychic",
  RADIANT: "radiant",
  SLASHING: "slashing",
  THUNDER: "thunder",
} as const;

export type BaseItemDamageType =
  (typeof BaseItemDamageType)[keyof typeof BaseItemDamageType];

export const BaseItemDexBonusRule = {
  FULL: "full",
  MAX_2: "max_2",
  NONE: "none",
} as const;

export type BaseItemDexBonusRule =
  (typeof BaseItemDexBonusRule)[keyof typeof BaseItemDexBonusRule];

export const BaseItemSource = {
  ADMIN_PANEL: "admin_panel",
  SEED_JSON_BOOTSTRAP: "seed_json_bootstrap",
} as const;

export type BaseItemSource =
  (typeof BaseItemSource)[keyof typeof BaseItemSource];

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
  equipmentCategory?: BaseItemEquipmentCategory | null;
  costQuantity?: number | null;
  costUnit?: BaseItemCostUnit | null;
  weight?: number | null;
  weaponCategory?: BaseItemWeaponCategory | null;
  weaponRangeType?: BaseItemWeaponRangeType | null;
  damageDice?: string | null;
  damageType?: BaseItemDamageType | null;
  rangeNormalMeters?: number | null;
  rangeLongMeters?: number | null;
  versatileDamage?: string | null;
  weaponPropertiesJson?: ItemPropertySlug[] | null;
  armorCategory?: BaseItemArmorCategory | null;
  armorClassBase?: number | null;
  dexBonusRule?: BaseItemDexBonusRule | null;
  strengthRequirement?: number | null;
  stealthDisadvantage?: boolean | null;
  isShield: boolean;
  source?: BaseItemSource | null;
  sourceRef?: string | null;
  isSrd: boolean;
  isActive: boolean;
  aliases: BaseItemAlias[];
};

export type BaseItemFilters = {
  system?: CampaignSystemType;
  itemKind?: BaseItemKind;
  canonicalKey?: string;
  search?: string;
  equipmentCategory?: BaseItemEquipmentCategory;
  isActive?: boolean;
};

export type BaseItemWritePayload = {
  system: CampaignSystemType;
  canonicalKey: string;
  nameEn?: string | null;
  namePt?: string | null;
  descriptionEn?: string | null;
  descriptionPt?: string | null;
  itemKind: BaseItemKind;
  equipmentCategory?: BaseItemEquipmentCategory | null;
  costQuantity?: number | null;
  costUnit?: BaseItemCostUnit | null;
  weight?: number | null;
  weaponCategory?: BaseItemWeaponCategory | null;
  weaponRangeType?: BaseItemWeaponRangeType | null;
  damageDice?: string | null;
  damageType?: BaseItemDamageType | null;
  rangeNormalMeters?: number | null;
  rangeLongMeters?: number | null;
  versatileDamage?: string | null;
  weaponPropertiesJson?: ItemPropertySlug[];
  armorCategory?: BaseItemArmorCategory | null;
  armorClassBase?: number | null;
  dexBonusRule?: BaseItemDexBonusRule | null;
  strengthRequirement?: number | null;
  stealthDisadvantage?: boolean;
  isShield?: boolean;
  source?: BaseItemSource | null;
  sourceRef?: string | null;
  isSrd?: boolean;
  isActive?: boolean;
};
