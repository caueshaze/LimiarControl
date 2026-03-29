import type { BaseItem } from "../../../entities/base-item";
import type {
  BaseItemArmorCategory,
  BaseItemDexBonusRule,
  BaseItemKind,
  BaseItemWeaponCategory,
  BaseItemWeaponRangeType,
} from "../../../entities/base-item";
import type { Item } from "../../../entities/item";
import { itemsRepo } from "../../../shared/api/itemsRepo";

export type CreationCatalogItem = {
  id: string;
  campaignItemId: string | null;
  baseItemId: string | null;
  canonicalKey: string;
  name: string;
  namePt: string;
  description: string;
  descriptionPt: string;
  properties: string[];
  weight: number;
  armorPresetName: string | null;
  armorCategory: BaseItemArmorCategory | null;
  isShield: boolean;
  stealthDisadvantage: boolean;
  itemKind: BaseItemKind;
  weaponCategory: BaseItemWeaponCategory | null;
  weaponRangeType: BaseItemWeaponRangeType | null;
  damageDice: string | null;
  damageType: string | null;
  weaponPropertiesJson: unknown;
  rangeNormalMeters: number | null;
  rangeLongMeters: number | null;
  versatileDamage: string | null;
  armorClassBase: number | null;
  dexBonusRule: BaseItemDexBonusRule | null;
  strengthRequirement: number | null;
};

export type CreationItemCatalog = {
  itemsByCanonicalKey: Map<string, CreationCatalogItem>;
  itemsByLookup: Map<string, CreationCatalogItem>;
};

const EMPTY_CATALOG: CreationItemCatalog = {
  itemsByCanonicalKey: new Map(),
  itemsByLookup: new Map(),
};

const CATALOG_STARTER_PREFIX = "catalog:";

const COMPATIBILITY_CANONICAL_KEYS: Record<string, string> = {
  "leather armor": "leather",
  "studded leather armor": "studded_leather",
  "hide armor": "hide",
  staff: "quarterstaff",
  "wooden shield": "shield",
  amulet: "holy_symbol",
  reliquary: "holy_symbol",
  "crossbow light": "light_crossbow",
  bolt: "crossbow_bolt",
  "con tools": "forgery_kit",
};

const normalizeLookup = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();

const inferItemKind = (item: Item): BaseItemKind | null => {
  if (item.itemKind) {
    return item.itemKind;
  }
  if (item.type === "WEAPON") {
    return "weapon";
  }
  if (item.type === "ARMOR") {
    return "armor";
  }
  if (item.type === "CONSUMABLE") {
    return "consumable";
  }
  return null;
};

const toArmorPresetName = (itemKind: BaseItemKind, isShield: boolean, nameEn: string) => {
  if (itemKind !== "armor" || isShield) {
    return null;
  }
  return nameEn;
};

const buildCatalogProperties = ({
  properties,
  stealthDisadvantage,
}: {
  properties?: readonly string[] | null;
  stealthDisadvantage?: boolean | null;
}) => {
  const next = [...(properties ?? [])];
  if (stealthDisadvantage && !next.includes("stealth_disadvantage")) {
    next.push("stealth_disadvantage");
  }
  return next;
};

const buildCatalogEntryFromBaseItem = (item: BaseItem): CreationCatalogItem => ({
  id: item.id,
  campaignItemId: null,
  baseItemId: item.id,
  canonicalKey: item.canonicalKey,
  name: item.nameEn,
  namePt: item.namePt,
  description: item.descriptionEn ?? item.descriptionPt ?? "",
  descriptionPt: item.descriptionPt ?? item.descriptionEn ?? "",
  properties: buildCatalogProperties({
    properties: item.weaponPropertiesJson,
    stealthDisadvantage: item.stealthDisadvantage,
  }),
  weight: item.weight ?? 0,
  armorPresetName: toArmorPresetName(item.itemKind, item.isShield, item.nameEn),
  armorCategory: item.armorCategory ?? null,
  isShield: item.isShield,
  stealthDisadvantage: item.stealthDisadvantage ?? false,
  itemKind: item.itemKind,
  weaponCategory: item.weaponCategory ?? null,
  weaponRangeType: item.weaponRangeType ?? null,
  damageDice: item.damageDice ?? null,
  damageType: item.damageType ?? null,
  weaponPropertiesJson: item.weaponPropertiesJson ?? null,
  rangeNormalMeters: item.rangeNormalMeters ?? null,
  rangeLongMeters: item.rangeLongMeters ?? null,
  versatileDamage: item.versatileDamage ?? null,
  armorClassBase: item.armorClassBase ?? null,
  dexBonusRule: item.dexBonusRule ?? null,
  strengthRequirement: item.strengthRequirement ?? null,
});

