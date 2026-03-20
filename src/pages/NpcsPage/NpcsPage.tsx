import { Link, useLocation } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useEffect } from "react";
import { useNpcs, NpcGenerator, NpcList } from "../../features/npc-generator";
import {
  CampaignEntityForm,
  CampaignEntityList,
  useCampaignEntities,
} from "../../features/campaign-entities";
import { useLocale } from "../../shared/hooks/useLocale";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";
import { useCampaigns } from "../../features/campaign-select";
import { NpcsHero } from "./NpcsHero";

export const NpcsPage = () => {
  const { selectedCampaign } = useCampaigns();
  const location = useLocation();
  const activeView = location.pathname === routes.bestiary ? "bestiary" : "npcs";
  const {
    npcs,
    rawNpcs,
    query,
    setQuery,
    saveNpc,
    npcsLoading,
    npcsError,
    selectedCampaignId,
  } = useNpcs(activeView === "npcs");
  const {
    entities,
    rawEntities,
    query: entityQuery,
    setQuery: setEntityQuery,
    categoryFilter,
    setCategoryFilter,
    saveEntity,
    updateEntity,
    removeEntity,
    loading: entitiesLoading,
    error: entitiesError,
  } = useCampaignEntities(activeView === "bestiary");
  const { t } = useLocale();
  const { toast, showToast, clearToast } = useToast();

  useEffect(() => {
    if (!npcsError || activeView !== "npcs") {
      return;
    }
    showToast({
      variant: "error",
      title: t("npc.loadErrorTitle"),
      description: t("npc.loadErrorDescription"),
    });
  }, [activeView, npcsError, showToast, t]);

  useEffect(() => {
    if (!entitiesError || activeView !== "bestiary") {
      return;
    }
    showToast({
      variant: "error",
      title: t("entity.loadErrorTitle"),
      description: t("entity.loadErrorDescription"),
    });
  }, [activeView, entitiesError, showToast, t]);

  if (!selectedCampaignId) {
    return (
      <section className="space-y-6">
        <section className="relative overflow-hidden rounded-[34px] border border-white/8 bg-[#070712] px-6 py-8 shadow-[0_30px_90px_rgba(0,0,0,0.28)] sm:px-8">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.16),transparent_28%),linear-gradient(180deg,rgba(15,23,42,0.88),rgba(2,6,23,0.96))]" />
          <div className="relative max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-emerald-100/80">
              {t("npc.heroEyebrow")}
            </p>
            <h1 className="mt-4 font-display text-4xl font-bold text-white">
              {t("npc.subtitle")}
            </h1>
            <p className="mt-4 text-sm leading-7 text-slate-300">{t("npc.noCampaign")}</p>
            <Link
              to={routes.home}
              className="mt-6 inline-flex rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-100 transition hover:border-white/20 hover:bg-white/[0.08]"
            >
              {t("npc.goCampaigns")}
            </Link>
          </div>
        </section>
      </section>
    );
  }

  const campaignPanelRoute = routes.campaignEdit.replace(
    ":campaignId",
    selectedCampaignId,
  );
  const heroTitle =
    activeView === "bestiary" ? t("entity.title") : t("npc.workspaceTitle");
  const heroDescription =
    activeView === "bestiary" ? t("entity.description") : t("npc.workspaceDescription");
  const heroTotalCount = activeView === "bestiary" ? rawEntities.length : rawNpcs.length;
  const heroVisibleCount = activeView === "bestiary" ? entities.length : npcs.length;

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />
      <NpcsHero
        campaignName={selectedCampaign?.name ?? t("home.activeCampaign")}
        totalCount={heroTotalCount}
        visibleCount={heroVisibleCount}
        backTo={campaignPanelRoute}
        title={heroTitle}
        description={heroDescription}
      />

      <section className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-2 shadow-[0_18px_50px_rgba(2,6,23,0.22)]">
        <div className="grid gap-2 sm:grid-cols-2">
          <Link
            to={routes.npcs}
            className={`rounded-[22px] px-5 py-4 transition ${
              activeView === "npcs"
                ? "border border-limiar-300/20 bg-limiar-400/10 text-white"
                : "border border-transparent bg-white/[0.03] text-slate-300 hover:bg-white/[0.06]"
            }`}
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              {t("npc.tabNpcs")}
            </p>
            <p className="mt-2 text-base font-semibold text-inherit">{t("npc.generatorTitle")}</p>
            <p className="mt-2 text-sm leading-7 text-slate-300">
              {t("npc.tabNpcsDescription")}
            </p>
          </Link>
          <Link
            to={routes.bestiary}
            className={`rounded-[22px] px-5 py-4 transition ${
              activeView === "bestiary"
                ? "border border-emerald-300/20 bg-emerald-400/10 text-white"
                : "border border-transparent bg-white/[0.03] text-slate-300 hover:bg-white/[0.06]"
            }`}
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              {t("npc.tabBestiary")}
            </p>
            <p className="mt-2 text-base font-semibold text-inherit">{t("entity.title")}</p>
            <p className="mt-2 text-sm leading-7 text-slate-300">
              {t("npc.tabBestiaryDescription")}
            </p>
          </Link>
        </div>
      </section>

      {activeView === "npcs" ? (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
          <NpcGenerator onSave={saveNpc} />
          {npcsLoading ? (
            <section className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
              <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
                {t("npc.listTitle")}
              </p>
              <div className="mt-5 rounded-[24px] border border-white/8 bg-white/[0.03] p-4 text-sm text-slate-300">
                {t("npc.loading")}
              </div>
            </section>
          ) : (
            <section className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
              <header className="border-b border-white/8 pb-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
                  {t("npc.listTitle")}
                </p>
                <p className="mt-3 text-sm leading-7 text-slate-300">
                  {t("npc.listDescription")}
                </p>
              </header>
              <div className="mt-5">
                <NpcList npcs={npcs} query={query} onQueryChange={setQuery} />
              </div>
            </section>
          )}
        </div>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
          <section className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
            <header className="border-b border-white/8 pb-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
                {t("entity.form.title")}
              </p>
              <p className="mt-3 text-sm leading-7 text-slate-300">
                {t("npc.bestiaryFormDescription")}
              </p>
            </header>
            <div className="mt-5">
              <CampaignEntityForm onSave={saveEntity} />
            </div>
          </section>

          {entitiesLoading ? (
            <section className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
              <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
                {t("npc.bestiaryListTitle")}
              </p>
              <div className="mt-5 rounded-[24px] border border-white/8 bg-white/[0.03] p-4 text-sm text-slate-300">
                {t("entity.loading")}
              </div>
            </section>
          ) : (
            <section className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
              <header className="border-b border-white/8 pb-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
                  {t("npc.bestiaryListTitle")}
                </p>
                <p className="mt-3 text-sm leading-7 text-slate-300">
                  {t("npc.bestiaryListDescription")}
                </p>
              </header>
              <div className="mt-5">
                <CampaignEntityList
                  entities={entities}
                  query={entityQuery}
                  onQueryChange={setEntityQuery}
                  categoryFilter={categoryFilter}
                  onCategoryChange={setCategoryFilter}
                  onUpdate={updateEntity}
                  onRemove={removeEntity}
                />
              </div>
            </section>
          )}
        </div>
      )}
    </section>
  );
};
