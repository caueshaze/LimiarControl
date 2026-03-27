import { ITEM_TYPES, type Item } from "../../../entities/item";
import type { InventoryItem } from "../../../entities/inventory";
import type { Armor } from "../../character-sheet/model/characterSheet.types";
import type { CurrencyWallet } from "../../../shared/api/inventoryRepo";
import {
  formatDamageLabel,
  localizeBaseItemDexBonusRule,
} from "../../../shared/i18n/domainLabels";
import { localizedItemName } from "../../shop/utils/localizedItemName";
import { buildWalletDisplay } from "../../shop/utils/shopCurrency";

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

export type SessionInventoryFilterGroup = "all" | SessionInventoryResolvedEntry["group"];

export type SessionInventoryFilterState = {
  equippedOnly: boolean;
  group: SessionInventoryFilterGroup;
  search: string;
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

const INVENTORY_GROUP_ORDER = ["weapon", "armor", "magic", "consumable", "misc"] as const;

const getInventoryGroup = (item: Item | null): SessionInventoryResolvedEntry["group"] => {
  if (!item) return "misc";
  if (item.type === ITEM_TYPES.WEAPON) return "weapon";
  if (item.type === ITEM_TYPES.ARMOR) return "armor";
  if (item.type === ITEM_TYPES.MAGIC) return "magic";
  if (item.type === ITEM_TYPES.CONSUMABLE) return "consumable";
  return "misc";
};

export const getInventoryItemName = (
  entry: InventoryItem,
  item: Item | null | undefined,
  locale: "en" | "pt" | string,
) => (item ? localizedItemName(item, locale) : entry.itemId);

export const resolveInventoryEntries = (
  inventory: InventoryItem[] | null,
  itemsById: Record<string, Item>,
  locale: "en" | "pt" | string,
): SessionInventoryResolvedEntry[] =>
  (inventory ?? [])
    .map((entry) => {
      const item = itemsById[entry.itemId] ?? null;
      return {
        entry,
        item,
        group: getInventoryGroup(item),
        name: getInventoryItemName(entry, item, locale),
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
  locale: "en" | "pt" | string,
) => {
  const grouped = new Map<SessionInventoryResolvedEntry["group"], SessionInventoryResolvedEntry[]>();
  for (const resolved of resolveInventoryEntries(inventory, itemsById, locale)) {
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

const normalizeSearch = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

export const filterInventoryEntries = (
  entries: SessionInventoryResolvedEntry[],
  filters: SessionInventoryFilterState,
) => {
  const needle = normalizeSearch(filters.search);

  return entries.filter((resolved) => {
    if (filters.group !== "all" && resolved.group !== filters.group) {
      return false;
    }
    if (filters.equippedOnly && !resolved.entry.isEquipped) {
      return false;
    }
    if (!needle) {
      return true;
    }

    const haystack = normalizeSearch([
      resolved.name,
      resolved.item?.description ?? "",
      ...(resolved.item?.properties ?? []),
      resolved.entry.notes ?? "",
      resolved.group,
    ].join(" "));

    return haystack.includes(needle);
  });
};

export const buildInventoryGroupsFromResolved = (
  entries: SessionInventoryResolvedEntry[],
) =>
  INVENTORY_GROUP_ORDER
    .map((group) => ({
      group,
      entries: entries.filter((entry) => entry.group === group),
    }))
    .filter((section) => section.entries.length > 0);

export const buildInventorySummary = (
  inventory: InventoryItem[] | null,
  itemsById: Record<string, Item>,
  locale: "en" | "pt" | string,
) => {
  const resolved = resolveInventoryEntries(inventory, itemsById, locale);
  return {
    distinctItems: resolved.length,
    equippedCount: resolved.filter((item) => item.entry.isEquipped).length,
    previewItems: resolved.slice(0, 3),
    totalItems: resolved.reduce((sum, item) => sum + item.entry.quantity, 0),
  };
};

export const buildWalletCoins = (wallet: CurrencyWallet | null | undefined) => {
  return buildWalletDisplay(wallet);
};

export const buildWeaponOptions = (
  inventory: InventoryItem[] | null,
  itemsById: Record<string, Item>,
  locale: "en" | "pt" | string,
): SessionInventorySelectOption[] =>
  resolveInventoryEntries(inventory, itemsById, locale)
    .filter((entry) => entry.group === "weapon")
    .map(({ entry, item, name }) => ({
      value: entry.id,
      label: name,
      detail: item?.damageDice ? formatDamageLabel(item.damageDice, item.damageType, locale) : null,
    }));

export const buildArmorOptions = (
  inventory: InventoryItem[] | null,
  itemsById: Record<string, Item>,
  locale: "en" | "pt" | string,
): SessionInventorySelectOption[] =>
  resolveInventoryEntries(inventory, itemsById, locale)
    .filter((entry) => entry.group === "armor" && !entry.item?.isShield)
    .map(({ entry, item, name }) => ({
      value: entry.id,
      label: name,
      detail:
        item?.armorClassBase != null
          ? `CA ${item.armorClassBase}${localizeBaseItemDexBonusRule(item.dexBonusRule, locale) ? ` · ${localizeBaseItemDexBonusRule(item.dexBonusRule, locale)}` : ""}`
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
