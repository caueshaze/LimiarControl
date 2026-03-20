import type { BaseItemCostUnit, BaseItemKind } from "../base-item";
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
  priceLabel?: string;
  weight?: number | null;
  damageDice?: string;
  rangeMeters?: number | null;
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
  properties?: ItemPropertySlug[];
  price?: number | string | null;
  weight?: number | string | null;
  rangeMeters?: number | string | null;
};
