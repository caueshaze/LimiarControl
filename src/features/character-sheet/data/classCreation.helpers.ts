import { getCreationWeapons } from "./creationWeapons";
import {
  getCreationItemCatalog,
  getWeaponsFromCatalog,
  resolveCreationItem,
  toCatalogStarterToken,
} from "../utils/creationItemCatalog";
import type { ClassCreationConfig, ClassEquipmentOption } from "./classCreation.types";

export const slugify = (value: string) =>
  value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

export const option = (label: string, ...items: string[]): ClassEquipmentOption => ({
  id: slugify(label),
  label,
  items,
});

export const uniqueOptions = (options: ClassEquipmentOption[]) => {
  const seen = new Set<string>();
  return options.filter((entry) => {
    const key = entry.label.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const weaponOptions = (
  filter: Parameters<typeof getCreationWeapons>[0],
): ClassEquipmentOption[] => {
  const catalog = getCreationItemCatalog();
  if (catalog.itemsByCanonicalKey.size > 0) {
    const category = filter?.category;
    const rangeType = filter?.kind;
    return getWeaponsFromCatalog(catalog, { category, rangeType }).map((weapon) => ({
      id: slugify(weapon.canonicalKey),
      label: weapon.namePt || weapon.name,
      items: [toCatalogStarterToken(weapon.canonicalKey)],
    }));
  }

  return getCreationWeapons(filter).map((weapon) => ({
    id: slugify(weapon.label),
    label: weapon.label,
    items: [weapon.name],
  }));
};

export const simpleWeaponOptions = weaponOptions({ category: "simple" });
export const simpleMeleeWeaponOptions = weaponOptions({ category: "simple", kind: "melee" });
export const martialWeaponOptions = weaponOptions({ category: "martial" });
export const martialMeleeWeaponOptions = weaponOptions({ category: "martial", kind: "melee" });
export const simpleMeleePairOptions = simpleMeleeWeaponOptions.map((entry) =>
  option(`${entry.label} x2`, entry.label, entry.label),
);
export const martialWeaponWithShieldOptions = martialWeaponOptions.map((entry) =>
  option(`${entry.label} + Escudo`, entry.label, "Shield"),
);
export const martialWeaponPairOptions = martialWeaponOptions.map((entry) =>
  option(`${entry.label} x2`, entry.label, entry.label),
);

const resolveStaticStarterEntry = (entry: string) => {
  const quantityMatch = entry.trim().match(/^(.+?)\s*x(\d+)$/i);
  const rawName = quantityMatch ? quantityMatch[1].trim() : entry.trim();
  const quantity = quantityMatch ? Number(quantityMatch[2]) : 1;
  const resolved = resolveCreationItem(rawName, getCreationItemCatalog());
  if (!resolved) {
    return entry;
  }
  return toCatalogStarterToken(resolved.canonicalKey, quantity);
};

export const resolveStaticConfigAgainstCatalog = (
  config: ClassCreationConfig,
): ClassCreationConfig => {
  const catalog = getCreationItemCatalog();
  if (catalog.itemsByCanonicalKey.size === 0) {
    return config;
  }

  return {
    ...config,
    fixedEquipment: config.fixedEquipment.map(resolveStaticStarterEntry),
    equipmentChoices: config.equipmentChoices.map((group) => ({
      ...group,
      options: group.options.map((entry) => ({
        ...entry,
        items: entry.items.map(resolveStaticStarterEntry),
      })),
    })),
  };
};
