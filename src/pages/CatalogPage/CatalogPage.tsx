import { useDeferredValue, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import type { BaseSpellUpdatePayload } from "../../shared/api/baseSpellsRepo";
import { campaignSpellsRepo } from "../../shared/api/campaignSpellsRepo";
import { useCampaigns } from "../../features/campaign-select";
import { CreateShopItemForm, useShop } from "../../features/shop";
import { useCampaignSpells } from "../../features/shop/hooks/useCampaignSpells";
import type { ItemType } from "../../entities/item";
import { useLocale } from "../../shared/hooks/useLocale";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";
import { CatalogItemsSection } from "./CatalogItemsSection";
import { CatalogNoCampaignState } from "./CatalogNoCampaignState";
import { CatalogHero } from "./CatalogHero";
import { CatalogSpellsSection } from "./CatalogSpellsSection";
import { CatalogTabs } from "./CatalogTabs";
import {
  resolveCatalogMessage,
  type CatalogTab,
} from "./catalogPage.utils";
import { useCatalogPageMetrics } from "./useCatalogPageMetrics";

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
    campaignSystemType,
  } = useShop();
  const { selectedCampaign } = useCampaigns();
  const { t, locale } = useLocale();
  const { toast, showToast, clearToast } = useToast();
  const location = useLocation();

  // Tab state
  const [activeTab, setActiveTab] = useState<CatalogTab>("items");

  // Item filters
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<"ALL" | ItemType>("ALL");
  const deferredSearch = useDeferredValue(search);

  // Spell filters
  const [spellSearch, setSpellSearch] = useState("");
  const [spellLevelFilter, setSpellLevelFilter] = useState<number | null>(null);
  const [spellSchoolFilter, setSpellSchoolFilter] = useState<string | null>(null);
  const [spellClassFilter, setSpellClassFilter] = useState<string | null>(null);
  const deferredSpellSearch = useDeferredValue(spellSearch);

  const {
    spells: allSpells,
    loading: spellsLoading,
    error: spellsError,
    refetch: refetchSpells,
  } = useCampaignSpells({
    campaignId: selectedCampaignId,
    auto: activeTab === "spells",
  });

  useEffect(() => {
    clearToast();
  }, [location.pathname, clearToast]);

  useEffect(() => {
    setSearch("");
    setTypeFilter("ALL");
    setSpellSearch("");
    setSpellLevelFilter(null);
    setSpellSchoolFilter(null);
    setSpellClassFilter(null);
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

  useEffect(() => {
    if (!spellsError || activeTab !== "spells") {
      return;
    }
    showToast({
      variant: "error",
      title: t("catalog.spells.loadErrorTitle"),
      description: t("catalog.spells.loadErrorDescription"),
    });
  }, [activeTab, showToast, spellsError, t]);

  const { customCount, filteredItems, filteredSpells, linkedCount, typeCounts } =
    useCatalogPageMetrics({
      allSpells,
      deferredSearch,
      deferredSpellSearch,
      itemTypes,
      items,
      locale,
      spellClassFilter,
      spellLevelFilter,
      spellSchoolFilter,
      t,
      typeFilter,
    });
  const campaignPanelRoute = selectedCampaignId
    ? routes.campaignEdit.replace(":campaignId", selectedCampaignId)
    : routes.home;

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

  const handleSpellUpdate = async (
    spellId: string,
    payload: BaseSpellUpdatePayload,
  ) => {
    if (!selectedCampaignId) {
      return false;
    }

    try {
      await campaignSpellsRepo.update(selectedCampaignId, spellId, payload);
      await refetchSpells();
      showToast({
        variant: "success",
        title: t("catalog.spells.updateSuccessTitle"),
        description: t("catalog.spells.updateSuccessDescription"),
      });
      return true;
    } catch (error) {
      const message =
        error instanceof Error && error.message
          ? error.message
          : t("catalog.spells.updateErrorDescription");
      showToast({
        variant: "error",
        title: t("catalog.spells.updateErrorTitle"),
        description: message,
      });
      return false;
    }
  };

  const showEmptyFiltered = !itemsLoading && items.length > 0 && filteredItems.length === 0;

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />

      <CatalogHero
        campaignName={selectedCampaign?.name ?? t("home.activeCampaign")}
        filteredCount={activeTab === "items" ? filteredItems.length : filteredSpells.length}
        linkedCount={activeTab === "items" ? linkedCount : allSpells.length}
        systemType={campaignSystemType}
        totalCount={activeTab === "items" ? items.length : allSpells.length}
        customCount={activeTab === "items" ? customCount : 0}
        backTo={campaignPanelRoute}
      />

      <CatalogTabs activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === "items" ? (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,430px)_minmax(0,1fr)]">
          <div className="space-y-6">
            <CreateShopItemForm onCreate={handleCreate} itemTypes={itemTypes} />
          </div>

          <CatalogItemsSection
            filteredItemsCount={filteredItems.length}
            itemsCount={items.length}
            itemsLoading={itemsLoading}
            itemTypes={itemTypes}
            items={filteredItems}
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
      ) : (
        <CatalogSpellsSection
          allSpellsCount={allSpells.length}
          classFilter={spellClassFilter}
          filteredSpells={filteredSpells}
          levelFilter={spellLevelFilter}
          schoolFilter={spellSchoolFilter}
          search={spellSearch}
          spellsLoading={spellsLoading}
          onClassChange={setSpellClassFilter}
          onClear={() => {
            setSpellSearch("");
            setSpellLevelFilter(null);
            setSpellSchoolFilter(null);
            setSpellClassFilter(null);
          }}
          onLevelChange={setSpellLevelFilter}
          onSchoolChange={setSpellSchoolFilter}
          onSearchChange={setSpellSearch}
          onUpdate={handleSpellUpdate}
        />
      )}
    </section>
  );
};
