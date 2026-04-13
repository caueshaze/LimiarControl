import { useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import {
  getCampaignSystemLabel,
  type CampaignMapConfig,
  type CampaignSystemType,
} from "../../entities/campaign";
import { useLocale } from "../../shared/hooks/useLocale";
import { useAuth } from "../../features/auth";
import { campaignsRepo } from "../../shared/api/campaignsRepo";
import { CampaignMapConfigCard } from "./CampaignMapConfig";
import { BackButton } from "../../shared/ui";

export const CampaignMapsPage = () => {
  const { campaignId } = useParams<{ campaignId: string }>();
  const {
    selectedCampaign,
    selectedCampaignId,
    selectCampaign,
  } = useCampaigns();
  const navigate = useNavigate();
  const { t } = useLocale();
  const { user } = useAuth();
  const role = user?.role ?? "PLAYER";
  const [gmName, setGmName] = useState<string | null>(null);
  const [overviewName, setOverviewName] = useState<string | null>(null);
  const [overviewSystem, setOverviewSystem] = useState<CampaignSystemType | null>(null);
  const [overviewMaps, setOverviewMaps] = useState<CampaignMapConfig[]>([]);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const effectiveCampaignId = campaignId ?? selectedCampaignId ?? null;
  const isGm = role === "GM";

  useEffect(() => {
    if (!effectiveCampaignId) {
      navigate(routes.gmHome, { replace: true });
      return;
    }
    if (selectedCampaignId !== effectiveCampaignId) {
      selectCampaign(effectiveCampaignId);
    }
  }, [effectiveCampaignId, navigate, selectedCampaignId, selectCampaign]);

  useEffect(() => {
    if (!effectiveCampaignId) {
      setGmName(null);
      setOverviewName(null);
      setOverviewSystem(null);
      setOverviewMaps([]);
      setOverviewError(null);
      return;
    }
    setOverviewMaps([]);
    setOverviewError(null);
    campaignsRepo
      .overview(effectiveCampaignId)
      .then((data) => {
        setGmName(data.gmName ?? null);
        setOverviewName(data.name);
        setOverviewSystem(data.systemType);
        setOverviewMaps(data.maps ?? []);
        setOverviewError(null);
      })
      .catch((error: { message?: string }) => {
        setGmName(null);
        setOverviewName(null);
        setOverviewSystem(null);
        setOverviewMaps([]);
        setOverviewError(error?.message ?? "Failed to load campaign");
      });
  }, [effectiveCampaignId]);

  const campaignName = selectedCampaign?.name ?? overviewName ?? null;
  const campaignSystemLabel = selectedCampaign
    ? getCampaignSystemLabel(selectedCampaign.systemType)
    : overviewSystem
      ? getCampaignSystemLabel(overviewSystem)
      : null;

  if (!isGm || !effectiveCampaignId) {
    return null;
  }

  return (
    <section className="space-y-6">
      <header className="rounded-3xl border border-slate-800 bg-linear-to-br from-void-950 via-slate-950/80 to-limiar-900/20 p-6">
        <p className="text-xs uppercase tracking-[0.3em] text-limiar-300">
          {t("campaignHome.mapConfigTitle")}
        </p>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold text-white">
              {t("campaignHome.mapConfigHeading")}
            </h1>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {campaignName ? (
                <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold text-white">
                  {campaignName}
                </span>
              ) : null}
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
            <BackButton
              fallbackTo={
                routes.campaignEdit.replace(":campaignId", effectiveCampaignId)
              }
              label={t("campaignHome.back")}
              className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 hover:border-slate-500"
            />
          </div>
        </div>
        <p className="mt-4 text-sm text-slate-300">
          {t("campaignHome.mapConfigDescription")}
        </p>
        {overviewError && (
          <p className="mt-2 text-xs text-rose-300">{overviewError}</p>
        )}
      </header>

      <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
        <CampaignMapConfigCard
          campaignId={effectiveCampaignId}
          initialMaps={overviewMaps}
          onSaved={setOverviewMaps}
        />
      </div>
    </section>
  );
};
