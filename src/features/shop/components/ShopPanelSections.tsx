import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import type { CurrencyWallet, InventorySellResult } from "../../../shared/api/inventoryRepo";
import { buildWalletDisplay } from "../utils/shopCurrency";
import { ShopSellList } from "./ShopSellList";

type HeaderProps = {
  closeLabel: string;
  description: string;
  subtitle: string;
  title: string;
  onClose: () => void;
};

export const ShopPanelHeader = ({
  closeLabel,
  description,
  subtitle,
  title,
  onClose,
}: HeaderProps) => (
  <div className="flex items-start justify-between gap-3">
    <div>
      <p className="text-xs uppercase tracking-[0.3em] text-slate-400">{title}</p>
      <h2 className="mt-2 text-xl font-semibold text-white">{subtitle}</h2>
      <p className="mt-2 text-sm text-slate-400">{description}</p>
    </div>
    <button
      type="button"
      onClick={onClose}
      className="h-9 w-9 rounded-full border border-slate-700 text-xs font-semibold text-slate-300 hover:border-slate-500"
      aria-label={closeLabel}
    >
      ✕
    </button>
  </div>
);

type SummaryProps = {
  inventorySummary: { total: number; unique: number };
  uniqueLabel: string;
  totalLabel: string;
  wallet: CurrencyWallet | null;
  walletLabel: string;
};

export const ShopPanelInventorySummary = ({
  inventorySummary,
  totalLabel,
  uniqueLabel,
  wallet,
  walletLabel,
}: SummaryProps) => {
  const walletCoins = buildWalletDisplay(wallet);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
      <p className="text-[11px] uppercase tracking-[0.3em] text-slate-500">Inventario</p>
      <div className="mt-3 flex flex-wrap gap-3">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 px-3 py-2">
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">{uniqueLabel}</p>
          <p className="mt-1 text-lg font-semibold text-white">{inventorySummary.unique}</p>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 px-3 py-2">
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">{totalLabel}</p>
          <p className="mt-1 text-lg font-semibold text-white">{inventorySummary.total}</p>
        </div>
        <div className="min-w-[15rem] rounded-2xl border border-slate-800 bg-slate-900/60 px-3 py-2">
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">{walletLabel}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {walletCoins.map((coin) => (
              <span key={coin.coin} className={coin.className} title={coin.longLabel}>
                {coin.amount} {coin.shortLabel}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

type SellSectionProps = {
  description: string;
  inventoryItems: InventoryItem[];
  itemsById: Record<string, Item>;
  pendingInventoryId: string | null;
  recentInventoryId: string | null;
  title: string;
  onSell: (inventoryItemId: string) => Promise<void>;
};

export const ShopPanelSellSection = ({
  description,
  inventoryItems,
  itemsById,
  pendingInventoryId,
  recentInventoryId,
  title,
  onSell,
}: SellSectionProps) => (
  <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
    <div className="flex items-center justify-between gap-3">
      <div>
        <p className="text-[11px] uppercase tracking-[0.3em] text-slate-500">{title}</p>
        <p className="mt-1 text-sm text-slate-400">{description}</p>
      </div>
    </div>

    <div className="mt-4 max-h-56 overflow-y-auto pr-1">
      <ShopSellList
        inventoryItems={inventoryItems}
        itemsById={itemsById}
        pendingInventoryId={pendingInventoryId}
        recentInventoryId={recentInventoryId}
        onSell={onSell}
      />
    </div>
  </div>
);
