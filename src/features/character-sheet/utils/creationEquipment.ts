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

const ARMOR_ALIASES: Record<string, string[]> = {
  None: [],
  Padded: ["Acolchoada", "Padded"],
  Leather: ["Couro", "Leather"],
  "Studded Leather": ["Couro Batido", "Studded Leather"],
  Hide: ["Gibão de Peles", "Hide"],
  "Chain Shirt": ["Camisão de Malha", "Chain Shirt"],
  "Scale Mail": ["Brunea", "Scale Mail"],
  Breastplate: ["Peitoral", "Breastplate"],
  "Half Plate": ["Meia-Armadura", "Half Plate"],
  "Ring Mail": ["Cota de Anéis", "Ring Mail"],
  "Chain Mail": ["Cota de Malha", "Chain Mail"],
  Splint: ["Cota de Talas", "Splint"],
  Plate: ["Placas", "Plate"],
};

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

const starterStableKey = (name: string, canonicalKey?: string | null) =>
  (canonicalKey ?? toStarterFallbackKey(name)).replace(/_/g, "-");

const matchesArmorPreset = (item: InventoryItem, presetName: string) => {
  const catalogItem = findCreationItemByCanonicalKey(item.canonicalKey, getCreationItemCatalog());
  if (catalogItem?.armorPresetName) {
    return catalogItem.armorPresetName === presetName;
  }

  const aliases = ARMOR_ALIASES[presetName] ?? [presetName];
  return aliases.some((alias) => item.name.toLowerCase().includes(alias.toLowerCase()));
};

export const canonicalizeStarterItemName = (name: string) =>
  resolveStarterItem(parseStarterEntry(name))?.name ?? name.trim();

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
  const { equippedArmor, equippedShield } = deriveLoadoutFromInventory(inventory);
  return { inventory, currency, equippedArmor, equippedShield, weapons };
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
    equippedShield: loadout.equippedShield,
    weapons: loadout.weapons,
  };
};

export const deriveLoadoutFromInventory = (inventory: CharacterSheet["inventory"]) => {
  const equippedArmor = ARMOR_PRESETS.find((preset) =>
    inventory.some((item) => matchesArmorPreset(item, preset.name)),
  ) ?? ARMOR_PRESETS.find((preset) => preset.name === "None")!;

  const equippedShield = inventory.some((item) => {
    const catalogItem = findCreationItemByCanonicalKey(item.canonicalKey, getCreationItemCatalog());
    return catalogItem?.isShield ?? ["shield", "escudo"].some((label) => item.name.toLowerCase().includes(label));
  })
    ? { name: "Shield", bonus: 2 }
    : null;

  return { equippedArmor, equippedShield };
};