const buildCatalogEntryFromCampaignItem = (item: Item): CreationCatalogItem | null => {
  const itemKind = inferItemKind(item);
  const canonicalKey = item.canonicalKeySnapshot ?? "";
  if (!itemKind || !canonicalKey) {
    return null;
  }

  const stableName = item.nameEnSnapshot ?? item.name;
  const stableNamePt = item.namePtSnapshot ?? item.name;
  const displayName = item.name;

  return {
    id: item.baseItemId ?? item.id,
    campaignItemId: item.id,
    baseItemId: item.baseItemId ?? null,
    canonicalKey,
    name: displayName,
    namePt: stableNamePt,
    description: item.description ?? "",
    descriptionPt: item.description ?? "",
    properties: buildCatalogProperties({
      properties: item.properties ?? null,
      stealthDisadvantage: item.stealthDisadvantage ?? false,
    }),
    weight: item.weight ?? 0,
    armorPresetName: toArmorPresetName(itemKind, item.isShield ?? false, stableName),
    armorCategory: item.armorCategory ?? null,
    isShield: item.isShield ?? false,
    stealthDisadvantage: item.stealthDisadvantage ?? false,
    itemKind,
    weaponCategory: item.weaponCategory ?? null,
    weaponRangeType: item.weaponRangeType ?? null,
    damageDice: item.damageDice ?? null,
    damageType: item.damageType ?? null,
    weaponPropertiesJson: item.properties ?? null,
    rangeNormalMeters: item.rangeMeters ?? null,
    rangeLongMeters: item.rangeLongMeters ?? null,
    versatileDamage: item.versatileDamage ?? null,
    armorClassBase: item.armorClassBase ?? null,
    dexBonusRule: item.dexBonusRule ?? null,
    strengthRequirement: item.strengthRequirement ?? null,
  };
};

const registerLookups = (
  entry: CreationCatalogItem,
  lookups: string[],
  itemsByLookup: Map<string, CreationCatalogItem>,
) => {
  for (const lookup of lookups) {
    const key = normalizeLookup(lookup);
    if (key && !itemsByLookup.has(key)) {
      itemsByLookup.set(key, entry);
    }
  }
};

export const buildCreationItemCatalog = (items: BaseItem[]): CreationItemCatalog => {
  const itemsByCanonicalKey = new Map<string, CreationCatalogItem>();
  const itemsByLookup = new Map<string, CreationCatalogItem>();

  for (const item of items) {
    const entry = buildCatalogEntryFromBaseItem(item);
    itemsByCanonicalKey.set(item.canonicalKey, entry);
    registerLookups(
      entry,
      [
        item.canonicalKey,
        item.nameEn,
        item.namePt,
      ],
      itemsByLookup,
    );
  }

  for (const [lookup, canonicalKey] of Object.entries(COMPATIBILITY_CANONICAL_KEYS)) {
    const target = itemsByCanonicalKey.get(canonicalKey);
    if (target) {
      itemsByLookup.set(lookup, target);
    }
  }

  return { itemsByCanonicalKey, itemsByLookup };
};

const buildCreationItemCatalogFromCampaignItems = (items: Item[]): CreationItemCatalog => {
  const itemsByCanonicalKey = new Map<string, CreationCatalogItem>();
  const itemsByLookup = new Map<string, CreationCatalogItem>();

  for (const item of items) {
    const entry = buildCatalogEntryFromCampaignItem(item);
    if (!entry) {
      continue;
    }
    const stableName = item.nameEnSnapshot ?? item.name;
    const stableNamePt = item.namePtSnapshot ?? item.name;
    itemsByCanonicalKey.set(entry.canonicalKey, entry);
    registerLookups(
      entry,
      [
        entry.canonicalKey,
        item.name,
        stableName,
        stableNamePt,
        entry.name,
      ],
      itemsByLookup,
    );
  }

  for (const [lookup, canonicalKey] of Object.entries(COMPATIBILITY_CANONICAL_KEYS)) {
    const target = itemsByCanonicalKey.get(canonicalKey);
    if (target) {
      itemsByLookup.set(lookup, target);
    }
  }

  return { itemsByCanonicalKey, itemsByLookup };
};

let cachedCatalog = EMPTY_CATALOG;
let cachedCatalogKey: string | null = null;
const loadingCatalogPromises = new Map<string, Promise<CreationItemCatalog>>();

export const getCreationItemCatalog = () => cachedCatalog;

export const getCreationCatalogItemsSorted = (
  catalog: CreationItemCatalog = cachedCatalog,
) =>
  [...catalog.itemsByCanonicalKey.values()].sort((a, b) =>
    a.namePt.localeCompare(b.namePt, "pt-BR"),
  );

