import { Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { ShopItemList, useShop } from "../../features/shop";
import { useLocale } from "../../shared/hooks/useLocale";

export const ShopPage = () => {
  const { items, itemsLoading, itemsError, selectedCampaignId } = useShop();
  const { t } = useLocale();

  if (!selectedCampaignId) {
    return (
      <section className="space-y-4">
        <h1 className="text-2xl font-semibold">{t("shop.title")}</h1>
        <p className="text-sm text-slate-400">
          {t("shop.noCampaign")}
        </p>
        <Link
          to={routes.gmHome}
          className="inline-flex rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200"
        >
          {t("shop.goCampaigns")}
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <header>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
          {t("shop.title")}
        </p>
        <h1 className="mt-2 text-2xl font-semibold">{t("shop.subtitle")}</h1>
        <p className="mt-3 text-sm text-slate-400">
          {t("shop.description")}
        </p>
        <div className="mt-4">
          <Link
            to={routes.gmDashboard.replace(":campaignId", selectedCampaignId)}
            className="inline-flex rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-800"
          >
            ← Back to GM dashboard
          </Link>
        </div>
        <Link
          to={routes.catalog}
          className="mt-4 inline-flex rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200"
        >
          {t("shop.goCatalog")}
        </Link>
      </header>
      {itemsLoading ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
          {t("shop.loading")}
        </div>
      ) : (
        <>
          {itemsError ? (
            <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
              {t("shop.loadErrorDescription")}
            </div>
          ) : (
            <ShopItemList items={items} />
          )}
        </>
      )}
    </section>
  );
};
