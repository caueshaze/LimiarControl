import type { Item } from "../../../entities/item";
import { ITEM_TYPES } from "../../../entities/item";
import {
  BASE_ARMORS,
  BASE_GEARS,
  BASE_WEAPONS,
  canonicalizeDndItemName,
  getDndItemCanonicalKey,
} from "../../../entities/dnd-base";

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
  ...(() => {
    const secondaryGearKeys = new Set(
      [
        "Holy Symbol",
        "Arcane Focus",
        "Druidic Focus",
        "Crossbow bolt",
        "Quiver",
        "Thieves' Tools",
        "Forgery Kit",
      ].map(getDndItemCanonicalKey),
    );

    const rawItems: Item[] = [
      ...BASE_WEAPONS.map((weapon) => ({
        id: `base-weapon-${toSlug(canonicalizeDndItemName(weapon.name))}`,
        name: canonicalizeDndItemName(weapon.name),
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
        id: `base-armor-${toSlug(canonicalizeDndItemName(armor.name))}`,
        name: canonicalizeDndItemName(armor.name),
        type: ITEM_TYPES.ARMOR,
        description: armor.description,
        price: armor.price.gpValue,
        priceLabel: armor.price.label,
        weight: armor.weightLb,
        properties: [
          `CA base ${armor.baseAC}`,
          armor.category === "shield" ? "Bônus de escudo" : `Tipo ${armor.category === "light" ? "leve" : armor.category === "medium" ? "média" : armor.category === "heavy" ? "pesada" : armor.category}`,
          ...(armor.dexCap === null ? [] : [`DEX máx ${armor.dexCap}`]),
          ...(armor.strengthRequirement ? [`FOR ${armor.strengthRequirement}`] : []),
          ...(armor.stealthDisadvantage ? ["Desvantagem em furtividade"] : []),
        ],
      })),
      ...BASE_GEARS
        .filter((gear) => secondaryGearKeys.has(getDndItemCanonicalKey(gear.name)))
        .map((gear) => ({
          id: `base-gear-${toSlug(canonicalizeDndItemName(gear.name))}`,
          name: canonicalizeDndItemName(gear.name),
          type: ITEM_TYPES.MISC,
          description: gear.description,
          price: gear.price?.gpValue ?? null,
          priceLabel: gear.price?.label,
          weight: gear.weightLb,
          properties: [],
        })),
    ];

    const catalogByKey = new Map<string, Item>();
    for (const item of rawItems) {
      const itemKey = getDndItemCanonicalKey(item.name);
      if (!itemKey || catalogByKey.has(itemKey)) {
        continue;
      }
      catalogByKey.set(itemKey, item);
    }
    return [...catalogByKey.values()];
  })(),
];

const BASE_CATALOG_ITEMS_BY_KEY = new Map(
  BASE_CATALOG_ITEMS.map((item) => [getDndItemCanonicalKey(item.name), item] as const),
);

export const getBaseCatalogItemByName = (name: string) =>
  BASE_CATALOG_ITEMS_BY_KEY.get(getDndItemCanonicalKey(name));

export const getMissingBaseCatalogItems = (existingItems: Pick<Item, "name">[]) => {
  const existingKeys = new Set(
    existingItems
      .map((item) => getDndItemCanonicalKey(item.name))
      .filter(Boolean),
  );
  return BASE_CATALOG_ITEMS.filter(
    (item) => !existingKeys.has(getDndItemCanonicalKey(item.name)),
  );
};
