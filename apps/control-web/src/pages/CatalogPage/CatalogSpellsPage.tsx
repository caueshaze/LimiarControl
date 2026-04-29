import { useDeferredValue, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import { useCampaignSpells } from "../../features/shop/hooks/useCampaignSpells";
import { useLocale } from "../../shared/hooks/useLocale";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";
import { CatalogHero } from "./CatalogHero";
import { CatalogNoCampaignState } from "./CatalogNoCampaignState";
import { CatalogSpellsSection } from "./CatalogSpellsSection";
import { useCatalogPageMetrics } from "./useCatalogPageMetrics";

export const CatalogSpellsPage = () => {
  const { selectedCampaign, selectedCampaignId } = useCampaigns();
  const { t, locale } = useLocale();
  const { toast, showToast, clearToast } = useToast();
  const location = useLocation();
  const navigate = useNavigate();
  const [spellSearch, setSpellSearch] = useState("");
  const [spellLevelFilter, setSpellLevelFilter] = useState<number | null>(null);
  const [spellSchoolFilter, setSpellSchoolFilter] = useState<string | null>(null);
  const [spellClassFilter, setSpellClassFilter] = useState<string | null>(null);
  const deferredSpellSearch = useDeferredValue(spellSearch);

  const {
    spells: allSpells,
    loading: spellsLoading,
    error: spellsError,
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
        filteredCount={filteredSpells.length}
        linkedCount={allSpells.length}
        systemType={selectedCampaign?.systemType ?? null}
        totalCount={allSpells.length}
        customCount={0}
        title={t("catalog.spells.subtitle")}
        description={t("catalog.spells.heroDescription")}
      />

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
              onClick={() => navigate(routes.catalogSpellNew)}
              className="rounded-full border border-violet-300/20 bg-violet-400/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-violet-100 transition hover:bg-violet-400/18"
            >
              {t("catalog.spells.formHeadline")}
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
          />
        </div>
      </section>
    </section>
  );
};
