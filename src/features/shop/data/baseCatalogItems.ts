import type { Item } from "../../../entities/item";
import { ITEM_TYPES } from "../../../entities/item";
import { BASE_ARMORS, BASE_WEAPONS } from "../../../entities/dnd-base";

const toSlug = (value: string) =>
  value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

const feetToMeters = (feet: number | null) =>
  feet && feet > 5 ? Math.max(1, Math.round(feet * 0.3048)) : null;

export const BASE_CATALOG_ITEMS: Item[] = [
  ...BASE_WEAPONS.map((weapon) => ({
    id: `base-weapon-${toSlug(weapon.name)}`,
    name: weapon.name,
    type: ITEM_TYPES.WEAPON,
    description: weapon.description,
    price: weapon.price.gpValue,
    priceLabel: weapon.price.label,
    weight: weapon.weightLb,
    damageDice: weapon.damageDice ?? undefined,
    rangeMeters: feetToMeters(weapon.normalRangeFt),
    properties: weapon.properties,
  })),
  ...BASE_ARMORS.map((armor) => ({
    id: `base-armor-${toSlug(armor.name)}`,
    name: armor.name,
    type: ITEM_TYPES.ARMOR,
    description: armor.description,
    price: armor.price.gpValue,
    priceLabel: armor.price.label,
    weight: armor.weightLb,
    properties: [
      `Base AC ${armor.baseAC}`,
      armor.category === "shield" ? "Shield bonus" : `Type ${armor.category}`,
      ...(armor.dexCap === null ? [] : [`DEX cap ${armor.dexCap}`]),
      ...(armor.strengthRequirement ? [`STR ${armor.strengthRequirement}`] : []),
      ...(armor.stealthDisadvantage ? ["Stealth disadvantage"] : []),
    ],
  })),
];

export const getBaseCatalogItemByName = (name: string) =>
  BASE_CATALOG_ITEMS.find((item) => item.name.toLowerCase() === name.trim().toLowerCase());
