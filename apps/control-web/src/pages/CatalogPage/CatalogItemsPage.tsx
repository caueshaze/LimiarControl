import { useDeferredValue, useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import { CreateShopItemForm, useShop } from "../../features/shop";
import type { ItemType } from "../../entities/item";
import { useCampaignSpells } from "../../features/shop/hooks/useCampaignSpells";
import { useLocale } from "../../shared/hooks/useLocale";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";
import { CatalogHero } from "./CatalogHero";
import { CatalogItemsSection } from "./CatalogItemsSection";
import { CatalogModeSwitch, type CatalogMode } from "./CatalogModeSwitch";
import { CatalogNoCampaignState } from "./CatalogNoCampaignState";
import { resolveCatalogMessage } from "./catalogPage.utils";
import { useCatalogPageMetrics } from "./useCatalogPageMetrics";

export const CatalogItemsPage = () => {
  const {
    items,
    itemsLoading,
    itemsError,
    createItem,
    updateItem,
    deleteItem,
    itemTypes,
    selectedCampaignId,
    campaignSystemType,
  } = useShop();
  const { selectedCampaign } = useCampaigns();
  const { t, locale } = useLocale();
  const { spells: campaignSpells } = useCampaignSpells({
    campaignId: selectedCampaignId,
    auto: true,
  });
  const { toast, showToast, clearToast } = useToast();
  const location = useLocation();
  const [mode, setMode] = useState<CatalogMode>("library");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<"ALL" | ItemType>("ALL");
  const deferredSearch = useDeferredValue(search);

  useEffect(() => {
    clearToast();
  }, [location.pathname, clearToast]);

  useEffect(() => {
    setSearch("");
    setTypeFilter("ALL");
    setMode("library");
  }, [selectedCampaignId]);

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

  const { customCount, filteredItems, linkedCount, typeCounts } = useCatalogPageMetrics({
    allSpells: [],
    deferredSearch,
    deferredSpellSearch: "",
    itemTypes,
    items,
    locale,
    spellClassFilter: null,
    spellLevelFilter: null,
    spellSchoolFilter: null,
    t,
    typeFilter,
  });

  if (!selectedCampaignId) {
    return (
      <section className="space-y-6">
        <Toast toast={toast} onClose={clearToast} />
        <CatalogNoCampaignState />
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
      setMode("library");
      return true;
    }

    showToast({
      variant: "error",
      title: t("catalog.createErrorTitle"),
      description: resolveCatalogMessage(
        t,
        (result as { message?: string })?.message,
        "catalog.createErrorDescription",
      ),
    });
    return false;
  };

  const handleUpdate = async (
    itemId: string,
    payload: Parameters<typeof updateItem>[1],
  ) => {
    const result = await updateItem(itemId, payload);
    if (result?.ok) {
      showToast({
        variant: "success",
        title: t("catalog.updateSuccessTitle"),
        description: t("catalog.updateSuccessDescription"),
      });
      return true;
    }

    showToast({
      variant: "error",
      title: t("catalog.updateErrorTitle"),
      description: resolveCatalogMessage(
        t,
        (result as { message?: string })?.message,
        "catalog.updateErrorDescription",
      ),
    });
    return false;
  };

  const handleDelete = async (itemId: string) => {
    await deleteItem(itemId);
    showToast({
      variant: "info",
      title: t("catalog.deleteTitle"),
      description: t("catalog.deleteDescription"),
    });
  };

  const showEmptyFiltered = !itemsLoading && items.length > 0 && filteredItems.length === 0;

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />

      <Link
        to={routes.campaigns}
        className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/3 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-300 transition hover:border-white/16 hover:text-white"
      >
        <span aria-hidden>←</span>
        {t("campaignHome.back")}
      </Link>

      <CatalogHero
        campaignName={selectedCampaign?.name ?? t("home.activeCampaign")}
        filteredCount={filteredItems.length}
        linkedCount={linkedCount}
        systemType={campaignSystemType}
        totalCount={items.length}
        customCount={customCount}
        title={t("catalog.subtitle")}
        description={t("catalog.heroDescription")}
      />

      <CatalogModeSwitch
        mode={mode}
        createTitle={t("catalog.formHeadline")}
        libraryTitle={t("catalog.items.listPanelTitle")}
        onChange={setMode}
      />

      {mode === "create" ? (
        <section className="mx-auto w-full max-w-330 space-y-4">
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => setMode("library")}
              className="rounded-full border border-white/10 bg-white/3 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 transition hover:border-white/20 hover:bg-white/8"
            >
              {t("catalog.openLibrary")}
            </button>
          </div>
          <CreateShopItemForm onCreate={handleCreate} itemTypes={itemTypes} spells={campaignSpells} />
        </section>
      ) : (
        <section className="rounded-[34px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.84),rgba(2,6,23,0.96))] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
          <header className="border-b border-white/8 pb-5">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
                  {t("catalog.items.listPanelTitle")}
                </p>
                <p className="mt-3 text-sm leading-7 text-slate-300">
                  {t("catalog.items.listPanelDescription")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setMode("create")}
                className="rounded-full border border-white/10 bg-white/3 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 transition hover:border-white/20 hover:bg-white/8"
              >
                {t("catalog.openCreate")}
              </button>
            </div>
          </header>
          <div className="mt-6">
            <CatalogItemsSection
              filteredItemsCount={filteredItems.length}
              itemsCount={items.length}
              itemsLoading={itemsLoading}
              itemTypes={itemTypes}
              items={filteredItems}
              spells={campaignSpells}
              search={search}
              showEmptyFiltered={showEmptyFiltered}
              typeCounts={typeCounts}
              typeFilter={typeFilter}
              onClear={() => {
                setSearch("");
                setTypeFilter("ALL");
              }}
              onDelete={handleDelete}
              onSearchChange={setSearch}
              onTypeFilterChange={setTypeFilter}
              onUpdate={handleUpdate}
            />
          </div>
        </section>
      )}
    </section>
  );
};
