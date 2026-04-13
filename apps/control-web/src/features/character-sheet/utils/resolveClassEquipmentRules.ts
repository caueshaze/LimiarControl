/**
 * Resolves declarative ClassEquipmentRules against the runtime
 * CreationItemCatalog to produce a ClassCreationConfig that the
 * existing UI components already know how to render.
 */

import type {
  ClassCreationConfig,
  ClassEquipmentChoiceGroup,
  ClassEquipmentOption,
} from "../data/classCreation";
import type {
  ClassEquipmentRules,
  EquipmentChoiceRule,
  EquipmentOptionSource,
} from "../data/classEquipmentRules";
import type { CreationItemCatalog, CreationCatalogItem } from "./creationItemCatalog";
import {
  getWeaponsFromCatalog,
  findCreationItemByCanonicalKey,
  toCatalogStarterToken,
} from "./creationItemCatalog";

// ── Helpers ─────────────────────────────────────────────────────────────────

const slugify = (value: string) =>
  value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

const weaponOptionFromCatalog = (item: CreationCatalogItem): ClassEquipmentOption => ({
  id: slugify(item.canonicalKey),
  label: item.namePt || item.name,
  items: [toCatalogStarterToken(item.canonicalKey)],
});

const specificItemsOption = (
  source: { labelPt: string; items: { canonicalKey: string; quantity?: number }[] },
  catalog: CreationItemCatalog,
): ClassEquipmentOption | null => {
  const resolvedItems: string[] = [];
  for (const spec of source.items) {
    const item = findCreationItemByCanonicalKey(spec.canonicalKey, catalog);
    if (!item) return null; // item not in catalog — skip this option
    resolvedItems.push(toCatalogStarterToken(item.canonicalKey, spec.quantity ?? 1));
  }

  return {
    id: slugify(source.labelPt),
    label: source.labelPt,
    items: resolvedItems,
  };
};

// ── Source resolvers ────────────────────────────────────────────────────────

const resolveWeaponFilter = (
  source: Extract<EquipmentOptionSource, { kind: "weapon_filter" }>,
  catalog: CreationItemCatalog,
): ClassEquipmentOption[] =>
  getWeaponsFromCatalog(catalog, {
    category: source.category,
    rangeType: source.rangeType,
  }).map(weaponOptionFromCatalog);

const resolveSpecificItems = (
  source: Extract<EquipmentOptionSource, { kind: "specific_items" }>,
  catalog: CreationItemCatalog,
): ClassEquipmentOption[] => {
  const option = specificItemsOption(source, catalog);
  return option ? [option] : [];
};

const resolvePackChoice = (
  source: Extract<EquipmentOptionSource, { kind: "pack_choice" }>,
  catalog: CreationItemCatalog,
): ClassEquipmentOption[] =>
  source.packs
    .map((pack) => {
      const item = findCreationItemByCanonicalKey(pack.canonicalKey, catalog);
      return {
        id: slugify(pack.canonicalKey),
        label: pack.labelPt,
        items: [item ? toCatalogStarterToken(item.canonicalKey) : pack.canonicalKey],
      };
    });

// ── Main resolver ───────────────────────────────────────────────────────────

const resolveSource = (
  source: EquipmentOptionSource,
  catalog: CreationItemCatalog,
): ClassEquipmentOption[] => {
  switch (source.kind) {
    case "weapon_filter":
      return resolveWeaponFilter(source, catalog);
    case "specific_items":
      return resolveSpecificItems(source, catalog);
    case "pack_choice":
      return resolvePackChoice(source, catalog);
  }
};

const uniqueOptions = (options: ClassEquipmentOption[]) => {
  const seen = new Set<string>();
  return options.filter((opt) => {
    const key = opt.label.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const resolveChoiceGroup = (
  rule: EquipmentChoiceRule,
  catalog: CreationItemCatalog,
): ClassEquipmentChoiceGroup => ({
  id: rule.id,
  label: rule.labelPt,
  options: uniqueOptions(rule.sources.flatMap((source) => resolveSource(source, catalog))),
});

const resolveFixedItems = (
  rules: ClassEquipmentRules,
  catalog: CreationItemCatalog,
): string[] =>
  rules.fixedItems.map((spec) => {
    const item = findCreationItemByCanonicalKey(spec.canonicalKey, catalog);
    const qty = spec.quantity ?? 1;
    return item ? toCatalogStarterToken(item.canonicalKey, qty) : spec.canonicalKey;
  });

/**
 * Converts a declarative ClassEquipmentRules into the ClassCreationConfig
 * shape that the UI already consumes. Returns null if the catalog is empty
 * (i.e. API hasn't loaded yet), signalling the caller to use the static fallback.
 */
export const resolveClassEquipmentRules = (
  rules: ClassEquipmentRules,
  catalog: CreationItemCatalog,
): ClassCreationConfig | null => {
  // Guard: if catalog is empty, we can't resolve — caller should use fallback
  if (catalog.itemsByCanonicalKey.size === 0) {
    return null;
  }

  return {
    fixedEquipment: resolveFixedItems(rules, catalog),
    equipmentChoices: rules.choices.map((choice) => resolveChoiceGroup(choice, catalog)),
  };
};
