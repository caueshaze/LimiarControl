import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item, ItemType } from "../../../entities/item";
import { getItemPropertyLabels } from "../../../entities/item";
import { localizedItemName } from "../utils/localizedItemName";
import type {
  CurrencyWallet,
  InventorySellResult,
} from "../../../shared/api/inventoryRepo";
import { ShopItemList } from "./ShopItemList";
import { ShopFilterBar } from "./ShopFilterBar";
import { useShop } from "../hooks/useShop";
import { SHOP_ITEM_TYPES } from "../utils/shopItemTypes";
import {
  ShopPanelHeader,
  ShopPanelInventorySummary,
  ShopPanelSellSection,
} from "./ShopPanelSections";

const normalizeInventoryKey = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();

type ShopPanelProps = {
  open: boolean;
  onClose: () => void;
  sessionId: string;
  campaignId: string;
  inventoryItems?: InventoryItem[] | null;
  wallet?: CurrencyWallet | null;
  onBuy?: (item: Item, inventoryItem: InventoryItem) => void;
  onBuyError?: (message?: string) => void;
  onSell?: (item: Item, result: InventorySellResult) => void;
  onSellError?: (message?: string) => void;
};

export const ShopPanel = ({
  open,
  onClose,
  sessionId,
  campaignId,
  inventoryItems = null,
  wallet = null,
  onBuy,
  onBuyError,
  onSell,
  onSellError,
}: ShopPanelProps) => {
  const { t, locale } = useLocale();
  const { items, itemsLoading, itemsError, buyItem, sellItem, loadItems } = useShop({
    campaignId,
    sessionId,
    auto: false,
  });
  const [pendingItemId, setPendingItemId] = useState<string | null>(null);
  const [recentItemId, setRecentItemId] = useState<string | null>(null);
  const [pendingSellInventoryId, setPendingSellInventoryId] = useState<string | null>(null);
  const [recentSellInventoryId, setRecentSellInventoryId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<"ALL" | ItemType>("ALL");
  const [ownedOnly, setOwnedOnly] = useState(false);
  const recentTimerRef = useRef<number | null>(null);
  const recentSellTimerRef = useRef<number | null>(null);
  const deferredSearch = useDeferredValue(search);

  const canonicalKeyByItemId = useMemo(() => {
    const next: Record<string, string> = {};
    for (const item of items) {
      next[item.id] = item.canonicalKeySnapshot
        ? normalizeInventoryKey(item.canonicalKeySnapshot)
        : normalizeInventoryKey(item.name);
    }
    return next;
  }, [items]);

  const ownedByCanonicalKey = useMemo(() => {
    const next: Record<string, number> = {};
    for (const entry of inventoryItems ?? []) {
      const itemKey = canonicalKeyByItemId[entry.itemId] ?? entry.itemId;
      next[itemKey] = (next[itemKey] ?? 0) + entry.quantity;
    }
    return next;
  }, [canonicalKeyByItemId, inventoryItems]);

  const ownedByItemId = useMemo(() => {
    const next: Record<string, number> = {};
    for (const item of items) {
      next[item.id] = ownedByCanonicalKey[normalizeInventoryKey(item.name)] ?? 0;
    }
    return next;
  }, [items, ownedByCanonicalKey]);

  const inventorySummary = useMemo(() => {
    const unique = Object.keys(ownedByCanonicalKey).length;
    const total = Object.values(ownedByCanonicalKey).reduce((sum, quantity) => sum + quantity, 0);
    return { unique, total };
  }, [ownedByCanonicalKey]);

  const typeCounts = useMemo(() => {
    const counts = Object.fromEntries(SHOP_ITEM_TYPES.map((type) => [type, 0])) as Record<
      ItemType,
      number
    >;
    for (const item of items) {
      counts[item.type] += 1;
    }
    return counts;
  }, [items]);

  const itemsById = useMemo(() => {
    const next: Record<string, Item> = {};
    for (const item of items) {
      next[item.id] = item;
    }
    return next;
  }, [items]);

  const filteredItems = useMemo(() => {
    const normalizedSearch = deferredSearch.trim().toLowerCase();
    return items
      .filter((item) => {
        if (ownedOnly && (ownedByItemId[item.id] ?? 0) === 0) {
          return false;
        }
        if (typeFilter !== "ALL" && item.type !== typeFilter) {
          return false;
        }
        if (!normalizedSearch) {
          return true;
        }
        const haystack = [
          item.name,
          item.nameEnSnapshot,
          item.namePtSnapshot,
          item.canonicalKeySnapshot,
          item.description,
          item.type,
          ...(item.properties ?? []),
          ...getItemPropertyLabels(item.properties, locale),
        ].filter(Boolean).join(" ").toLowerCase();
        return haystack.includes(normalizedSearch);
      })
      .sort((left, right) => localizedItemName(left, locale).localeCompare(localizedItemName(right, locale)));
  }, [deferredSearch, items, locale, ownedByItemId, ownedOnly, typeFilter]);

  const hasFilteredResults = filteredItems.length > 0;

  useEffect(() => {
    if (!open || !sessionId) {
      return;
    }
    void loadItems({ sessionId });
  }, [open, sessionId, loadItems]);

  useEffect(() => {
    return () => {
      if (recentTimerRef.current) {
        window.clearTimeout(recentTimerRef.current);
      }
      if (recentSellTimerRef.current) {
        window.clearTimeout(recentSellTimerRef.current);
      }
    };
  }, []);

  return (
    <aside
      className={`relative w-full rounded-3xl border border-slate-800 bg-slate-900/50 p-5 transition-all duration-300 ${
        open ? "opacity-100" : "pointer-events-none opacity-0"
      }`}
      aria-hidden={!open}
    >
      <ShopPanelHeader
        closeLabel={t("shop.close") ?? "Close shop"}
        description={t("shop.description")}
        subtitle={t("shop.subtitle")}
        title={t("shop.title")}
        onClose={onClose}
      />

      <div className="mt-4">
        {itemsLoading ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-300">
            {t("shop.loading")}
          </div>
        ) : itemsError ? (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            <p>{t("shop.loadErrorDescription")}</p>
            <button
              type="button"
              onClick={() => loadItems({ sessionId })}
              className="mt-3 rounded-full border border-rose-400/40 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-rose-100 hover:border-rose-300"
            >
              {t("shop.retry") ?? "Try again"}
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-300">
            {t("shop.empty")}
          </div>
        ) : (
          <div className="space-y-4">
            <ShopPanelInventorySummary
              inventorySummary={inventorySummary}
              totalLabel={t("shop.panel.total")}
              uniqueLabel={t("shop.panel.unique")}
              wallet={wallet}
              walletLabel={t("shop.panel.wallet")}
            />

            <ShopPanelSellSection
              description={t("shop.sell.description")}
              inventoryItems={inventoryItems ?? []}
              itemsById={itemsById}
              pendingInventoryId={pendingSellInventoryId}
              recentInventoryId={recentSellInventoryId}
              title={t("shop.sell.title")}
              onSell={async (inventoryItemId) => {
                const inventoryEntry = (inventoryItems ?? []).find((entry) => entry.id === inventoryItemId);
                if (!inventoryEntry) {
                  return;
                }
                const selectedItem = itemsById[inventoryEntry.itemId];
                if (!selectedItem) {
                  return;
                }
                setPendingSellInventoryId(inventoryItemId);
                try {
                  const result = await sellItem(inventoryItemId);
                  if (recentSellTimerRef.current) {
                    window.clearTimeout(recentSellTimerRef.current);
                  }
                  setRecentSellInventoryId(inventoryItemId);
                  recentSellTimerRef.current = window.setTimeout(() => {
                    setRecentSellInventoryId(null);
                    recentSellTimerRef.current = null;
                  }, 1800);
                  onSell?.(selectedItem, result);
                } catch (error) {
                  const message = (error as { message?: string })?.message;
                  onSellError?.(message);
                } finally {
                  setPendingSellInventoryId(null);
                }
              }}
            />

            <ShopFilterBar
              filteredCount={filteredItems.length}
              ownedCount={inventorySummary.unique}
              ownedOnly={ownedOnly}
              onClear={() => {
                setSearch("");
                setTypeFilter("ALL");
                setOwnedOnly(false);
              }}
              onOwnedOnlyChange={setOwnedOnly}
              onSearchChange={setSearch}
              onTypeFilterChange={setTypeFilter}
              search={search}
              totalCount={items.length}
              typeCounts={typeCounts}
              typeFilter={typeFilter}
            />

            <div className="max-h-[32rem] overflow-y-auto pr-1">
              <ShopItemList
                emptyMessage={hasFilteredResults ? undefined : t("shop.panel.emptyFiltered")}
                items={filteredItems}
                ownedByItemId={ownedByItemId}
                pendingItemId={pendingItemId}
                recentItemId={recentItemId}
                onBuy={async (id) => {
                  const selectedItem = items.find((item) => item.id === id);
                  if (!selectedItem) {
                    return;
                  }
                  setPendingItemId(id);
                  try {
                    const inventoryItem = await buyItem(id);
                    if (recentTimerRef.current) {
                      window.clearTimeout(recentTimerRef.current);
                    }
                    setRecentItemId(id);
                    recentTimerRef.current = window.setTimeout(() => {
                      setRecentItemId(null);
                      recentTimerRef.current = null;
                    }, 1800);
                    onBuy?.(selectedItem, inventoryItem);
                  } catch (error) {
                    const message = (error as { message?: string })?.message;
                    onBuyError?.(message);
                  } finally {
                    setPendingItemId(null);
                  }
                }}
              />
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
