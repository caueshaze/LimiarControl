import { useEffect } from "react";
import { useLocale } from "../../../shared/hooks/useLocale";
import { ShopItemList } from "./ShopItemList";
import { useShop } from "../hooks/useShop";

type ShopPanelProps = {
  open: boolean;
  onClose: () => void;
  sessionId: string;
  campaignId: string;
  onBuy?: (itemId: string) => void;
  onBuyError?: () => void;
};

export const ShopPanel = ({
  open,
  onClose,
  sessionId,
  campaignId,
  onBuy,
  onBuyError,
}: ShopPanelProps) => {
  const { t } = useLocale();
  const { items, itemsLoading, itemsError, buyItem, loadItems } = useShop({
    campaignId,
    sessionId,
    auto: false,
  });

  useEffect(() => {
    if (!open || !sessionId) {
      return;
    }
    void loadItems({ sessionId });
  }, [open, sessionId, loadItems]);

  return (
    <aside
      className={`relative w-full max-w-sm rounded-3xl border border-slate-800 bg-slate-900/50 p-5 transition-all duration-300 ${
        open ? "opacity-100" : "pointer-events-none opacity-0"
      }`}
      aria-hidden={!open}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
            {t("shop.title")}
          </p>
          <h2 className="mt-2 text-xl font-semibold text-white">
            {t("shop.subtitle")}
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            {t("shop.description")}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="h-9 w-9 rounded-full border border-slate-700 text-xs font-semibold text-slate-300 hover:border-slate-500"
          aria-label={t("shop.close") ?? "Close shop"}
        >
          ✕
        </button>
      </div>

      <div className="mt-4">
        {itemsLoading ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-300">
            {t("shop.loading")}
          </div>
        ) : itemsError ? (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            <p>{t("shop.loadErrorDescription")}</p>
            <button
              type="button"
              onClick={() => loadItems({ sessionId })}
              className="mt-3 rounded-full border border-rose-400/40 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-rose-100 hover:border-rose-300"
            >
              {t("shop.retry") ?? "Try again"}
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-300">
            {t("shop.empty")}
          </div>
        ) : (
          <ShopItemList
            items={items}
            onBuy={async (id) => {
              try {
                await buyItem(id);
                onBuy?.(id);
              } catch {
                onBuyError?.();
              }
            }}
          />
        )}
      </div>
    </aside>
  );
};
