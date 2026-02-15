import type { Item } from "../../../entities/item";
import { ShopItemCard } from "./ShopItemCard";
import { useLocale } from "../../../shared/hooks/useLocale";

type ShopItemListProps = {
  items: Item[];
  onBuy?: (itemId: string) => void;
};

export const ShopItemList = ({ items, onBuy }: ShopItemListProps) => {
  const { t } = useLocale();
  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
        {t("shop.empty")}
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {items.map((item) => (
        <ShopItemCard key={item.id} item={item} onBuy={onBuy} />
      ))}
    </div>
  );
};
