import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import { getCampaignSystemLabel, type CampaignSystemType } from "../../entities/campaign";
import { useLocale } from "../../shared/hooks/useLocale";
import { useAuth } from "../../features/auth";
import { campaignsRepo } from "../../shared/api/campaignsRepo";
import { CampaignQuickLinkCard } from "./CampaignQuickLinkCard";

export const CampaignHomePage = () => {
  const { campaignId } = useParams<{ campaignId: string }>();
  const { selectedCampaign, selectedCampaignId, selectCampaign } = useCampaigns();
  const { t } = useLocale();
  const { user } = useAuth();
  const role = user?.role ?? "PLAYER";
  const [gmName, setGmName] = useState<string | null>(null);
  const [overviewName, setOverviewName] = useState<string | null>(null);
  const [overviewSystem, setOverviewSystem] = useState<CampaignSystemType | null>(null);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const isGm = role === "GM";
  const effectiveCampaignId = campaignId ?? selectedCampaignId ?? null;

  useEffect(() => {
    if (!effectiveCampaignId) {
      return;
    }
    if (selectedCampaignId !== effectiveCampaignId) {
      selectCampaign(effectiveCampaignId);
    }
  }, [effectiveCampaignId, selectedCampaignId, selectCampaign]);

  useEffect(() => {
    if (!effectiveCampaignId) {
      setGmName(null);
      setOverviewName(null);
      setOverviewSystem(null);
      setOverviewError(null);
      return;
    }
    campaignsRepo
      .overview(effectiveCampaignId)
      .then((data) => {
        setGmName(data.gmName ?? null);
        setOverviewName(data.name);
        setOverviewSystem(data.systemType);
        setOverviewError(null);
      })
      .catch((error: { message?: string }) => {
        setGmName(null);
        setOverviewName(null);
        setOverviewSystem(null);
        setOverviewError(error?.message ?? "Failed to load campaign");
      });
  }, [effectiveCampaignId]);

  const campaignName = selectedCampaign?.name ?? overviewName ?? null;
  const campaignSystemLabel = selectedCampaign
    ? getCampaignSystemLabel(selectedCampaign.systemType)
    : overviewSystem
      ? getCampaignSystemLabel(overviewSystem)
      : null;

  return (
    <section className="space-y-6">
      <header className="rounded-3xl border border-slate-800 bg-gradient-to-br from-void-950 via-slate-950/80 to-limiar-900/20 p-6">
        <p className="text-xs uppercase tracking-[0.3em] text-limiar-300">
          {t("campaignHome.title")}
        </p>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold text-white">
              {t("campaignHome.subtitle")}
            </h1>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {campaignName ? (
                <span className="rounded-full border border-white/10 bg-white/[0.05] px-4 py-2 text-xs font-semibold text-white">
                  {campaignName}
                </span>
              ) : (
                <span className="rounded-full border border-white/10 bg-white/[0.05] px-4 py-2 text-xs font-semibold text-white">
                  {t("campaignHome.none")}
                </span>
              )}
              {campaignSystemLabel && (
                <span className="rounded-full border border-sky-300/15 bg-sky-400/10 px-4 py-2 text-xs font-semibold text-sky-100">
                  {campaignSystemLabel}
                </span>
              )}
              {gmName && (
                <span className="rounded-full border border-white/10 bg-black/20 px-4 py-2 text-xs font-semibold text-slate-300">
                  {t("campaignHome.gmLabel")} {gmName}
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              to={routes.home}
              className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 hover:border-slate-500"
            >
              {t("campaignHome.back")}
            </Link>
          </div>
        </div>
        <p className="mt-4 text-sm text-slate-300">
          {t("campaignHome.description")}
        </p>
        {overviewError && (
          <p className="mt-2 text-xs text-rose-300">{overviewError}</p>
        )}
      </header>

      {isGm && (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
          <div className="flex flex-col gap-4 border-b border-white/8 pb-5 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
                {t("campaignHome.configTitle")}
              </p>
              <h2 className="mt-3 text-2xl font-semibold text-white">
                {t("campaignHome.quickActionsTitle")}
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
                {t("campaignHome.configDescription")}
              </p>
            </div>
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <CampaignQuickLinkCard
              to={routes.catalog}
              title={t("campaignHome.actionItems")}
              description={t("campaignHome.actionItemsDescription")}
              accent="sky"
            />
            <CampaignQuickLinkCard
              to={routes.bestiary}
              title={t("campaignHome.actionNpcs")}
              description={t("campaignHome.actionNpcsDescription")}
              accent="emerald"
            />
          </div>
        </div>
      )}
    </section>
  );
};
