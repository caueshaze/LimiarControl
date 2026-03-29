import type {
  BaseItem,
  BaseItemArmorCategory,
  BaseItemCostUnit,
  BaseItemDamageType,
  BaseItemDexBonusRule,
  BaseItemEquipmentCategory,
  BaseItemKind,
  BaseItemSource,
  BaseItemWeaponCategory,
  BaseItemWeaponRangeType,
} from "../../entities/base-item";
import {
  BaseItemArmorCategory as BaseItemArmorCategoryValues,
  BaseItemCostUnit as BaseItemCostUnitValues,
  BaseItemDamageType as BaseItemDamageTypeValues,
  BaseItemDexBonusRule as BaseItemDexBonusRuleValues,
  BaseItemEquipmentCategory as BaseItemEquipmentCategoryValues,
  BaseItemKind as BaseItemKindValues,
  BaseItemSource as BaseItemSourceValues,
  BaseItemWeaponCategory as BaseItemWeaponCategoryValues,
  BaseItemWeaponRangeType as BaseItemWeaponRangeTypeValues,
} from "../../entities/base-item";
import type { ItemPropertySlug } from "../../entities/item";

export type ActiveFilter = "all" | "active" | "inactive";
export type ItemKindFilter = "ALL" | BaseItemKind;
export type EquipmentCategoryFilter = "ALL" | BaseItemEquipmentCategory;

export type FormState = {
  system: BaseItem["system"];
  canonicalKey: string;
  nameEn: string;
  namePt: string;
  descriptionEn: string;
  descriptionPt: string;
  itemKind: BaseItemKind;
  equipmentCategory: BaseItemEquipmentCategory | "";
  costQuantity: string;
  costUnit: BaseItemCostUnit | "";
  weight: string;
  weaponCategory: BaseItemWeaponCategory | "";
  weaponRangeType: BaseItemWeaponRangeType | "";
  damageDice: string;
  damageType: BaseItemDamageType | "";
  healDice: string;
  healBonus: string;
  rangeNormalMeters: string;
  rangeLongMeters: string;
  versatileDamage: string;
  weaponPropertiesJson: ItemPropertySlug[];
  armorCategory: BaseItemArmorCategory | "";
  armorClassBase: string;
  dexBonusRule: BaseItemDexBonusRule | "";
  strengthRequirement: string;
  stealthDisadvantage: boolean;
  source: BaseItemSource;
  sourceRef: string;
  isSrd: boolean;
  isActive: boolean;
};

export {
  BaseItemArmorCategoryValues,
  BaseItemSourceValues,
  BaseItemKindValues,
  BaseItemWeaponRangeTypeValues,
};

export const SYSTEM_OPTIONS = ["DND5E"] as const;
export const ITEM_KIND_OPTIONS = Object.values(BaseItemKindValues);
export const EQUIPMENT_CATEGORY_OPTIONS = Object.values(BaseItemEquipmentCategoryValues);
export const COST_UNIT_OPTIONS = Object.values(BaseItemCostUnitValues);
export const WEAPON_CATEGORY_OPTIONS = Object.values(BaseItemWeaponCategoryValues);
export const WEAPON_RANGE_OPTIONS = Object.values(BaseItemWeaponRangeTypeValues);
export const ARMOR_CATEGORY_OPTIONS = Object.values(BaseItemArmorCategoryValues);
export const DAMAGE_TYPE_OPTIONS = Object.values(BaseItemDamageTypeValues);
export const DEX_BONUS_RULE_OPTIONS = Object.values(BaseItemDexBonusRuleValues);
export const SOURCE_OPTIONS = Object.values(BaseItemSourceValues);

export const inputClassName =
  "w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-amber-400/50 focus:outline-none";
export const panelClassName =
  "rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(14,17,31,0.92),rgba(3,7,18,0.98))] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.35)]";
