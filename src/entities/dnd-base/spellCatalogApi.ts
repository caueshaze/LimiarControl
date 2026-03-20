/**
 * API-backed spell catalog that replaces the CSV-based spellCatalog.ts.
 *
 * Fetches spells from the appropriate API source on first access,
 * caches them in memory by scope, and exposes the same synchronous interface
 * that creationSpells.ts expects.
 */
import type { BaseSpell as ApiBaseSpell } from "../base-spell/baseSpell.types";
import { baseSpellsRepo } from "../../shared/api/baseSpellsRepo";
import { campaignSpellsRepo } from "../../shared/api/campaignSpellsRepo";

/** Shape expected by consumers (matches the old CSV-based BaseSpell). */
export type BaseSpell = {
  name: string;
  level: number;
  school: string;
  castingTime: string;
  range: string;
  components: string;
  duration: string;
  concentration: boolean;
  ritual: boolean;
  description: string;
  damageType: string | null;
  savingThrow: string | null;
  classes: string[];
};

const BASE_SCOPE_KEY = "__base__";

const getScopeKey = (campaignId?: string | null) =>
  campaignId?.trim() ? campaignId : BASE_SCOPE_KEY;

// ---- Module-level cache ----
let activeScopeKey = BASE_SCOPE_KEY;
const cacheByScope = new Map<string, BaseSpell[]>();
const loadPromiseByScope = new Map<string, Promise<void>>();

const adapt = (api: ApiBaseSpell): BaseSpell => ({
  name: api.nameEn,
  level: api.level,
  school: api.school || "Evocation",
  castingTime: api.castingTime ?? "",
  range: api.rangeText ?? "",
  components: api.componentsJson?.join(", ") ?? "",
  duration: api.duration ?? "",
  concentration: api.concentration,
  ritual: api.ritual,
  description: api.descriptionEn,
  damageType: api.damageType ?? null,
  savingThrow: api.savingThrow ?? null,
  classes: api.classesJson ?? [],
});

/**
 * Fetch spells from the API and populate the cache for the chosen scope.
 * Idempotent — subsequent calls return the same promise.
 */
export const loadSpellCatalog = (campaignId?: string | null): Promise<void> => {
  const scopeKey = getScopeKey(campaignId);
  activeScopeKey = scopeKey;

  if (cacheByScope.has(scopeKey)) {
    return Promise.resolve();
  }

  const existingPromise = loadPromiseByScope.get(scopeKey);
  if (existingPromise) {
    return existingPromise;
  }

  const loadPromise = (
    scopeKey === BASE_SCOPE_KEY
      ? baseSpellsRepo.list()
      : campaignSpellsRepo.list(scopeKey)
  )
    .then((spells) => {
      cacheByScope.set(scopeKey, spells.map(adapt));
    })
    .catch((err) => {
      console.error("[spellCatalogApi] Failed to load spells:", err);
      throw err;
    })
    .finally(() => {
      loadPromiseByScope.delete(scopeKey);
    });

  loadPromiseByScope.set(scopeKey, loadPromise);
  return loadPromise;
};

/** Returns true if spells have been loaded into cache. */
export const isSpellCatalogLoaded = (campaignId?: string | null): boolean =>
  cacheByScope.has(getScopeKey(campaignId));

/** Returns all cached spells — empty array if not yet loaded. */
export const getBaseSpells = (campaignId?: string | null): BaseSpell[] =>
  cacheByScope.get(campaignId === undefined ? activeScopeKey : getScopeKey(campaignId)) ?? [];

export const getBaseSpellsForClass = (
  className: string,
  maxLevel = 9,
  campaignId?: string | null,
): BaseSpell[] => {
  const source = getBaseSpells(campaignId);
  return source.filter(
    (spell) =>
      spell.level <= maxLevel &&
      spell.classes.some((c) => c.toLowerCase() === className.trim().toLowerCase()),
  );
};

export const findBaseSpell = (name: string, campaignId?: string | null): BaseSpell | undefined => {
  const source = getBaseSpells(campaignId);
  return source.find((spell) => spell.name.toLowerCase() === name.trim().toLowerCase());
};

/**
 * Directly seed the cache with pre-built spell data.
 * Used for tests that can't call the API.
 */
export const seedSpellCatalogCache = (spells: BaseSpell[], campaignId?: string | null): void => {
  const scopeKey = getScopeKey(campaignId);
  activeScopeKey = scopeKey;
  cacheByScope.set(scopeKey, spells);
};
