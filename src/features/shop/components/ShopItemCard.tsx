import { useState } from "react";
import type { Item } from "../../../entities/item";
import { getItemPropertyLabels } from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";
import { getShopItemTypeLabelKey } from "../utils/shopItemTypes";
import { localizedItemName } from "../utils/localizedItemName";

type ShopItemCardProps = {
  item: Item;
  ownedQuantity?: number;
  isBuying?: boolean;
  didJustBuy?: boolean;
  onBuy?: (itemId: string) => Promise<void> | void;
};

export const ShopItemCard = ({
  item,
  ownedQuantity = 0,
  isBuying = false,
  didJustBuy = false,
  onBuy,
}: ShopItemCardProps) => {
  const { t, locale } = useLocale();
  const [expanded, setExpanded] = useState(false);
  const propertyLabels = getItemPropertyLabels(item.properties, locale);
  const detailBits = [
    item.damageDice ? `${t("shop.card.damage")} ${item.damageDice}` : null,
    item.rangeMeters ? `${t("shop.card.range")} ${item.rangeMeters}m` : null,
    item.weight ? `${t("shop.card.weight")} ${item.weight}` : null,
  ].filter(Boolean);
  const hasExpandableContent =
    item.description.length > 96 || propertyLabels.length > 0 || detailBits.length > 0;

  return (
    <div
      className={`rounded-2xl border p-4 text-sm text-slate-200 transition-all ${
        didJustBuy
          ? "border-emerald-500/40 bg-emerald-500/10 shadow-[0_0_25px_rgba(16,185,129,0.15)]"
          : "border-slate-800 bg-slate-900/40"
      }`}
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-base font-semibold text-slate-100">{localizedItemName(item, locale)}</p>
            <span className="rounded-full border border-slate-700 bg-slate-950/80 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-300">
              {t(getShopItemTypeLabelKey(item.type))}
            </span>
            {ownedQuantity > 0 && (
              <span className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-200">
                {t("shop.card.owned")} {ownedQuantity}
              </span>
            )}
            {didJustBuy && (
              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/15 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-emerald-300">
                {t("shop.card.added")}
              </span>
            )}
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
            <span className="rounded-full bg-slate-100 px-3 py-1 font-semibold text-slate-900">
              {item.priceLabel ?? item.price ?? "—"}
            </span>
            {detailBits.map((bit) => (
              <span
                key={bit}
                className="rounded-full border border-slate-800 bg-slate-950/60 px-2 py-1 text-slate-400"
              >
                {bit}
              </span>
            ))}
          </div>

          <p className={`mt-2 text-xs text-slate-400 ${expanded ? "" : "line-clamp-1"}`}>
            {item.description}
          </p>

          {expanded && propertyLabels.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
              {propertyLabels.map((prop) => (
                <span
                  key={prop}
                  className="rounded-full border border-slate-700 px-2 py-1 text-[11px] text-slate-300"
                >
                  {prop}
                </span>
              ))}
            </div>
          )}

          {hasExpandableContent && (
            <button
              type="button"
              onClick={() => setExpanded((current) => !current)}
              className="mt-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-limiar-300 transition hover:text-limiar-200"
            >
              {expanded ? t("shop.card.hideDetails") : t("shop.card.showDetails")}
            </button>
          )}
        </div>

        {onBuy && (
          <div className="flex shrink-0 items-center justify-end lg:min-w-[9rem]">
            <button
              type="button"
              onClick={() => onBuy(item.id)}
              disabled={isBuying}
              className="w-full rounded-full bg-slate-100 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-900 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60 lg:w-auto"
            >
              {isBuying ? t("shop.card.buying") : t("shop.card.buy")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
