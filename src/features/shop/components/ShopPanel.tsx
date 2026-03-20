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
import { ShopSellList } from "./ShopSellList";
import { useShop } from "../hooks/useShop";
import { formatWallet } from "../utils/shopCurrency";
import { SHOP_ITEM_TYPES } from "../utils/shopItemTypes";

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
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
            {t("shop.title")}
          </p>
          <h2 className="mt-2 text-xl font-semibold text-white">
            {t("shop.subtitle")}
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            {t("shop.description")}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="h-9 w-9 rounded-full border border-slate-700 text-xs font-semibold text-slate-300 hover:border-slate-500"
          aria-label={t("shop.close") ?? "Close shop"}
        >
          ✕
        </button>
      </div>

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
            <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <p className="text-[11px] uppercase tracking-[0.3em] text-slate-500">
                {t("shop.panel.inventory")}
              </p>
              <div className="mt-3 flex flex-wrap gap-3">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    {t("shop.panel.unique")}
                  </p>
                  <p className="mt-1 text-lg font-semibold text-white">{inventorySummary.unique}</p>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    {t("shop.panel.total")}
                  </p>
                  <p className="mt-1 text-lg font-semibold text-white">{inventorySummary.total}</p>
                </div>
                <div className="min-w-[12rem] rounded-2xl border border-slate-800 bg-slate-900/60 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    {t("shop.panel.wallet")}
                  </p>
                  <p className="mt-1 text-sm font-semibold text-white">{formatWallet(wallet)}</p>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.3em] text-slate-500">
                    {t("shop.sell.title")}
                  </p>
                  <p className="mt-1 text-sm text-slate-400">
                    {t("shop.sell.description")}
                  </p>
                </div>
              </div>

              <div className="mt-4 max-h-56 overflow-y-auto pr-1">
                <ShopSellList
                  inventoryItems={inventoryItems ?? []}
                  itemsById={itemsById}
                  pendingInventoryId={pendingSellInventoryId}
                  recentInventoryId={recentSellInventoryId}
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
              </div>
            </div>

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
