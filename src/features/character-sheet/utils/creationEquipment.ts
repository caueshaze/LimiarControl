import { findBaseArmor, findBaseWeapon } from "../../../entities/dnd-base";
import { ARMOR_PRESETS } from "../constants";
import { getBackground } from "../data/backgrounds";
import { getClassCreationConfig } from "../data/classCreation";
import type { Armor, CharacterSheet, Currency, InventoryItem, Shield } from "../model/characterSheet.types";

const EMPTY_CURRENCY: Currency = { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };

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
  | { kind: "currency"; coin: keyof Currency; amount: number }
  | { kind: "item"; name: string; quantity: number };

const parseStarterEntry = (entry: string): ParsedStarterEntry => {
  const currencyMatch = entry.trim().match(/^(\d+)\s*(cp|sp|ep|gp|pp)$/i);
  if (currencyMatch) {
    return {
      kind: "currency",
      amount: Number(currencyMatch[1]),
      coin: currencyMatch[2].toLowerCase() as keyof Currency,
    };
  }

  const quantityMatch = entry.trim().match(/^(.+?)\s*x(\d+)$/i);
  if (quantityMatch) {
    return {
      kind: "item",
      name: quantityMatch[1].trim(),
      quantity: Number(quantityMatch[2]),
    };
  }

  return { kind: "item", name: entry.trim(), quantity: 1 };
};

const getItemWeight = (name: string) =>
  findBaseWeapon(name)?.weightLb ?? findBaseArmor(name)?.weightLb ?? 0;

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

export const buildCreationLoadout = (
  className: string,
  backgroundName: string,
  selections: Record<string, string>,
): {
  inventory: InventoryItem[];
  currency: Currency;
  equippedArmor: Armor;
  equippedShield: Shield | null;
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
      currency[parsed.coin] += parsed.amount;
      continue;
    }

    const existing = inventoryMap.get(parsed.name);
    const quantity = (existing?.quantity ?? 0) + parsed.quantity;
    inventoryMap.set(parsed.name, {
      id: existing?.id ?? `${parsed.name}-${inventoryMap.size}`,
      name: parsed.name,
      quantity,
      weight: getItemWeight(parsed.name),
      notes: "Starting equipment",
    });
  }

  const inventory = [...inventoryMap.values()];
  return {
    inventory,
    currency,
    equippedArmor: deriveLoadoutFromInventory(inventory).equippedArmor,
    equippedShield: deriveLoadoutFromInventory(inventory).equippedShield,
  };
};

export const deriveLoadoutFromInventory = (inventory: CharacterSheet["inventory"]) => {
  const equippedArmor = ARMOR_PRESETS.find((preset) => {
    const aliases = ARMOR_ALIASES[preset.name] ?? [preset.name];
    return inventory.some((item) =>
      aliases.some((alias) => item.name.toLowerCase().includes(alias.toLowerCase())),
    );
  }) ?? ARMOR_PRESETS.find((preset) => preset.name === "None")!;

  const equippedShield = inventory.some((item) =>
    ["shield", "escudo"].some((label) => item.name.toLowerCase().includes(label)),
  )
    ? { name: "Shield", bonus: 2 }
    : null;

  return { equippedArmor, equippedShield };
};
