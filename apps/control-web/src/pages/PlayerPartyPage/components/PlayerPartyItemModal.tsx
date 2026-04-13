import { getItemPropertyLabel } from "../../../entities/item";
import { localizedItemName } from "../../../features/shop/utils/localizedItemName";
import { formatItemPrice } from "../../../features/shop/utils/shopCurrency";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { PlayerPartySelectedItem } from "../playerParty.types";
import { getItemTypeLabel } from "../playerParty.utils";

type Props = {
  selectedItem: PlayerPartySelectedItem | null;
  onClose: () => void;
};

export const PlayerPartyItemModal = ({ selectedItem, onClose }: Props) => {
  const { t, locale } = useLocale();

  if (!selectedItem) {
    return null;
  }

  const { item, inv } = selectedItem;
  const propertyNames = (item.properties ?? []).map((property) =>
    getItemPropertyLabel(property, locale),
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 backdrop-blur-sm sm:items-center sm:px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md overflow-hidden rounded-t-3xl border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.98),rgba(2,6,23,0.98))] shadow-2xl sm:rounded-3xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex justify-center pt-3 sm:hidden">
          <span className="h-1 w-10 rounded-full bg-slate-700" />
        </div>

        <div className="px-6 pb-8 pt-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-limiar-200">
                {getItemTypeLabel(item.type, t)}
              </p>
              <h2 className="mt-1 text-xl font-bold text-white">{localizedItemName(item, locale)}</h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="mt-0.5 shrink-0 rounded-full border border-white/10 p-1.5 text-slate-400 transition hover:border-white/20 hover:text-white"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 16 16"
                fill="currentColor"
                className="h-3.5 w-3.5"
              >
                <path d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z" />
              </svg>
            </button>
          </div>

          {item.damageDice || item.price != null || item.weight != null || item.rangeMeters != null ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {item.damageDice ? (
                <span className="rounded-full border border-rose-500/20 bg-rose-500/10 px-3 py-1 text-xs font-semibold text-rose-200">
                  {item.damageDice}
                </span>
              ) : null}
              {item.rangeMeters != null ? (
                <span className="rounded-full border border-sky-500/20 bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-200">
                  {item.rangeMeters}m
                </span>
              ) : null}
              {item.weight != null ? (
                <span className="rounded-full border border-white/10 bg-white/4 px-3 py-1 text-xs font-semibold text-slate-200">
                  {item.weight} kg
                </span>
              ) : null}
              {item.price != null ? (
                <span className="rounded-full border border-amber-500/20 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-200">
                  {formatItemPrice(item.price, item.priceLabel, item.priceCopperValue)}
                </span>
              ) : null}
            </div>
          ) : null}

          {propertyNames.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-1.5">
              {propertyNames.map((property) => (
                <span
                  key={property}
                  className="rounded-full border border-white/10 bg-white/4 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-300"
                >
                  {property}
                </span>
              ))}
            </div>
          ) : null}

          {item.description ? (
            <p className="mt-4 text-sm leading-7 text-slate-300">{item.description}</p>
          ) : null}

          {inv.notes ? (
            <div className="mt-4 rounded-2xl border border-white/8 bg-white/3 px-4 py-3">
              <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                {t("inventory.notes")}
              </p>
              <p className="text-sm text-slate-200">{inv.notes}</p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
