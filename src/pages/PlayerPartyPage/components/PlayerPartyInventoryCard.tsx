import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import { localizedItemName } from "../../../features/shop/utils/localizedItemName";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { PlayerPartySelectedItem } from "../playerParty.types";
import { getItemTypeLabel } from "../playerParty.utils";

type Props = {
  inventory: InventoryItem[] | null;
  catalogItems: Record<string, Item>;
  onSelectItem: (item: PlayerPartySelectedItem) => void;
};

export const PlayerPartyInventoryCard = ({
  inventory,
  catalogItems,
  onSelectItem,
}: Props) => {
  const { locale, t } = useLocale();

  return (
    <section className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] px-6 py-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <div className="flex items-start justify-between gap-4 border-b border-white/8 pb-4">
        <div className="space-y-1">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
            {t("playerParty.inventoryTitle")}
          </p>
          <h2 className="text-xl font-semibold text-white">
            {t("playerParty.inventoryHeading")}
          </h2>
          <p className="text-sm leading-7 text-slate-400">
            {t("playerParty.inventoryDescription")}
          </p>
        </div>
        <span className="rounded-full border border-white/8 bg-white/4 px-3 py-1.5 text-xs font-semibold text-slate-200">
          {inventory?.length ?? 0}
        </span>
      </div>

      {inventory === null ? (
        <p className="py-5 text-sm text-slate-400">{t("playerParty.inventoryLoading")}</p>
      ) : inventory.length === 0 ? (
        <p className="py-5 text-sm leading-7 text-slate-400">
          {t("playerParty.inventoryEmpty")}
        </p>
      ) : (
        <div className="mt-4 space-y-3">
          {inventory.map((inventoryItem) => {
            const catalogItem = catalogItems[inventoryItem.itemId];

            return (
              <button
                key={inventoryItem.id}
                type="button"
                onClick={() =>
                  catalogItem
                    ? onSelectItem({ item: catalogItem, inv: inventoryItem })
                    : undefined
                }
                className={`flex w-full items-center justify-between gap-4 rounded-[22px] border px-4 py-3 text-left transition ${
                  catalogItem
                    ? "border-white/8 bg-white/3 hover:border-white/14 hover:bg-white/5"
                    : "cursor-default border-white/8 bg-white/3"
                }`}
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-white">
                    {catalogItem ? localizedItemName(catalogItem, locale) : t("inventory.unknownItem")}
                  </p>
                  <p className="truncate text-xs text-slate-500">
                    {getItemTypeLabel(catalogItem?.type, t)}
                  </p>
                </div>

                <div className="flex flex-wrap items-center justify-end gap-2">
                  <span className="rounded-full border border-white/10 bg-white/4 px-2.5 py-1 text-xs font-semibold text-slate-200">
                    x{inventoryItem.quantity}
                  </span>
                  {inventoryItem.isEquipped ? (
                    <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-emerald-200">
                      {t("playerParty.equipped")}
                    </span>
                  ) : null}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
};
