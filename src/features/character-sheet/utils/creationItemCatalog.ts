import { CampaignSystemType } from "../../../entities/campaign";
import type { BaseItem } from "../../../entities/base-item";
import type {
  BaseItemKind,
  BaseItemWeaponCategory,
  BaseItemWeaponRangeType,
} from "../../../entities/base-item";
import { baseItemsRepo } from "../../../shared/api/baseItemsRepo";

export type CreationCatalogItem = {
  id: string;
  canonicalKey: string;
  name: string;
  namePt: string;
  weight: number;
  armorPresetName: string | null;
  isShield: boolean;
  itemKind: BaseItemKind;
  weaponCategory: BaseItemWeaponCategory | null;
  weaponRangeType: BaseItemWeaponRangeType | null;
  damageDice: string | null;
  damageType: string | null;
  weaponPropertiesJson: unknown;
  rangeNormal: number | null;
  rangeLong: number | null;
  versatileDamage: string | null;
};

export type CreationItemCatalog = {
  itemsByCanonicalKey: Map<string, CreationCatalogItem>;
  itemsByLookup: Map<string, CreationCatalogItem>;
};

const EMPTY_CATALOG: CreationItemCatalog = {
  itemsByCanonicalKey: new Map(),
  itemsByLookup: new Map(),
};

const COMPATIBILITY_CANONICAL_KEYS: Record<string, string> = {
  "leather armor": "leather",
  "studded leather armor": "studded_leather",
  "hide armor": "hide",
};

const normalizeLookup = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();

const toArmorPresetName = (item: BaseItem) => {
  if (item.itemKind !== "armor" || item.isShield) {
    return null;
  }
  return item.nameEn;
};

export const buildCreationItemCatalog = (items: BaseItem[]): CreationItemCatalog => {
  const itemsByCanonicalKey = new Map<string, CreationCatalogItem>();
  const itemsByLookup = new Map<string, CreationCatalogItem>();

  for (const item of items) {
    const entry: CreationCatalogItem = {
      id: item.id,
      canonicalKey: item.canonicalKey,
      name: item.nameEn,
      namePt: item.namePt,
      weight: item.weight ?? 0,
      armorPresetName: toArmorPresetName(item),
      isShield: item.isShield,
      itemKind: item.itemKind,
      weaponCategory: item.weaponCategory ?? null,
      weaponRangeType: item.weaponRangeType ?? null,
      damageDice: item.damageDice ?? null,
      damageType: item.damageType ?? null,
      weaponPropertiesJson: item.weaponPropertiesJson ?? null,
      rangeNormal: item.rangeNormal ?? null,
      rangeLong: item.rangeLong ?? null,
      versatileDamage: item.versatileDamage ?? null,
    };

    itemsByCanonicalKey.set(item.canonicalKey, entry);

    const lookups = [
      item.canonicalKey,
      item.nameEn,
      item.namePt,
      ...item.aliases.map((alias) => alias.alias),
    ];

    for (const lookup of lookups) {
      const key = normalizeLookup(lookup);
      if (key && !itemsByLookup.has(key)) {
        itemsByLookup.set(key, entry);
      }
    }
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
let loadingCatalogPromise: Promise<CreationItemCatalog> | null = null;

export const getCreationItemCatalog = () => cachedCatalog;

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

export const loadCreationItemCatalog = async () => {
  if (loadingCatalogPromise) {
    return loadingCatalogPromise;
  }

  loadingCatalogPromise = baseItemsRepo
    .list({ system: CampaignSystemType.DND5E })
    .then((items) => {
      cachedCatalog = buildCreationItemCatalog(items);
      return cachedCatalog;
    })
    .catch((error) => {
      console.warn("Failed to load persisted creation item catalog.", error);
      cachedCatalog = EMPTY_CATALOG;
      loadingCatalogPromise = null;
      return cachedCatalog;
    });

  return loadingCatalogPromise;
};

export const seedCreationItemCatalogForTests = (items: BaseItem[]) => {
  cachedCatalog = buildCreationItemCatalog(items);
  loadingCatalogPromise = Promise.resolve(cachedCatalog);
  return cachedCatalog;
};

export const resetCreationItemCatalogForTests = () => {
  cachedCatalog = EMPTY_CATALOG;
  loadingCatalogPromise = null;
};

export const toStarterFallbackKey = (value: string) =>
  normalizeLookup(value).replace(/\s+/g, "_");

// ── DB-driven weapon queries ───────────────────────────────────────────────

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