export const findCreationItemByCanonicalKey = (
  canonicalKey: string | null | undefined,
  catalog: CreationItemCatalog = cachedCatalog,
) => (canonicalKey ? catalog.itemsByCanonicalKey.get(canonicalKey) ?? null : null);

export const resolveCreationItem = (
  value: string,
  catalog: CreationItemCatalog = cachedCatalog,
) => {
  const lookup = normalizeLookup(value);
  if (!lookup) {
    return null;
  }

  const compatibilityKey = COMPATIBILITY_CANONICAL_KEYS[lookup];
  if (compatibilityKey) {
    return catalog.itemsByCanonicalKey.get(compatibilityKey) ?? null;
  }

  return catalog.itemsByLookup.get(lookup) ?? null;
};

export const loadCreationItemCatalog = async (campaignId?: string | null) => {
  if (!campaignId) {
    cachedCatalog = EMPTY_CATALOG;
    cachedCatalogKey = null;
    return cachedCatalog;
  }

  const existingPromise = loadingCatalogPromises.get(campaignId);
  if (existingPromise) {
    return existingPromise;
  }
  if (cachedCatalogKey === campaignId) {
    return cachedCatalog;
  }

  const nextPromise = itemsRepo
    .list(campaignId)
    .then((items) => {
      cachedCatalog = buildCreationItemCatalogFromCampaignItems(items);
      cachedCatalogKey = campaignId;
      return cachedCatalog;
    })
    .catch((error) => {
      console.warn("Failed to load campaign-scoped creation item catalog.", error);
      cachedCatalog = EMPTY_CATALOG;
      cachedCatalogKey = campaignId;
      return cachedCatalog;
    })
    .finally(() => {
      loadingCatalogPromises.delete(campaignId);
    });

  loadingCatalogPromises.set(campaignId, nextPromise);
  return nextPromise;
};

export const seedCreationItemCatalogForTests = (items: BaseItem[]) => {
  cachedCatalog = buildCreationItemCatalog(items);
  cachedCatalogKey = "tests";
  loadingCatalogPromises.set("tests", Promise.resolve(cachedCatalog));
  return cachedCatalog;
};

export const seedCreationCatalogItemsForTests = (items: CreationCatalogItem[]) => {
  const itemsByCanonicalKey = new Map<string, CreationCatalogItem>();
  const itemsByLookup = new Map<string, CreationCatalogItem>();

  for (const item of items) {
    itemsByCanonicalKey.set(item.canonicalKey, item);
    registerLookups(
      item,
      [
        item.canonicalKey,
        item.name,
        item.namePt,
      ],
      itemsByLookup,
    );
  }

  cachedCatalog = { itemsByCanonicalKey, itemsByLookup };
  cachedCatalogKey = "tests";
  loadingCatalogPromises.set("tests", Promise.resolve(cachedCatalog));
  return cachedCatalog;
};

export const resetCreationItemCatalogForTests = () => {
  cachedCatalog = EMPTY_CATALOG;
  cachedCatalogKey = null;
  loadingCatalogPromises.clear();
};

export const toStarterFallbackKey = (value: string) =>
  normalizeLookup(value).replace(/\s+/g, "_");

export const toCatalogStarterToken = (
  canonicalKey: string,
  quantity = 1,
) => {
  const baseToken = `${CATALOG_STARTER_PREFIX}${canonicalKey}`;
  return quantity > 1 ? `${baseToken} x${quantity}` : baseToken;
};

export const parseCatalogStarterCanonicalKey = (value: string) => {
  const trimmed = value.trim();
  if (!trimmed.toLowerCase().startsWith(CATALOG_STARTER_PREFIX)) {
    return null;
  }
  const body = trimmed.slice(CATALOG_STARTER_PREFIX.length).trim();
  return body || null;
};

export type CatalogWeaponFilter = {
  category?: BaseItemWeaponCategory;
  rangeType?: BaseItemWeaponRangeType;
};

const NON_PHB_WEAPON_KEYS = new Set([
  "pistol",
  "musket",
  "blowgun",
]);

export const getWeaponsFromCatalog = (
  catalog: CreationItemCatalog = cachedCatalog,
  filter?: CatalogWeaponFilter,
): CreationCatalogItem[] => {
  const weapons: CreationCatalogItem[] = [];

  for (const item of catalog.itemsByCanonicalKey.values()) {
    if (item.itemKind !== "weapon") continue;
    if (NON_PHB_WEAPON_KEYS.has(item.canonicalKey)) continue;
    if (filter?.category && item.weaponCategory !== filter.category) continue;
    if (filter?.rangeType && item.weaponRangeType !== filter.rangeType) continue;
    weapons.push(item);
  }

  return weapons.sort((a, b) => a.namePt.localeCompare(b.namePt, "pt-BR"));
};
