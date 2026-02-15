import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import { useLocale } from "../../shared/hooks/useLocale";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";
import { sessionsRepo } from "../../shared/api/sessionsRepo";
import { useSession } from "../../features/sessions";
import { useAuth } from "../../features/auth";
import { campaignsRepo } from "../../shared/api/campaignsRepo";

export const JoinPage = () => {
  const { selectCampaign, upsertCampaign } = useCampaigns();
  const { setSelectedSessionId } = useSession();
  const { user } = useAuth();
  const { t } = useLocale();
  const { toast, showToast, clearToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [joinCode, setJoinCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [successDetails, setSuccessDetails] = useState<{ campaign: string; gm?: string | null } | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const code = params.get("code");
    if (code) {
      setJoinCode(code.toUpperCase());
    }
  }, [location.search]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!joinCode.trim()) {
      return;
    }
    setSuccessMessage(null);
    setSuccessDetails(null);
    setLoading(true);
    try {
      const response = await campaignsRepo.joinByCode({
        joinCode: joinCode.trim().toUpperCase(),
      });
      const overview = await campaignsRepo.overview(response.campaignId);
      upsertCampaign(overview);
      selectCampaign(response.campaignId);
      setSelectedSessionId(null);
      setSuccessMessage(t("join.successDescription"));
      setSuccessDetails({ campaign: response.campaignName, gm: response.gmName });
      showToast({
        variant: "success",
        title: t("join.successTitle"),
        description: `${t("join.successDescription")} ${response.campaignName}`,
      });
      window.setTimeout(
        () => navigate(routes.board.replace(":campaignId", response.campaignId)),
        700
      );
    } catch (error: any) {
      if (error?.status === 404) {
        try {
          const response = await sessionsRepo.join({
            joinCode: joinCode.trim().toUpperCase(),
          });
          const overview = await campaignsRepo.overview(response.campaignId);
          upsertCampaign(overview);
          selectCampaign(response.campaignId);
          setSelectedSessionId(response.sessionId);
          setSuccessMessage(t("join.successDescription"));
          setSuccessDetails({ campaign: response.campaignName, gm: response.gmName });
          showToast({
            variant: "success",
            title: t("join.successTitle"),
            description: `${t("join.successDescription")} ${response.campaignName}`,
          });
          window.setTimeout(
            () => navigate(routes.board.replace(":campaignId", response.campaignId)),
            700
          );
        } catch (innerError: any) {
          showToast({
            variant: "error",
            title: t("join.errorTitle"),
            description: innerError?.message ?? t("join.errorDescription"),
          });
        }
      } else {
        showToast({
          variant: "error",
          title: t("join.errorTitle"),
          description: error?.message ?? t("join.errorDescription"),
        });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />
      <header>
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400 hover:text-slate-200"
        >
          ← Voltar
        </button>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
          {t("join.title")}
        </p>
        <h1 className="mt-2 text-2xl font-semibold">{t("join.subtitle")}</h1>
        <p className="mt-3 text-sm text-slate-400">{t("join.description")}</p>
      </header>
      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-4"
      >
        {user?.displayName && (
          <p className="text-xs text-slate-300">
            {t("join.signedInAs")} {user.displayName}
          </p>
        )}
        <div className="rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2 text-xs text-slate-400">
          <p className="text-slate-200">{t("join.helpTitle")}</p>
          <p className="mt-1">{t("join.helpBody")}</p>
        </div>
        {successMessage && (
          <div className="rounded-xl border border-emerald-700 bg-emerald-900/20 px-3 py-2 text-xs text-emerald-200">
            {successMessage}
            {successDetails && (
              <div className="mt-1 text-[11px] text-emerald-100">
                {successDetails.campaign}
                {successDetails.gm ? ` · ${t("join.successGm")} ${successDetails.gm}` : ""}
              </div>
            )}
          </div>
        )}
        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            {t("join.form.code")}
          </label>
          <input
            value={joinCode}
            onChange={(event) => setJoinCode(event.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
            placeholder={t("join.form.codePlaceholder")}
            autoCapitalize="characters"
            disabled={loading}
          />
        </div>
        <button
          type="submit"
          disabled={loading || !joinCode.trim()}
          className="w-full rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? t("join.form.submitting") : t("join.form.submit")}
        </button>
      </form>
    </section>
  );
};
