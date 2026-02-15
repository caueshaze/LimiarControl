import { Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useEffect } from "react";
import { useNpcs, NpcGenerator, NpcList } from "../../features/npc-generator";
import { useLocale } from "../../shared/hooks/useLocale";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";

export const NpcsPage = () => {
  const { npcs, query, setQuery, saveNpc, npcsLoading, npcsError, selectedCampaignId } =
    useNpcs();
  const { t } = useLocale();
  const { toast, showToast, clearToast } = useToast();

  useEffect(() => {
    if (!npcsError) {
      return;
    }
    showToast({
      variant: "error",
      title: t("npc.loadErrorTitle"),
      description: t("npc.loadErrorDescription"),
    });
  }, [npcsError, showToast, t]);

  if (!selectedCampaignId) {
    return (
      <section className="space-y-4">
        <h1 className="text-2xl font-semibold">{t("npc.title")}</h1>
        <p className="text-sm text-slate-400">{t("npc.noCampaign")}</p>
        <Link
          to={routes.gmHome}
          className="inline-flex rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200"
        >
          {t("npc.goCampaigns")}
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />
      <header>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
          {t("npc.title")}
        </p>
        <h1 className="mt-2 text-2xl font-semibold">{t("npc.subtitle")}</h1>
        <p className="mt-3 text-sm text-slate-400">{t("npc.description")}</p>
        <div className="mt-4">
          <Link
            to={routes.gmDashboard.replace(":campaignId", selectedCampaignId)}
            className="inline-flex rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-800"
          >
            ← Back to GM dashboard
          </Link>
        </div>
      </header>
      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <NpcGenerator onSave={saveNpc} />
        {npcsLoading ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
            {t("npc.loading")}
          </div>
        ) : (
          <NpcList npcs={npcs} query={query} onQueryChange={setQuery} />
        )}
      </div>
    </section>
  );
};
