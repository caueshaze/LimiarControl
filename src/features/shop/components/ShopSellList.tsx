import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";
import { formatItemPrice } from "../utils/shopCurrency";
import { localizedItemName } from "../utils/localizedItemName";

type ShopSellListProps = {
  itemsById: Record<string, Item>;
  inventoryItems: InventoryItem[];
  pendingInventoryId?: string | null;
  recentInventoryId?: string | null;
  onSell?: (inventoryItemId: string) => Promise<void> | void;
};

export const ShopSellList = ({
  itemsById,
  inventoryItems,
  pendingInventoryId = null,
  recentInventoryId = null,
  onSell,
}: ShopSellListProps) => {
  const { t, locale } = useLocale();

  if (inventoryItems.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
        {t("shop.sell.empty")}
      </div>
    );
  }

  const sortedItems = [...inventoryItems].sort((left, right) => {
    const leftItem = itemsById[left.itemId];
    const rightItem = itemsById[right.itemId];
    const leftName = leftItem ? localizedItemName(leftItem, locale) : left.itemId;
    const rightName = rightItem ? localizedItemName(rightItem, locale) : right.itemId;
    return leftName.localeCompare(rightName);
  });

  return (
    <div className="space-y-2">
      {sortedItems.map((entry) => {
        const item = itemsById[entry.itemId];
        const isPending = pendingInventoryId === entry.id;
        const wasSold = recentInventoryId === entry.id;
        return (
          <div
            key={entry.id}
            className={`rounded-2xl border px-4 py-3 transition-all ${
              wasSold
                ? "border-emerald-500/30 bg-emerald-500/10"
                : "border-slate-800 bg-slate-900/40"
            }`}
          >
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-white">
                    {item ? localizedItemName(item, locale) : t("inventory.unknownItem")}
                  </p>
                  <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] text-slate-400">
                    x{entry.quantity}
                  </span>
                  {wasSold && (
                    <span className="rounded-full border border-emerald-500/30 bg-emerald-500/15 px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] text-emerald-300">
                      {t("shop.sell.sold")}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  {t("shop.sell.refund")} {formatItemPrice(item?.price, item?.priceLabel)}
                </p>
              </div>

              {onSell && (
                <button
                  type="button"
                  onClick={() => onSell(entry.id)}
                  disabled={isPending}
                  className="rounded-full border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-amber-200 transition hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isPending ? t("shop.sell.selling") : t("shop.sell.action")}
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
