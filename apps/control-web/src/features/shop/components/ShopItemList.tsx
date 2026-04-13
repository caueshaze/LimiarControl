import type { Item } from "../../../entities/item";
import { ShopItemCard } from "./ShopItemCard";
import { useLocale } from "../../../shared/hooks/useLocale";

type ShopItemListProps = {
  emptyMessage?: string;
  items: Item[];
  ownedByItemId?: Record<string, number>;
  pendingItemId?: string | null;
  recentItemId?: string | null;
  onBuy?: (itemId: string) => Promise<void> | void;
};

export const ShopItemList = ({
  emptyMessage,
  items,
  ownedByItemId = {},
  pendingItemId = null,
  recentItemId = null,
  onBuy,
}: ShopItemListProps) => {
  const { t } = useLocale();
  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
        {emptyMessage ?? t("shop.empty")}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <ShopItemCard
          key={item.id}
          item={item}
          ownedQuantity={ownedByItemId[item.id] ?? 0}
          isBuying={pendingItemId === item.id}
          didJustBuy={recentItemId === item.id}
          onBuy={onBuy}
        />
      ))}
    </div>
  );
};
