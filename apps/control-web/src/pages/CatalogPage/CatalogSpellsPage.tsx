import { useDeferredValue, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import { useCampaignSpells } from "../../features/shop/hooks/useCampaignSpells";
import { CreateSpellCatalogForm } from "../../features/shop/components/CreateSpellCatalogForm";
import type { BaseSpellUpdatePayload } from "../../shared/api/baseSpellsRepo";
import {
  campaignSpellsRepo,
  type CampaignSpellCreatePayload,
} from "../../shared/api/campaignSpellsRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";
import { CatalogHero } from "./CatalogHero";
import { CatalogModeSwitch, type CatalogMode } from "./CatalogModeSwitch";
import { CatalogNoCampaignState } from "./CatalogNoCampaignState";
import { CatalogSpellsSection } from "./CatalogSpellsSection";
import { resolveCatalogMessage } from "./catalogPage.utils";
import { useCatalogPageMetrics } from "./useCatalogPageMetrics";

export const CatalogSpellsPage = () => {
  const { selectedCampaign, selectedCampaignId } = useCampaigns();
  const { t, locale } = useLocale();
  const { toast, showToast, clearToast } = useToast();
  const location = useLocation();
  const [mode, setMode] = useState<CatalogMode>("library");
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
    auto: true,
  });

  useEffect(() => {
    clearToast();
  }, [location.pathname, clearToast]);

  useEffect(() => {
    setSpellSearch("");
    setSpellLevelFilter(null);
    setSpellSchoolFilter(null);
    setSpellClassFilter(null);
    setMode("library");
  }, [selectedCampaignId]);

  useEffect(() => {
    if (!spellsError) {
      return;
    }
    showToast({
      variant: "error",
      title: t("catalog.spells.loadErrorTitle"),
      description: t("catalog.spells.loadErrorDescription"),
    });
  }, [showToast, spellsError, t]);

  const { filteredSpells } = useCatalogPageMetrics({
    allSpells,
    deferredSearch: "",
    deferredSpellSearch,
    itemTypes: [],
    items: [],
    locale,
    spellClassFilter,
    spellLevelFilter,
    spellSchoolFilter,
    t,
    typeFilter: "ALL",
  });

  if (!selectedCampaignId) {
    return (
      <section className="space-y-6">
        <Toast toast={toast} onClose={clearToast} />
        <CatalogNoCampaignState />
      </section>
    );
  }

  const campaignPanelRoute = routes.campaignEdit.replace(":campaignId", selectedCampaignId);

  const handleSpellUpdate = async (
    spellId: string,
    payload: BaseSpellUpdatePayload,
  ) => {
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

  const handleSpellCreate = async (payload: CampaignSpellCreatePayload) => {
    try {
      await campaignSpellsRepo.create(selectedCampaignId, payload);
      await refetchSpells();
      showToast({
        variant: "success",
        title: t("catalog.spells.createSuccessTitle"),
        description: t("catalog.spells.createSuccessDescription"),
      });
      setMode("library");
      return true;
    } catch (error) {
      showToast({
        variant: "error",
        title: t("catalog.spells.createErrorTitle"),
        description: resolveCatalogMessage(
          t,
          error instanceof Error ? error.message : undefined,
          "catalog.spells.createErrorDescription",
        ),
      });
      return false;
    }
  };

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />

      <CatalogHero
        campaignName={selectedCampaign?.name ?? t("home.activeCampaign")}
        filteredCount={filteredSpells.length}
        linkedCount={allSpells.length}
        systemType={selectedCampaign?.systemType ?? null}
        totalCount={allSpells.length}
        customCount={0}
        backTo={campaignPanelRoute}
        title={t("catalog.spells.subtitle")}
        description={t("catalog.spells.heroDescription")}
      />

      <CatalogModeSwitch
        mode={mode}
        createTitle={t("catalog.spells.formHeadline")}
        libraryTitle={t("catalog.spells.listPanelTitle")}
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
          <CreateSpellCatalogForm onCreate={handleSpellCreate} />
        </section>
      ) : (
        <section className="rounded-[34px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.84),rgba(2,6,23,0.96))] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
          <header className="border-b border-white/8 pb-5">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
                  {t("catalog.spells.listPanelTitle")}
                </p>
                <p className="mt-3 text-sm leading-7 text-slate-300">
                  {t("catalog.spells.listPanelDescription")}
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
          </div>
        </section>
      )}
    </section>
  );
};
