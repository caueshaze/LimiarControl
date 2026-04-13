import type { Item } from "../../entities/item";
import type { CurrencyWallet } from "../../shared/api/inventoryRepo";
import type { CurrencyUnit } from "../../shared/utils/money";
import { EMPTY_WALLET, buildWalletDisplay } from "../../features/shop/utils/shopCurrency";
import { localizedItemName } from "../../features/shop/utils/localizedItemName";
import type { CurrencyDraft, GrantFeedback, ItemDraft } from "./gmDashboard.types";

type Props = {
  userId: string;
  locale: string;
  wallet: CurrencyWallet | undefined;
  currencyDraft: CurrencyDraft | undefined;
  itemDraft: ItemDraft | undefined;
  sortedCatalogItems: Item[];
  grantingCurrencyForUserId: string | null;
  grantingItemForUserId: string | null;
  grantFeedback: GrantFeedback | undefined;
  onGrantCurrency: () => void;
  onGrantItem: () => void;
  setCurrencyDraft: (updater: (current: CurrencyDraft | undefined) => CurrencyDraft) => void;
  setItemDraft: (updater: (current: ItemDraft | undefined) => ItemDraft) => void;
};

export const GmDashboardGrantPanels = ({
  userId,
  locale,
  wallet,
  currencyDraft,
  itemDraft,
  sortedCatalogItems,
  grantingCurrencyForUserId,
  grantingItemForUserId,
  grantFeedback,
  onGrantCurrency,
  onGrantItem,
  setCurrencyDraft,
  setItemDraft,
}: Props) => {
  return (
    <>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">
            Give Currency
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {buildWalletDisplay(wallet ?? EMPTY_WALLET).map((coin) => (
              <span key={coin.coin} className={coin.className} title={coin.longLabel}>
                {coin.amount} {coin.shortLabel}
              </span>
            ))}
          </div>
          <div className="mt-3 flex gap-2">
            <input
              type="number"
              min={1}
              value={currencyDraft?.amount ?? ""}
              onChange={(event) =>
                setCurrencyDraft((current) => ({
                  amount: event.target.value,
                  coin: current?.coin ?? "gp",
                }))
              }
              placeholder="10"
              className="w-24 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
            />
            <select
              value={currencyDraft?.coin ?? "gp"}
              onChange={(event) =>
                setCurrencyDraft((current) => ({
                  amount: current?.amount ?? "",
                  coin: event.target.value as CurrencyUnit,
                }))
              }
              className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs uppercase text-white focus:border-limiar-500 focus:outline-none"
            >
              {(["cp", "sp", "ep", "gp", "pp"] as CurrencyUnit[]).map((coin) => (
                <option key={coin} value={coin}>
                  {coin}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={onGrantCurrency}
              disabled={grantingCurrencyForUserId === userId}
              className="rounded-xl bg-emerald-500/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white hover:bg-emerald-500 disabled:opacity-60"
            >
              {grantingCurrencyForUserId === userId ? "Sending..." : "Give"}
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">Give Item</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <select
              value={itemDraft?.itemId ?? sortedCatalogItems[0]?.id ?? ""}
              onChange={(event) =>
                setItemDraft((current) => ({
                  itemId: event.target.value,
                  quantity: current?.quantity ?? "1",
                }))
              }
              className="min-w-48 flex-1 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
            >
              {sortedCatalogItems.length === 0 ? (
                <option value="">No items</option>
              ) : (
                sortedCatalogItems.map((item) => (
                  <option key={item.id} value={item.id}>
                    {localizedItemName(item, locale)}
                  </option>
                ))
              )}
            </select>
            <input
              type="number"
              min={1}
              value={itemDraft?.quantity ?? "1"}
              onChange={(event) =>
                setItemDraft((current) => ({
                  itemId: current?.itemId ?? sortedCatalogItems[0]?.id ?? "",
                  quantity: event.target.value,
                }))
              }
              className="w-20 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={onGrantItem}
              disabled={grantingItemForUserId === userId || sortedCatalogItems.length === 0}
              className="rounded-xl bg-limiar-500/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white hover:bg-limiar-500 disabled:opacity-60"
            >
              {grantingItemForUserId === userId ? "Sending..." : "Give"}
            </button>
          </div>
        </div>
      </div>

      {grantFeedback && (
        <div
          className={`mt-3 rounded-2xl border px-3 py-2 text-[11px] ${
            grantFeedback.tone === "success"
              ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
              : "border-rose-500/20 bg-rose-500/10 text-rose-200"
          }`}
        >
          {grantFeedback.message}
        </div>
      )}
    </>
  );
};
