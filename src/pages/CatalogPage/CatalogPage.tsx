import { useEffect } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import {
  CatalogItemList,
  CreateShopItemForm,
  useShop,
} from "../../features/shop";
import { useLocale } from "../../shared/hooks/useLocale";
import type { LocaleKey } from "../../shared/i18n";
import { Toast } from "../../shared/ui/Toast";
import { useToast } from "../../shared/hooks/useToast";

export const CatalogPage = () => {
  const {
    items,
    itemsLoading,
    itemsError,
    createItem,
    updateItem,
    deleteItem,
    itemTypes,
    selectedCampaignId,
  } = useShop();
  const { t } = useLocale();
  const { toast, showToast, clearToast } = useToast();
  const location = useLocation();

  useEffect(() => {
    clearToast();
  }, [location.pathname, clearToast]);

  useEffect(() => {
    if (!itemsError) {
      return;
    }
    showToast({
      variant: "error",
      title: t("catalog.loadErrorTitle"),
      description: t("catalog.loadErrorDescription"),
    });
  }, [itemsError, showToast, t]);

  if (!selectedCampaignId) {
    return (
      <section className="space-y-4">
        <h1 className="text-2xl font-semibold">{t("catalog.title")}</h1>
        <p className="text-sm text-slate-400">{t("catalog.noCampaign")}</p>
        <Link
          to={routes.gmHome}
          className="inline-flex rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200"
        >
          {t("catalog.goCampaigns")}
        </Link>
      </section>
    );
  }

  const handleCreate = async (payload: Parameters<typeof createItem>[0]) => {
    const result = await createItem(payload);
    if (result?.ok) {
      showToast({
        variant: "success",
        title: t("catalog.createSuccessTitle"),
        description: t("catalog.createSuccessDescription"),
      });
    } else {
      showToast({
        variant: "error",
        title: t("catalog.createErrorTitle"),
        description: (result as { message?: string })?.message
          ? t(((result as { message?: string }).message) as LocaleKey)
          : t("catalog.createErrorDescription"),
      });
    }
  };

  const handleUpdate = async (
    itemId: string,
    payload: Parameters<typeof updateItem>[1]
  ) => {
    const result = await updateItem(itemId, payload);
    if (result?.ok) {
      showToast({
        variant: "success",
        title: t("catalog.updateSuccessTitle"),
        description: t("catalog.updateSuccessDescription"),
      });
    } else {
      showToast({
        variant: "error",
        title: t("catalog.updateErrorTitle"),
        description: (result as { message?: string })?.message
          ? t(((result as { message?: string }).message) as LocaleKey)
          : t("catalog.updateErrorDescription"),
      });
    }
  };

  const handleDelete = async (itemId: string) => {
    await deleteItem(itemId);
    showToast({
      variant: "info",
      title: t("catalog.deleteTitle"),
      description: t("catalog.deleteDescription"),
    });
  };

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />
      <header>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
          {t("catalog.title")}
        </p>
        <h1 className="mt-2 text-2xl font-semibold">{t("catalog.subtitle")}</h1>
        <p className="mt-3 text-sm text-slate-400">{t("catalog.description")}</p>
        <div className="mt-4">
          <Link
            to={routes.gmDashboard.replace(":campaignId", selectedCampaignId)}
            className="inline-flex rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-800"
          >
            ← Back to GM dashboard
          </Link>
        </div>
      </header>
      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <CreateShopItemForm onCreate={handleCreate} itemTypes={itemTypes} />
        {itemsLoading ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
            {t("catalog.loading")}
          </div>
        ) : (
          <CatalogItemList
            items={items}
            itemTypes={itemTypes}
            onUpdate={handleUpdate}
            onDelete={handleDelete}
          />
        )}
      </div>
    </section>
  );
};
