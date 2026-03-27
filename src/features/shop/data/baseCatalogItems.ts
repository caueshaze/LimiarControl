import baseItemsSeed from "../../../../Base/base_items.seed.json";

import type { BaseItemWritePayload } from "../../../entities/base-item";
import type { Item } from "../../../entities/item";
import { ITEM_TYPES, normalizeItemProperties, type ItemPropertySlug } from "../../../entities/item";
import { canonicalizeDndItemName, getDndItemCanonicalKey } from "../../../entities/dnd-base";

const toSlug = (value: string) =>
  value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

type BaseItemSeedDocument = {
  version: number;
  items: BaseItemWritePayload[];
};

const seedDocument = baseItemsSeed as BaseItemSeedDocument;

const toLabelName = (item: BaseItemWritePayload) =>
  canonicalizeDndItemName(
    item.nameEn?.trim() ||
      item.namePt?.trim() ||
      item.canonicalKey
        .split("_")
        .map((entry) => entry.charAt(0).toUpperCase() + entry.slice(1))
        .join(" "),
  );

const toGpValue = (item: BaseItemWritePayload) => {
  if (typeof item.costQuantity !== "number") {
    return null;
  }
  switch (item.costUnit) {
    case "cp":
      return item.costQuantity / 100;
    case "sp":
      return item.costQuantity / 10;
    case "ep":
      return item.costQuantity / 2;
    case "pp":
      return item.costQuantity * 10;
    case "gp":
    default:
      return item.costQuantity;
  }
};

const toPriceLabel = (item: BaseItemWritePayload) =>
  typeof item.costQuantity === "number" && item.costUnit
    ? `${item.costQuantity} ${item.costUnit.toUpperCase()}`
    : undefined;

const toItemType = (item: BaseItemWritePayload): Item["type"] => {
  if (item.itemKind === "weapon") {
    return ITEM_TYPES.WEAPON;
  }
  if (item.itemKind === "armor") {
    return ITEM_TYPES.ARMOR;
  }
  if (item.itemKind === "consumable") {
    return ITEM_TYPES.CONSUMABLE;
  }
  return ITEM_TYPES.MISC;
};

const toCatalogProperties = (item: BaseItemWritePayload): ItemPropertySlug[] => {
  if (item.itemKind === "weapon") {
    return normalizeItemProperties(item.weaponPropertiesJson ?? []).value;
  }

  if (item.itemKind === "armor" && item.stealthDisadvantage) {
    return ["stealth_disadvantage"];
  }

  return [];
};

export const BASE_CATALOG_ITEMS: Item[] = [
  ...(() => {
    const rawItems: Item[] = seedDocument.items
      .filter((item) => item.system === "DND5E" && item.isActive !== false)
      .map((item) => {
        const name = toLabelName(item);
        return {
          id: `base-item-${toSlug(item.canonicalKey)}`,
          name,
          type: toItemType(item),
          description:
            item.descriptionPt ??
            item.descriptionEn ??
            item.namePt ??
            item.nameEn ??
            name,
          price: toGpValue(item),
          priceLabel: toPriceLabel(item),
          weight: item.weight ?? null,
          damageDice: item.damageDice ?? undefined,
          damageType: item.damageType ?? undefined,
          rangeMeters: item.rangeNormalMeters ?? null,
          rangeLongMeters: item.rangeLongMeters ?? null,
          versatileDamage: item.versatileDamage ?? undefined,
          weaponCategory: item.weaponCategory ?? undefined,
          weaponRangeType: item.weaponRangeType ?? undefined,
          armorCategory: item.armorCategory ?? undefined,
          armorClassBase: item.armorClassBase ?? undefined,
          dexBonusRule: item.dexBonusRule ?? undefined,
          strengthRequirement: item.strengthRequirement ?? undefined,
          stealthDisadvantage: item.stealthDisadvantage ?? undefined,
          isShield: item.isShield ?? false,
          properties: toCatalogProperties(item),
          canonicalKeySnapshot: item.canonicalKey,
          itemKind: item.itemKind,
          costUnit: item.costUnit ?? undefined,
        };
      });

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
