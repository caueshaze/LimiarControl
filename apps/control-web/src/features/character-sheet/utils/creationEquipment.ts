import { ARMOR_PRESETS } from "../constants";
import { getBackground } from "../data/backgrounds";
import { getClassCreationConfig } from "../data/classCreation";
import type { AbilityName, Armor, CharacterSheet, Currency, InventoryItem, Shield, Weapon } from "../model/characterSheet.types";
import { addMoney, toCopper, type CurrencyUnit } from "../../../shared/utils/money";
import {
  findCreationItemByCanonicalKey,
  getCreationItemCatalog,
  parseCatalogStarterCanonicalKey,
  resolveCreationItem,
  toStarterFallbackKey,
  type CreationCatalogItem,
} from "./creationItemCatalog";

const EMPTY_CURRENCY: Currency = { copperValue: 0 };
const EMPTY_ARMOR = ARMOR_PRESETS.find((preset) => preset.name === "None")!;

type ParsedStarterEntry =
  | { kind: "currency"; coin: CurrencyUnit; amount: number }
  | { kind: "item"; name: string; quantity: number; canonicalKey?: string | null };

const SPECIAL_LITERAL_STARTER_ITEMS: Record<string, ParsedStarterEntry> = {
  "5_sticks_of_incense": { kind: "item", name: "Incense", quantity: 5 },
  "15_meters_of_silk_rope": { kind: "item", name: "Silk Rope", quantity: 1 },
};

const parseStarterEntry = (entry: string): ParsedStarterEntry => {
  const currencyMatch = entry.trim().match(/^(\d+)\s*(cp|sp|ep|gp|pp)$/i);
  if (currencyMatch) {
    return {
      kind: "currency",
      amount: Number(currencyMatch[1]),
      coin: currencyMatch[2].toLowerCase() as CurrencyUnit,
    };
  }

  const literalMatch = SPECIAL_LITERAL_STARTER_ITEMS[toStarterFallbackKey(entry)];
  if (literalMatch) {
    return literalMatch;
  }

  const quantityMatch = entry.trim().match(/^(.+?)\s*x(\d+)$/i);
  const tokenSource = quantityMatch ? quantityMatch[1].trim() : entry.trim();
  const tokenCanonicalKey = parseCatalogStarterCanonicalKey(tokenSource);
  if (tokenCanonicalKey) {
    return {
      kind: "item",
      name: tokenCanonicalKey,
      quantity: quantityMatch ? Number(quantityMatch[2]) : 1,
      canonicalKey: tokenCanonicalKey,
    };
  }

  if (quantityMatch) {
    return {
      kind: "item",
      name: quantityMatch[1].trim(),
      quantity: Number(quantityMatch[2]),
    };
  }

  return { kind: "item", name: entry.trim(), quantity: 1 };
};

const resolveStarterItem = (entry: ParsedStarterEntry | string) => {
  if (typeof entry === "string") {
    return resolveCreationItem(entry, getCreationItemCatalog());
  }
  if (entry.kind === "currency") {
    return null;
  }
  if (entry.canonicalKey) {
    return findCreationItemByCanonicalKey(entry.canonicalKey, getCreationItemCatalog());
  }
  return resolveCreationItem(entry.name, getCreationItemCatalog());
};

const resolveInventoryCatalogItem = (item: InventoryItem) =>
  findCreationItemByCanonicalKey(item.canonicalKey, getCreationItemCatalog()) ??
  resolveCreationItem(item.name, getCreationItemCatalog());

const starterStableKey = (name: string, canonicalKey?: string | null) =>
  (canonicalKey ?? toStarterFallbackKey(name)).replace(/_/g, "-");

export const canonicalizeStarterItemName = (name: string) =>
  resolveStarterItem(parseStarterEntry(name))?.name ?? name.trim();

const getArmorPresetByName = (presetName: string | null | undefined) =>
  presetName ? ARMOR_PRESETS.find((preset) => preset.name === presetName) ?? null : null;

const toArmorDexCap = (dexBonusRule: CreationCatalogItem["dexBonusRule"]) => {
  if (dexBonusRule === "max_2") {
    return 2;
  }
  if (dexBonusRule === "none") {
    return 0;
  }
  return null;
};

const toArmorFromCreationCatalogItem = (item: CreationCatalogItem | null): Armor | null => {
  if (!item || item.itemKind !== "armor" || item.isShield) {
    return null;
  }

  if (item.armorCategory && item.armorCategory !== "shield" && item.armorClassBase != null) {
    return {
      name: item.name,
      baseAC: item.armorClassBase,
      dexCap: toArmorDexCap(item.dexBonusRule),
      armorType: item.armorCategory,
      allowsDex: item.dexBonusRule !== "none",
      stealthDisadvantage:
        item.stealthDisadvantage || item.properties.includes("stealth_disadvantage"),
      minStrength: item.strengthRequirement ?? null,
    };
  }

  const preset = getArmorPresetByName(item.armorPresetName);
  return preset ? { ...preset, name: item.name } : null;
};

