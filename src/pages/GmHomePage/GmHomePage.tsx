import { useState } from "react";
import { Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { CampaignList, CreateCampaignForm, useCampaigns } from "../../features/campaign-select";
import type { CampaignSystemType } from "../../entities/campaign";
import { useAuth } from "../../features/auth";
import { useLocale } from "../../shared/hooks/useLocale";

export const GmHomePage = () => {
  const { campaigns, selectedCampaign, selectedCampaignId, selectCampaign, createCampaign } =
    useCampaigns();
  const { user } = useAuth();
  const { t } = useLocale();
  const [showCreateModal, setShowCreateModal] = useState(false);

  const handleCreateCampaign = async (
    name: string,
    systemType: CampaignSystemType
  ) => {
    const result = await createCampaign(name, systemType);
    if (result.ok) {
      setShowCreateModal(false);
    }
    return result;
  };

  return (
    <section className="space-y-8">
      <header className="rounded-3xl border border-slate-800 bg-gradient-to-br from-void-950 via-slate-950/80 to-limiar-900/30 p-6">
        <p className="text-xs uppercase tracking-[0.3em] text-limiar-300">
          {t("gm.dashboard.title")}
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-white">
          {t("home.gm.welcome")} {user?.displayName || user?.username || "GM"}
        </h1>
        <p className="mt-3 text-sm text-slate-300">
          {t("gm.dashboard.subtitle")}
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-[320px_1fr]">
        <aside className="space-y-4">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-5">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
              {t("gm.dashboard.campaignsTitle")}
            </p>
            <div className="mt-4 space-y-2">
              <CampaignList
                campaigns={campaigns}
                selectedCampaignId={selectedCampaignId}
                onSelect={selectCampaign}
              />
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowCreateModal(true)}
            className="inline-flex w-full items-center justify-center rounded-full border border-limiar-400/40 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-limiar-100 hover:border-limiar-300"
          >
            {t("campaign.createCta")}
          </button>
        </aside>

        <main className="space-y-6">
          {!selectedCampaignId && (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6 text-sm text-slate-300">
              {t("gm.dashboard.selectCampaign")}
            </div>
          )}

          {selectedCampaignId && (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
                {t("gm.dashboard.campaignContext")}
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-white">
                {selectedCampaign?.name ?? t("campaignHome.none")}
              </h2>
              <p className="mt-2 text-sm text-slate-400">
                {t("campaign.description")}
              </p>
              <div className="mt-5 flex flex-wrap items-center gap-3 text-xs font-semibold uppercase tracking-[0.2em]">
                <Link
                  to={routes.campaignSessions.replace(":campaignId", selectedCampaignId)}
                  className="rounded-full border border-limiar-400/40 px-4 py-2 text-limiar-100 hover:border-limiar-300"
                >
                  {t("home.gm.ctaSessions")}
                </Link>
              </div>
            </div>
          )}
        </main>
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-3xl border border-slate-800 bg-void-950 p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-white">
                  {t("campaign.createTitle")}
                </h2>
                <p className="mt-2 text-sm text-slate-400">
                  {t("campaign.createDescription")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="rounded-full border border-slate-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 hover:border-slate-500"
              >
                {t("common.close")}
              </button>
            </div>
            <div className="mt-4">
              <CreateCampaignForm onCreate={handleCreateCampaign} />
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
