import type { Item } from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";

type ShopItemCardProps = {
  item: Item;
  onBuy?: (itemId: string) => void;
};

export const ShopItemCard = ({ item, onBuy }: ShopItemCardProps) => {
  const { t } = useLocale();

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-200">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-base font-semibold text-slate-100">{item.name}</p>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
            {item.type}
          </p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-900">
          {item.price ?? "—"}
        </span>
      </div>
      <p className="mt-3 text-xs text-slate-400">{item.description}</p>
      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-slate-400">
        {item.damageDice && (
          <span>
            {t("shop.card.damage")} {item.damageDice}
          </span>
        )}
        {item.rangeMeters && (
          <span>
            {t("shop.card.range")} {item.rangeMeters}m
          </span>
        )}
        {item.weight && (
          <span>
            {t("shop.card.weight")} {item.weight}
          </span>
        )}
      </div>
      {item.properties && item.properties.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {item.properties.map((prop) => (
            <span
              key={prop}
              className="rounded-full border border-slate-700 px-2 py-0.5 text-xs text-slate-300"
            >
              {prop}
            </span>
          ))}
        </div>
      )}
      {onBuy && (
        <button
          type="button"
          onClick={() => onBuy(item.id)}
          className="mt-4 w-full rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-900"
        >
          {t("shop.card.buy")}
        </button>
      )}
    </div>
  );
};
