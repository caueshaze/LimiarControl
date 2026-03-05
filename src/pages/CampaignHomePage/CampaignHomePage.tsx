import { Link, useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import { getCampaignSystemLabel, type CampaignSystemType } from "../../entities/campaign";
import { useLocale } from "../../shared/hooks/useLocale";
import { useAuth } from "../../features/auth";
import { campaignsRepo } from "../../shared/api/campaignsRepo";

export const CampaignHomePage = () => {
  const { campaignId } = useParams<{ campaignId: string }>();
  const { selectedCampaign, selectedCampaignId, selectCampaign } = useCampaigns();
  const { t } = useLocale();
  const navigate = useNavigate();
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

  return (
    <section className="space-y-6">
      <header>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
          {t("campaignHome.title")}
        </p>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold">
              {t("campaignHome.subtitle")}
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              {selectedCampaign
                ? `${selectedCampaign.name} · ${getCampaignSystemLabel(
                  selectedCampaign.systemType
                )}`
                : overviewName && overviewSystem
                  ? `${overviewName} · ${getCampaignSystemLabel(overviewSystem)}`
                  : t("campaignHome.none")}
            </p>
            {gmName && (
              <p className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-500">
                {t("campaignHome.gmLabel")} {gmName}
              </p>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 hover:border-slate-500"
            >
              Voltar
            </button>
          </div>
        </div>
        <p className="mt-4 text-sm text-slate-400">
          {t("campaignHome.description")}
        </p>
        {overviewError && (
          <p className="mt-2 text-xs text-rose-300">{overviewError}</p>
        )}
      </header>

      {isGm && (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
            {t("campaignHome.configTitle")}
          </p>
          <p className="mt-3 text-sm text-slate-400">
            {t("campaignHome.configDescription")}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Link
              to={routes.catalog}
              className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-sm font-semibold text-slate-100 transition-colors hover:border-slate-500"
            >
              {t("campaignHome.actionItems")}
            </Link>
            <Link
              to={routes.npcs}
              className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-sm font-semibold text-slate-100 transition-colors hover:border-slate-500"
            >
              {t("campaignHome.actionNpcs")}
            </Link>
          </div>
        </div>
      )}

    </section>
  );
};
