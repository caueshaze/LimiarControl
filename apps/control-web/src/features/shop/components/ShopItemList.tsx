import type { Item } from "../../../entities/item";
import type { EncumbranceTier } from "../../../features/character-sheet/utils/calculations";
import type { CurrencyWallet } from "../../../shared/api/inventoryRepo";
import { ShopItemCard } from "./ShopItemCard";
import { useLocale } from "../../../shared/hooks/useLocale";

type ShopItemListProps = {
  emptyMessage?: string;
  items: Item[];
  wallet?: CurrencyWallet | null;
  ownedByItemId?: Record<string, number>;
  pendingItemId?: string | null;
  recentItemId?: string | null;
  onBuy?: (itemId: string) => Promise<void> | void;
  strengthScore?: number;
  currentTotalWeightKg?: number;
  currentEncumbranceTier?: EncumbranceTier;
};

export const ShopItemList = ({
  emptyMessage,
  items,
  wallet = null,
  ownedByItemId = {},
  pendingItemId = null,
  recentItemId = null,
  onBuy,
  strengthScore,
  currentTotalWeightKg,
  currentEncumbranceTier,
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
          wallet={wallet}
          ownedQuantity={ownedByItemId[item.id] ?? 0}
          isBuying={pendingItemId === item.id}
          didJustBuy={recentItemId === item.id}
          onBuy={onBuy}
          strengthScore={strengthScore}
          currentTotalWeightKg={currentTotalWeightKg}
          currentEncumbranceTier={currentEncumbranceTier}
        />
      ))}
    </div>
  );
};
