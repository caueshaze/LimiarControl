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
};

export type ItemInput = {
  name: string;
  type: ItemType;
  description: string;
  damageDice?: string;
  properties?: string[];
  price?: number | string | null;
  weight?: number | string | null;
  rangeMeters?: number | string | null;
};
