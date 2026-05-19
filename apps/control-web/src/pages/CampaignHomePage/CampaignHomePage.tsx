import { useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import {
  getCampaignSystemLabel,
  type CampaignSystemType,
} from "../../entities/campaign";
import { useLocale } from "../../shared/hooks/useLocale";
import { useAuth } from "../../features/auth";
import { campaignsRepo } from "../../shared/api/campaignsRepo";
import { CampaignQuickLinkCard } from "./CampaignQuickLinkCard";
import { CampaignHero } from "./CampaignHero";

export const CampaignHomePage = () => {
  const { campaignId } = useParams<{ campaignId: string }>();
  const {
    selectedCampaign,
    selectedCampaignId,
    selectCampaign,
    refreshCampaigns,
    clearSelectedCampaign,
  } = useCampaigns();
  const navigate = useNavigate();
  const { t } = useLocale();
  const { user } = useAuth();
  const role = user?.role ?? "PLAYER";
  const [gmName, setGmName] = useState<string | null>(null);
  const [overviewSystem, setOverviewSystem] = useState<CampaignSystemType | null>(null);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [deletingCampaign, setDeletingCampaign] = useState(false);
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
      setOverviewSystem(null);
      setOverviewError(null);
      return;
    }
    setOverviewError(null);
    campaignsRepo
      .overview(effectiveCampaignId)
      .then((data) => {
        setGmName(data.gmName ?? null);
        setOverviewSystem(data.systemType);
        setOverviewError(null);
      })
      .catch((error: { message?: string }) => {
        setGmName(null);
        setOverviewSystem(null);
        setOverviewError(error?.message ?? "Failed to load campaign");
      });
  }, [effectiveCampaignId]);

  const campaignName = selectedCampaign?.name ?? null;
  const campaignSystem = selectedCampaign?.systemType ?? overviewSystem ?? null;

  const handleDeleteCampaign = async () => {
    if (!effectiveCampaignId || deletingCampaign) {
      return;
    }

    const label = campaignName ?? "this campaign";
    const confirmed = confirm(
      `Delete "${label}" permanently?\n\nThis removes the campaign, parties, sessions, sheets, inventory, NPCs, and campaign snapshots.`
    );
    if (!confirmed) {
      return;
    }

    setDeletingCampaign(true);
    try {
      await campaignsRepo.remove(effectiveCampaignId);
      try {
        await refreshCampaigns();
      } catch {
        // ignore refresh failures after a successful delete
      }
      clearSelectedCampaign();
      navigate(routes.gmHome);
    } catch (error: any) {
      alert(error?.message ?? "Failed to delete campaign");
      setDeletingCampaign(false);
    }
  };

  return (
    <section className="space-y-6">
      <CampaignHero
        campaignName={campaignName}
        campaignSystem={campaignSystem}
        gmName={gmName}
        backFallbackTo={routes.home}
      />

      {overviewError && (
        <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {overviewError}
        </div>
      )}

      {isGm && (
        <section className="rounded-[34px] border border-limiar-300/10 bg-[linear-gradient(180deg,rgba(26,12,55,0.4),rgba(2,6,23,0.92))] p-1 shadow-[0_24px_70px_rgba(2,6,23,0.32)]">
          <section className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
            <div className="flex flex-col gap-4 border-b border-white/8 pb-5 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
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

            <div className="mt-6 grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
              {effectiveCampaignId && (
                <CampaignQuickLinkCard
                  to={routes.campaignMaps.replace(":campaignId", effectiveCampaignId)}
                  title={t("campaignHome.actionMaps")}
                  description={t("campaignHome.actionMapsDescription")}
                  accent="amber"
                />
              )}
              <CampaignQuickLinkCard
                to={routes.catalogItems}
                title={t("campaignHome.actionItems")}
                description={t("campaignHome.actionItemsDescription")}
                accent="sky"
              />
              <CampaignQuickLinkCard
                to={routes.catalogSpells}
                title={t("campaignHome.actionSpells")}
                description={t("campaignHome.actionSpellsDescription")}
                accent="violet"
              />
              <CampaignQuickLinkCard
                to={routes.bestiary}
                title={t("campaignHome.actionNpcs")}
                description={t("campaignHome.actionNpcsDescription")}
                accent="emerald"
              />
            </div>

            {effectiveCampaignId && (
              <div className="mt-6 relative overflow-hidden rounded-[28px] border border-red-500/15 bg-red-500/5 p-5">
                <div className="pointer-events-none absolute -right-16 top-0 h-40 w-40 rounded-full bg-red-500/10 blur-[80px]" />
                <div className="relative flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-red-300">
                      Danger Zone
                    </p>
                    <p className="mt-2 max-w-2xl text-sm leading-7 text-slate-300">
                      Delete the campaign and all of its parties, sessions, inventories, sheets, and current snapshot data.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleDeleteCampaign}
                    disabled={deletingCampaign}
                    className="rounded-full border border-red-500/30 bg-red-500/10 px-5 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-red-200 transition hover:border-red-400/40 hover:bg-red-500/18 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {deletingCampaign ? "Deleting..." : "Delete Campaign"}
                  </button>
                </div>
              </div>
            )}
          </section>
        </section>
      )}
    </section>
  );
};