export type CreationArmorOption = {
  value: string;
  label: string;
  detail: string | null;
  armor: Armor;
};

export const buildCreationArmorOptions = (
  inventory: CharacterSheet["inventory"],
): CreationArmorOption[] =>
  inventory
    .filter((entry) => entry.quantity > 0)
    .flatMap((entry) => {
      const resolved = resolveInventoryCatalogItem(entry);
      if (!resolved || resolved.itemKind !== "armor" || resolved.isShield) {
        return [];
      }
      const armor = toArmorFromCreationCatalogItem(resolved);
      if (!armor) {
        return [];
      }
      return [{
        value: entry.id,
        label: entry.name,
        detail: armor.armorType !== "none" ? `AC ${armor.baseAC}` : null,
        armor,
      }];
    });

export const hasCreationShieldInInventory = (inventory: CharacterSheet["inventory"]) =>
  inventory.some((entry) => {
    if (entry.quantity <= 0) return false;
    const resolved = resolveInventoryCatalogItem(entry);
    return resolved?.isShield ?? false;
  });

export const canonicalizeCreationInventory = (
  inventory: CharacterSheet["inventory"],
): CharacterSheet["inventory"] =>
  inventory.map((entry) => {
    const resolved = resolveInventoryCatalogItem(entry);
    if (!resolved) {
      return {
        ...entry,
        canonicalKey: null,
        campaignItemId: null,
        baseItemId: null,
      };
    }
    return {
      ...entry,
      canonicalKey: resolved.canonicalKey,
      campaignItemId: resolved.campaignItemId,
      baseItemId: resolved.baseItemId,
      weight: entry.weight > 0 ? entry.weight : resolved.weight,
    };
  });

export const hasCustomCreationInventoryItems = (
  inventory: CharacterSheet["inventory"],
) => inventory.some((entry) => entry.quantity > 0 && !entry.id.startsWith("starter:"));

export const hasUnresolvedCreationInventoryItems = (
  inventory: CharacterSheet["inventory"],
) => inventory.some((entry) => entry.quantity > 0 && !entry.canonicalKey);

export const syncCreationInventoryLoadoutState = (
  sheet: CharacterSheet,
): CharacterSheet => {
  const inventory = canonicalizeCreationInventory(sheet.inventory);
  const armorOptions = buildCreationArmorOptions(inventory);

  const resolveSelectedArmor = () => {
    if (sheet.equippedArmorItemId) {
      const selectedById = armorOptions.find((option) => option.value === sheet.equippedArmorItemId);
      if (selectedById) {
        return selectedById;
      }
    }

    if (sheet.equippedArmor.name !== EMPTY_ARMOR.name) {
      const selectedByName = armorOptions.find((option) => option.armor.name === sheet.equippedArmor.name);
      if (selectedByName) {
        return selectedByName;
      }

      if (armorOptions.length === 1) {
        return armorOptions[0] ?? null;
      }
    }

    return null;
  };

  const selectedArmor = resolveSelectedArmor();

  return {
    ...sheet,
    inventory,
    equippedArmorItemId: selectedArmor?.value ?? null,
    equippedArmor: selectedArmor?.armor ?? { ...EMPTY_ARMOR },
    equippedShield: hasCreationShieldInInventory(inventory) ? sheet.equippedShield : null,
  };
};

export const getInitialClassEquipmentSelections = (className: string) => {
  const config = getClassCreationConfig(className);
  if (!config) return {};
  return Object.fromEntries(
    config.equipmentChoices
      .filter((group) => group.options.length > 0)
      .map((group) => [group.id, group.options[0].id]),
  ) as Record<string, string>;
};

export const resolveClassEquipmentItems = (
  className: string,
  selections: Record<string, string>,
) => {
  const config = getClassCreationConfig(className);
  if (!config) return [];

  return [
    ...config.fixedEquipment,
    ...config.equipmentChoices.flatMap((group) => {
      const selectedId = selections[group.id] ?? group.options[0]?.id;
      const selected = group.options.find((option) => option.id === selectedId) ?? group.options[0];
      return selected?.items ?? [];
    }),
  ];
};

// ── Weapon auto-population from base item data ────────────────────────────

const formatWeaponProperties = (propsJson: unknown): string => {
  if (!propsJson) return "";
  if (Array.isArray(propsJson)) return propsJson.join(", ");
  return "";
};

const formatWeaponRange = (item: CreationCatalogItem): string => {
  if (item.rangeNormalMeters && item.rangeLongMeters) return `${item.rangeNormalMeters}/${item.rangeLongMeters} m`;
  if (item.rangeNormalMeters) return `${item.rangeNormalMeters} m`;
  return "";
};

