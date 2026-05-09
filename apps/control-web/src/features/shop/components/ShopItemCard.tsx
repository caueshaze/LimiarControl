import { useMemo, useState } from "react";
import type { Item } from "../../../entities/item";
import { getItemPropertyLabels } from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";
import { LB_TO_KG, computeProjectedEncumbranceTier } from "../../../features/character-sheet/utils/calculations";
import type { EncumbranceTier } from "../../../features/character-sheet/utils/calculations";
import { getShopItemTypeLabelKey } from "../utils/shopItemTypes";
import { localizedItemName } from "../utils/localizedItemName";
import {
  formatItemPrice,
  formatPriceMoney,
  getItemPriceCopperValue,
} from "../utils/shopCurrency";
import { hasEnough, subtractMoney } from "../../../shared/utils/money";
import type { CurrencyWallet } from "../../../shared/api/inventoryRepo";

type ShopItemCardProps = {
  item: Item;
  wallet?: CurrencyWallet | null;
  ownedQuantity?: number;
  isBuying?: boolean;
  didJustBuy?: boolean;
  onBuy?: (itemId: string) => Promise<void> | void;
  strengthScore?: number;
  currentTotalWeightKg?: number;
  currentEncumbranceTier?: EncumbranceTier;
};

const encumbranceWarningColor: Record<string, string> = {
  encumbered: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  heavily_encumbered: "border-orange-500/30 bg-orange-500/10 text-orange-300",
  overloaded: "border-red-500/30 bg-red-500/10 text-red-300",
};

export const ShopItemCard = ({
  item,
  wallet = null,
  ownedQuantity = 0,
  isBuying = false,
  didJustBuy = false,
  onBuy,
  strengthScore,
  currentTotalWeightKg,
  currentEncumbranceTier,
}: ShopItemCardProps) => {
  const { t, locale } = useLocale();
  const [expanded, setExpanded] = useState(false);

  const projectedTier = useMemo(() => {
    if (strengthScore == null || currentTotalWeightKg == null || !currentEncumbranceTier) return null;
    const result = computeProjectedEncumbranceTier({
      strengthScore,
      currentWeightKg: currentTotalWeightKg,
      addedWeightLb: item.weight ?? 0,
    });
    return result.tier !== currentEncumbranceTier ? result.tier : null;
  }, [strengthScore, currentTotalWeightKg, currentEncumbranceTier, item.weight]);

  const propertyLabels = getItemPropertyLabels(item.properties, locale);
  const priceCopperValue = getItemPriceCopperValue(item.price, item.priceCopperValue);
  const canAfford = hasEnough(wallet, priceCopperValue);
  const missingAmount = Math.max(0, priceCopperValue - (wallet?.copperValue ?? 0));
  const balanceAfter = subtractMoney(wallet, priceCopperValue).copperValue;
  const detailBits = [
    item.damageDice ? `${t("shop.card.damage")} ${item.damageDice}` : null,
    item.rangeMeters ? `${t("shop.card.range")} ${item.rangeMeters}m` : null,
    item.weight ? `${t("shop.card.weight")} ${Math.round(item.weight * LB_TO_KG * 100) / 100} kg` : null,
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
            {projectedTier && projectedTier !== "normal" && (
              <span className={`rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em] ${encumbranceWarningColor[projectedTier] ?? ""}`}>
                {t(`shop.card.encumbranceWarning.${projectedTier}`)}
              </span>
            )}
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
            <span className="rounded-full bg-slate-100 px-3 py-1 font-semibold text-slate-900">
              {formatItemPrice(item.price, item.priceLabel, item.priceCopperValue)}
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

          {onBuy && (
            <div className="mt-3 space-y-1">
              {!canAfford ? (
                <p className="text-xs font-medium text-rose-300">
                  {t("shop.card.cannotAfford").replace("{amount}", formatPriceMoney(missingAmount))}
                </p>
              ) : (
                <p className="text-xs text-emerald-300">
                  {t("shop.card.balanceAfter").replace("{amount}", formatPriceMoney(balanceAfter))}
                </p>
              )}
            </div>
          )}
        </div>

        {onBuy && (
          <div className="flex shrink-0 items-center justify-end lg:min-w-[9rem]">
            <button
              type="button"
              onClick={() => onBuy(item.id)}
              disabled={isBuying || !canAfford}
              className={`w-full rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition disabled:cursor-not-allowed disabled:opacity-60 lg:w-auto ${
                canAfford
                  ? "bg-slate-100 text-slate-900 hover:bg-white"
                  : "bg-slate-800 text-slate-400"
              }`}
            >
              {isBuying ? t("shop.card.buying") : t("shop.card.buy")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
