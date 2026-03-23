import type {
  BaseItemArmorCategory,
  BaseItemCostUnit,
  BaseItemKind,
  BaseItemWeaponCategory,
  BaseItemWeaponRangeType,
} from "../base-item";
import type { ItemPropertySlug } from "./itemProperties";

export const ItemType = {
  WEAPON: "WEAPON",
  ARMOR: "ARMOR",
  CONSUMABLE: "CONSUMABLE",
  MISC: "MISC",
  MAGIC: "MAGIC",
} as const;

export type ItemType = (typeof ItemType)[keyof typeof ItemType];

export type Item = {
  id: string;
  name: string;
  type: ItemType;
  description: string;
  price?: number | null;
  priceCopperValue?: number | null;
  priceLabel?: string;
  weight?: number | null;
  damageDice?: string | null;
  damageType?: string | null;
  rangeMeters?: number | null;
  rangeLongMeters?: number | null;
  versatileDamage?: string | null;
  weaponCategory?: BaseItemWeaponCategory | null;
  weaponRangeType?: BaseItemWeaponRangeType | null;
  armorCategory?: BaseItemArmorCategory | null;
  armorClassBase?: number | null;
  dexBonusRule?: string | null;
  strengthRequirement?: number | null;
  stealthDisadvantage?: boolean | null;
  isShield?: boolean;
  properties?: string[];
  baseItemId?: string | null;
  canonicalKeySnapshot?: string | null;
  nameEnSnapshot?: string | null;
  namePtSnapshot?: string | null;
  itemKind?: BaseItemKind | null;
  costUnit?: BaseItemCostUnit | null;
  isCustom?: boolean;
  isEnabled?: boolean;
};

export type ItemInput = {
  name: string;
  type: ItemType;
  description: string;
  damageDice?: string;
  damageType?: string;
  properties?: ItemPropertySlug[];
  price?: number | string | null;
  weight?: number | string | null;
  rangeMeters?: number | string | null;
  rangeLongMeters?: number | string | null;
  versatileDamage?: string;
  weaponCategory?: BaseItemWeaponCategory | "";
  weaponRangeType?: BaseItemWeaponRangeType | "";
  armorCategory?: BaseItemArmorCategory | "";
  armorClassBase?: number | string | null;
  dexBonusRule?: string;
  strengthRequirement?: number | string | null;
  stealthDisadvantage?: boolean;
  isShield?: boolean;
};
