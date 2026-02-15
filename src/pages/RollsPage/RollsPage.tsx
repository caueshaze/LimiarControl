import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { RollFeed, RollForm, useRollSession } from "../../features/dice-roller";
import { useSession } from "../../features/sessions";
import { routes } from "../../app/routes/routes";
import { useLocale } from "../../shared/hooks/useLocale";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";
import { useCampaigns } from "../../features/campaign-select";

export const RollsPage = () => {
  const { selectedSessionId } = useSession();
  const { selectedCampaignId } = useCampaigns();
  const { events, connectionState, lastError, roll } = useRollSession();
  const { t } = useLocale();
  const { toast, showToast, clearToast } = useToast();
  const location = useLocation();

  useEffect(() => {
    clearToast();
  }, [location.pathname, clearToast]);

  useEffect(() => {
    if (!lastError) {
      return;
    }
    showToast({
      variant: "error",
      title: t("rolls.errorTitle"),
      description: lastError.message,
    });
  }, [lastError, showToast, t]);

  if (!selectedSessionId) {
    return (
      <section className="space-y-4">
        <h1 className="text-2xl font-semibold">{t("rolls.title")}</h1>
        <p className="text-sm text-slate-400">{t("rolls.noSession")}</p>
        <Link
          to={routes.join}
          className="inline-flex rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200"
        >
          {t("rolls.goJoin")}
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />
      <header>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
          {t("rolls.title")}
        </p>
        <h1 className="mt-2 text-2xl font-semibold">{t("rolls.subtitle")}</h1>
        <p className="mt-3 text-sm text-slate-400">{t("rolls.description")}</p>
        <div className="mt-4">
          <Link
            to={
              selectedCampaignId
                ? routes.gmDashboard.replace(":campaignId", selectedCampaignId)
                : routes.gmHome
            }
            className="inline-flex rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-800"
          >
            ← Back to GM dashboard
          </Link>
        </div>
      </header>
      <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <RollForm onRoll={roll} disabled={connectionState === "offline"} />
        <RollFeed events={events} connectionState={connectionState} />
      </div>
    </section>
  );
};
