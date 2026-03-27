import { Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useEffect, useState } from "react";
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

type BestiaryMode = "create" | "library";

export const NpcsPage = () => {
  const { selectedCampaign } = useCampaigns();
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
    selectedCampaignId,
  } = useCampaignEntities(true);
  const { t } = useLocale();
  const { toast, showToast, clearToast } = useToast();
  const [mode, setMode] = useState<BestiaryMode>("create");

  useEffect(() => {
    if (!entitiesError) {
      return;
    }
    showToast({
      variant: "error",
      title: t("entity.loadErrorTitle"),
      description: t("entity.loadErrorDescription"),
    });
  }, [entitiesError, showToast, t]);

  if (!selectedCampaignId) {
    return (
      <section className="space-y-6">
        <section className="relative overflow-hidden rounded-[34px] border border-white/8 bg-[#070712] px-6 py-8 shadow-[0_30px_90px_rgba(0,0,0,0.28)] sm:px-8">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.16),transparent_28%),linear-gradient(180deg,rgba(15,23,42,0.88),rgba(2,6,23,0.96))]" />
          <div className="relative max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-emerald-100/80">
              {t("entity.heroEyebrow")}
            </p>
            <h1 className="mt-4 font-display text-4xl font-bold text-white">
              {t("entity.title")}
            </h1>
            <p className="mt-4 text-sm leading-7 text-slate-300">{t("entity.noCampaign")}</p>
            <Link
              to={routes.home}
              className="mt-6 inline-flex rounded-full border border-white/10 bg-white/4 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-100 transition hover:border-white/20 hover:bg-white/8"
            >
              {t("entity.goCampaigns")}
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
  const handleSaveEntity = async (payload: Parameters<typeof saveEntity>[0]) => {
    await saveEntity(payload);
    setMode("library");
  };

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />
      <NpcsHero
        campaignName={selectedCampaign?.name ?? t("home.activeCampaign")}
        totalCount={rawEntities.length}
        visibleCount={entities.length}
        backTo={campaignPanelRoute}
        eyebrow={t("entity.heroEyebrow")}
        title={t("entity.title")}
        description={t("entity.description")}
      />

      <section className="rounded-4xl border border-white/8 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_36%),linear-gradient(180deg,rgba(15,23,42,0.84),rgba(2,6,23,0.96))] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.26)]">
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-3xl border border-white/8 bg-white/4 p-5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-emerald-100/70">
              {t("entity.form.generalSection")}
            </p>
            <p className="mt-3 text-sm leading-7 text-slate-300">
              {t("entity.pageFeatureOne")}
            </p>
          </div>
          <div className="rounded-3xl border border-white/8 bg-white/4 p-5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-emerald-100/70">
              {t("entity.form.combatActions")}
            </p>
            <p className="mt-3 text-sm leading-7 text-slate-300">
              {t("entity.pageFeatureTwo")}
            </p>
          </div>
          <div className="rounded-3xl border border-white/8 bg-white/4 p-5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-emerald-100/70">
              {t("entity.form.notesSection")}
            </p>
            <p className="mt-3 text-sm leading-7 text-slate-300">
              {t("entity.pageFeatureThree")}
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-[34px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.84),rgba(2,6,23,0.96))] p-3 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
        <div className="grid gap-2 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => setMode("create")}
            className={`rounded-3xl px-5 py-5 text-left transition ${
              mode === "create"
                ? "border border-emerald-300/20 bg-emerald-400/10 text-white shadow-[0_18px_40px_rgba(16,185,129,0.08)]"
                : "border border-transparent bg-white/3 text-slate-300 hover:bg-white/6"
            }`}
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              {t("entity.switchCreate")}
            </p>
            <p className="mt-2 text-lg font-semibold text-inherit">{t("entity.form.title")}</p>
            <p className="mt-2 text-sm leading-7 text-slate-300">
              {t("entity.switchCreateDescription")}
            </p>
          </button>
          <button
            type="button"
            onClick={() => setMode("library")}
            className={`rounded-3xl px-5 py-5 text-left transition ${
              mode === "library"
                ? "border border-sky-300/20 bg-sky-400/10 text-white shadow-[0_18px_40px_rgba(56,189,248,0.08)]"
                : "border border-transparent bg-white/3 text-slate-300 hover:bg-white/6"
            }`}
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              {t("entity.switchLibrary")}
            </p>
            <p className="mt-2 text-lg font-semibold text-inherit">{t("entity.listPanelTitle")}</p>
            <p className="mt-2 text-sm leading-7 text-slate-300">
              {t("entity.switchLibraryDescription")}
            </p>
          </button>
        </div>
      </section>

      {mode === "create" ? (
        <section className="mx-auto w-full max-w-390 rounded-[36px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.88),rgba(2,6,23,0.98))] p-5 sm:p-6 lg:p-8 shadow-[0_28px_80px_rgba(2,6,23,0.3)]">
          <header className="border-b border-white/8 pb-6">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-emerald-100/75">
                  {t("entity.form.title")}
                </p>
                <p className="mt-3 max-w-4xl text-sm leading-7 text-slate-300">
                  {t("entity.formPanelDescription")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setMode("library")}
                className="rounded-full border border-white/10 bg-white/3 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 transition hover:border-white/20 hover:bg-white/8"
              >
                {t("entity.openLibrary")}
              </button>
            </div>
          </header>
          <div className="mt-8">
            <CampaignEntityForm onSave={handleSaveEntity} />
          </div>
        </section>
      ) : entitiesLoading ? (
        <section className="mx-auto w-full max-w-330 rounded-[34px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.84),rgba(2,6,23,0.96))] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
            {t("entity.listPanelTitle")}
          </p>
          <div className="mt-5 rounded-3xl border border-white/8 bg-white/3 p-4 text-sm text-slate-300">
            {t("entity.loading")}
          </div>
        </section>
      ) : (
        <section className="mx-auto w-full max-w-330 rounded-[34px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.84),rgba(2,6,23,0.96))] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
          <header className="border-b border-white/8 pb-5">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
                  {t("entity.listPanelTitle")}
                </p>
                <p className="mt-3 text-sm leading-7 text-slate-300">
                  {t("entity.listPanelDescription")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setMode("create")}
                className="rounded-full border border-white/10 bg-white/3 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 transition hover:border-white/20 hover:bg-white/8"
              >
                {t("entity.openCreate")}
              </button>
            </div>
          </header>
          <div className="mt-6">
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
    </section>
  );
};
