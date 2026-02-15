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
  weight?: number | null;
  damageDice?: string;
  rangeMeters?: number | null;
  properties?: string[];
};

export type ItemInput = Omit<Item, "id" | "price" | "weight" | "rangeMeters"> & {
  price?: number | string | null;
  weight?: number | string | null;
  rangeMeters?: number | string | null;
};
