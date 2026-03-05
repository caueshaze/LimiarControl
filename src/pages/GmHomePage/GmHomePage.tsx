import { useState } from "react";
import { CampaignManagementPanel, useCampaigns } from "../../features/campaign-select";
import { useAuth } from "../../features/auth";
import { PartyManagementPanel } from "../../features/party-management";
import { useLocale } from "../../shared/hooks/useLocale";

type GmHomeSection = "campaigns" | "parties";

export const GmHomePage = () => {
  const { campaigns, selectCampaign } = useCampaigns();
  const { user } = useAuth();
  const { t } = useLocale();
  const [activeSection, setActiveSection] = useState<GmHomeSection>("campaigns");

  return (
    <section className="space-y-8">
      <header className="rounded-3xl border border-slate-800 bg-gradient-to-br from-void-950 via-slate-950/80 to-limiar-900/30 p-6">
        <p className="text-xs uppercase tracking-[0.3em] text-limiar-300">
          {t("gm.home.workspaceTitle")}
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-white">
          {t("home.gm.welcome")} {user?.displayName || user?.username || "GM"}
        </h1>
        <p className="mt-3 text-sm text-slate-300">{t("gm.home.workspaceSubtitle")}</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => setActiveSection("campaigns")}
            className={
              activeSection === "campaigns"
                ? "rounded-full bg-slate-100 px-5 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-900"
                : "rounded-full border border-slate-700 px-5 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 hover:border-slate-500"
            }
          >
            {t("gm.home.menuCampaigns")}
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("parties")}
            className={
              activeSection === "parties"
                ? "rounded-full bg-slate-100 px-5 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-900"
                : "rounded-full border border-slate-700 px-5 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 hover:border-slate-500"
            }
          >
            {t("gm.home.menuParties")}
          </button>
        </div>
      </header>

      {activeSection === "campaigns" ? (
        <CampaignManagementPanel />
      ) : (
        <PartyManagementPanel campaigns={campaigns} onSelectCampaign={selectCampaign} />
      )}
    </section>
  );
};