const deriveWeaponAbility = (item: CreationCatalogItem): AbilityName => {
  const props = Array.isArray(item.weaponPropertiesJson) ? item.weaponPropertiesJson : [];
  const hasFinesse = props.some(
    (p: unknown) => typeof p === "string" && p.toLowerCase().includes("finesse"),
  );
  if (hasFinesse) return "dexterity"; // Player can choose; default to DEX for finesse
  if (item.weaponRangeType === "ranged") return "dexterity";
  return "strength";
};

const catalogItemToWeapon = (
  item: CreationCatalogItem,
  stableId: string,
): Weapon => ({
  id: `weapon:${stableId}`,
  name: item.namePt || item.name,
  ability: deriveWeaponAbility(item),
  damageDice: item.damageDice ?? "1d4",
  damageType: item.damageType ?? "bludgeoning",
  proficient: true,
  magicBonus: 0,
  properties: formatWeaponProperties(item.weaponPropertiesJson),
  range: formatWeaponRange(item),
  rangeType: item.weaponRangeType ?? null,
});

const buildWeaponsFromInventory = (
  inventoryMap: Map<string, InventoryItem>,
): Weapon[] => {
  const catalog = getCreationItemCatalog();
  const weapons: Weapon[] = [];
  const seen = new Set<string>();

  for (const [stableId, invItem] of inventoryMap) {
    if (!invItem.canonicalKey) continue;
    const catalogItem = findCreationItemByCanonicalKey(invItem.canonicalKey, catalog);
    if (!catalogItem || catalogItem.itemKind !== "weapon") continue;
    if (seen.has(catalogItem.canonicalKey)) continue;
    seen.add(catalogItem.canonicalKey);
    weapons.push(catalogItemToWeapon(catalogItem, stableId.replace("starter:", "")));
  }

  return weapons;
};

export const buildCreationLoadout = (
  className: string,
  backgroundName: string,
  selections: Record<string, string>,
): {
  inventory: InventoryItem[];
  currency: Currency;
  equippedArmor: Armor;
  equippedArmorItemId: string | null;
  equippedShield: Shield | null;
  weapons: Weapon[];
} => {
  const inventoryMap = new Map<string, InventoryItem>();
  const currency: Currency = { ...EMPTY_CURRENCY };
  const entries = [
    ...resolveClassEquipmentItems(className, selections),
    ...(getBackground(backgroundName)?.startingEquipment ?? []),
  ];

  for (const entry of entries) {
    const parsed = parseStarterEntry(entry);
    if (parsed.kind === "currency") {
      const nextCurrency = addMoney(currency, toCopper(parsed.amount, parsed.coin));
      currency.copperValue = nextCurrency.copperValue;
      continue;
    }

    const resolved = resolveStarterItem(parsed);
    const stableId = `starter:${starterStableKey(parsed.name, resolved?.canonicalKey ?? parsed.canonicalKey)}`;
    const existing = inventoryMap.get(stableId);
    inventoryMap.set(stableId, {
      id: stableId,
      name: resolved?.name ?? parsed.name,
      quantity: (existing?.quantity ?? 0) + parsed.quantity,
      weight: resolved?.weight ?? existing?.weight ?? 0,
      notes: existing?.notes ?? "Equipamento inicial",
      canonicalKey: resolved?.canonicalKey ?? existing?.canonicalKey ?? null,
      campaignItemId: resolved?.campaignItemId ?? existing?.campaignItemId ?? null,
      baseItemId: resolved?.baseItemId ?? existing?.baseItemId ?? null,
    });
  }

  const weapons = buildWeaponsFromInventory(inventoryMap);
  const inventory = [...inventoryMap.values()];
  const { equippedArmor, equippedArmorItemId, equippedShield } = deriveLoadoutFromInventory(inventory);
  return { inventory, currency, equippedArmor, equippedArmorItemId, equippedShield, weapons };
};

export const applyCreationLoadoutToSheet = (sheet: CharacterSheet): CharacterSheet => {
  const loadout = buildCreationLoadout(
    sheet.class,
    sheet.background,
    sheet.classEquipmentSelections,
  );
  return {
    ...sheet,
    inventory: loadout.inventory,
    currency: loadout.currency,
    equippedArmor: loadout.equippedArmor,
    equippedArmorItemId: loadout.equippedArmorItemId,
    equippedShield: loadout.equippedShield,
    weapons: loadout.weapons,
  };
};

export const deriveLoadoutFromInventory = (inventory: CharacterSheet["inventory"]) => {
  const armorOption = buildCreationArmorOptions(inventory)[0] ?? null;
  const equippedArmor = armorOption?.armor ?? { ...EMPTY_ARMOR };
  const equippedArmorItemId = armorOption?.value ?? null;

  const equippedShield = inventory.some((item) => {
    if (item.quantity <= 0) return false;
    const catalogItem = resolveInventoryCatalogItem(item);
    return catalogItem?.isShield ?? ["shield", "escudo"].some((label) => item.name.toLowerCase().includes(label));
  })
    ? { name: "Shield", bonus: 2 }
    : null;

  return { equippedArmor, equippedArmorItemId, equippedShield };
};
