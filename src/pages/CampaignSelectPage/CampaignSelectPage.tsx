import {
  CampaignList,
  CreateCampaignForm,
  useCampaigns,
} from "../../features/campaign-select";
import { useLocale } from "../../shared/hooks/useLocale";
import { Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";

export const CampaignSelectPage = () => {
  const {
    campaigns,
    selectedCampaignId,
    createCampaign,
    selectCampaign,
  } = useCampaigns();
  const { t } = useLocale();

  return (
    <section className="space-y-8">
      <header className="rounded-3xl border border-slate-800 bg-gradient-to-br from-void-950 via-slate-950/80 to-limiar-900/20 p-6">
        <p className="text-xs uppercase tracking-[0.3em] text-limiar-300">
          {t("campaign.title")}
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-white">
          {t("campaign.subtitle")}
        </h1>
        <p className="mt-3 text-sm text-slate-300">
          {t("campaign.description")}
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-6">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
                  {t("campaign.listTitle")}
                </p>
                <p className="mt-2 text-sm text-slate-300">
                  {t("campaign.listDescription")}
                </p>
              </div>
              {selectedCampaignId && (
                <Link
                  to={routes.campaignSessions.replace(":campaignId", selectedCampaignId)}
                  className="rounded-full border border-limiar-400/40 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-limiar-100 hover:border-limiar-300"
                >
                  {t("home.gm.ctaSessions")}
                </Link>
              )}
            </div>
            <div className="mt-4">
              <CampaignList
                campaigns={campaigns}
                selectedCampaignId={selectedCampaignId}
                onSelect={selectCampaign}
              />
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <CreateCampaignForm onCreate={createCampaign} />

          {selectedCampaignId && (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
                {t("campaign.quickTitle")}
              </p>
              <p className="mt-2 text-sm text-slate-300">
                {t("campaign.quickDescription")}
              </p>
              <div className="mt-4 grid gap-3">
                <Link
                  to={routes.campaignSessions.replace(":campaignId", selectedCampaignId)}
                  className="flex w-full items-center justify-center rounded-xl bg-slate-100 px-4 py-3 text-sm font-bold text-slate-900 shadow-lg shadow-slate-100/10 hover:bg-white"
                >
                  {t("home.gm.ctaSessions")}
                </Link>
                <Link
                  to={routes.campaignDetails.replace(":campaignId", selectedCampaignId)}
                  className="flex w-full items-center justify-center rounded-xl border border-slate-700 px-4 py-3 text-sm font-semibold text-slate-200 hover:border-slate-500"
                >
                  {t("campaign.ctaConfig")}
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};
