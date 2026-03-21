import { ITEM_TYPES, type Item } from "../../../entities/item";
import type { InventoryItem } from "../../../entities/inventory";
import type { Armor } from "../../character-sheet/model/characterSheet.types";
import type { CurrencyWallet } from "../../../shared/api/inventoryRepo";

export type SessionInventoryResolvedEntry = {
  entry: InventoryItem;
  item: Item | null;
  group: "weapon" | "armor" | "magic" | "consumable" | "misc";
  name: string;
};

export type SessionInventorySelectOption = {
  value: string;
  label: string;
  detail: string | null;
};

export const EMPTY_EQUIPPED_ARMOR: Armor = {
  name: "None",
  baseAC: 0,
  dexCap: null,
  armorType: "none",
  allowsDex: true,
  stealthDisadvantage: false,
  minStrength: null,
};

const COIN_ORDER = ["pp", "gp", "ep", "sp", "cp"] as const;

const INVENTORY_GROUP_ORDER = ["weapon", "armor", "magic", "consumable", "misc"] as const;

const getInventoryGroup = (item: Item | null): SessionInventoryResolvedEntry["group"] => {
  if (!item) return "misc";
  if (item.type === ITEM_TYPES.WEAPON) return "weapon";
  if (item.type === ITEM_TYPES.ARMOR) return "armor";
  if (item.type === ITEM_TYPES.MAGIC) return "magic";
  if (item.type === ITEM_TYPES.CONSUMABLE) return "consumable";
  return "misc";
};

export const getInventoryItemName = (entry: InventoryItem, item?: Item | null) =>
  item?.name ?? entry.itemId;

export const resolveInventoryEntries = (
  inventory: InventoryItem[] | null,
  itemsById: Record<string, Item>,
): SessionInventoryResolvedEntry[] =>
  (inventory ?? [])
    .map((entry) => {
      const item = itemsById[entry.itemId] ?? null;
      return {
        entry,
        item,
        group: getInventoryGroup(item),
        name: getInventoryItemName(entry, item),
      };
    })
    .sort((left, right) => {
      const groupDelta =
        INVENTORY_GROUP_ORDER.indexOf(left.group) - INVENTORY_GROUP_ORDER.indexOf(right.group);
      if (groupDelta !== 0) return groupDelta;
      if (left.entry.isEquipped !== right.entry.isEquipped) {
        return left.entry.isEquipped ? -1 : 1;
      }
      if (left.entry.quantity !== right.entry.quantity) {
        return right.entry.quantity - left.entry.quantity;
      }
      return left.name.localeCompare(right.name, "pt-BR");
    });

export const buildInventoryGroups = (
  inventory: InventoryItem[] | null,
  itemsById: Record<string, Item>,
) => {
  const grouped = new Map<SessionInventoryResolvedEntry["group"], SessionInventoryResolvedEntry[]>();
  for (const resolved of resolveInventoryEntries(inventory, itemsById)) {
    const current = grouped.get(resolved.group) ?? [];
    current.push(resolved);
    grouped.set(resolved.group, current);
  }
  return INVENTORY_GROUP_ORDER
    .map((group) => ({
      group,
      entries: grouped.get(group) ?? [],
    }))
    .filter((section) => section.entries.length > 0);
};

export const buildInventorySummary = (
  inventory: InventoryItem[] | null,
  itemsById: Record<string, Item>,
) => {
  const resolved = resolveInventoryEntries(inventory, itemsById);
  return {
    distinctItems: resolved.length,
    equippedCount: resolved.filter((item) => item.entry.isEquipped).length,
    previewItems: resolved.slice(0, 3),
    totalItems: resolved.reduce((sum, item) => sum + item.entry.quantity, 0),
  };
};

export const buildWalletCoins = (wallet: CurrencyWallet | null | undefined) => {
  const current = wallet ?? { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
  return COIN_ORDER.map((coin) => ({
    amount: current[coin],
    coin,
  })).filter((entry) => entry.amount > 0 || entry.coin === "gp");
};

const formatDexRule = (rule: string | null | undefined) => {
  if (rule === "max_2") return "DEX max +2";
  if (rule === "none") return "Sem DEX";
  if (rule === "full") return "DEX completo";
  return null;
};

export const buildWeaponOptions = (
  inventory: InventoryItem[] | null,
  itemsById: Record<string, Item>,
): SessionInventorySelectOption[] =>
  resolveInventoryEntries(inventory, itemsById)
    .filter((entry) => entry.group === "weapon")
    .map(({ entry, item, name }) => ({
      value: entry.id,
      label: name,
      detail: item?.damageDice
        ? `${item.damageDice}${item.damageType ? ` ${item.damageType}` : ""}`
        : null,
    }));

export const buildArmorOptions = (
  inventory: InventoryItem[] | null,
  itemsById: Record<string, Item>,
): SessionInventorySelectOption[] =>
  resolveInventoryEntries(inventory, itemsById)
    .filter((entry) => entry.group === "armor" && !entry.item?.isShield)
    .map(({ entry, item, name }) => ({
      value: entry.id,
      label: name,
      detail:
        item?.armorClassBase != null
          ? `CA ${item.armorClassBase}${formatDexRule(item.dexBonusRule) ? ` · ${formatDexRule(item.dexBonusRule)}` : ""}`
          : null,
    }));

export const buildArmorFromItem = (item?: Item | null): Armor => {
  if (!item || item.type !== ITEM_TYPES.ARMOR || item.isShield) {
    return EMPTY_EQUIPPED_ARMOR;
  }

  const dexCap = item.dexBonusRule === "max_2"
    ? 2
    : item.dexBonusRule === "none"
      ? 0
      : null;
  const armorType =
    item.armorCategory === "light" ||
    item.armorCategory === "medium" ||
    item.armorCategory === "heavy"
      ? item.armorCategory
      : "none";

  if (armorType === "none") {
    return EMPTY_EQUIPPED_ARMOR;
  }

  return {
    name: item.name,
    baseAC: item.armorClassBase ?? 0,
    dexCap,
    armorType,
    allowsDex: item.dexBonusRule !== "none",
    stealthDisadvantage: item.stealthDisadvantage ?? false,
    minStrength: item.strengthRequirement ?? null,
  };
};

export const hasInventoryEntry = (
  inventory: InventoryItem[] | null,
  inventoryItemId: string | null | undefined,
) => Boolean(inventoryItemId && (inventory ?? []).some((entry) => entry.id === inventoryItemId));
