import { Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useAuth } from "../../features/auth";
import { useLocale } from "../../shared/hooks/useLocale";
import { useCampaignMember, useCampaigns } from "../../features/campaign-select";
import { useActiveSession } from "../../features/sessions";
import { useSession } from "../../features/sessions";

export const PlayerHomePage = () => {
  const { user } = useAuth();
  const { t } = useLocale();
  const { selectedCampaignId } = useCampaigns();
  const { memberRole, loading: memberLoading } = useCampaignMember(selectedCampaignId);
  const { activeSession } = useActiveSession();
  const { selectedSessionId } = useSession();
  const hasCampaignAccess = Boolean(selectedCampaignId && memberRole);
  const hasActiveJoin = Boolean(selectedSessionId);

  return (
    <section className="space-y-8">
      <header className="rounded-3xl border border-slate-800 bg-gradient-to-br from-void-950 via-slate-950/80 to-limiar-900/30 p-6">
        <p className="text-xs uppercase tracking-[0.3em] text-limiar-300">
          {t("home.player.title")}
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-white">
          {t("home.player.welcome")} {user?.displayName || user?.username || "Player"}
        </h1>
        <p className="mt-3 text-sm text-slate-300">
          {t("home.player.subtitle")}
        </p>
        <div className="mt-6 flex flex-wrap gap-3 text-xs font-semibold uppercase tracking-[0.2em]">
          {hasActiveJoin ? (
            <span className="rounded-full border border-slate-700 px-5 py-2 text-slate-400">
              {t("home.player.joinDisabled")}
            </span>
          ) : (
            <Link
              to={routes.join}
              className="rounded-full bg-limiar-500 px-5 py-2 text-white shadow-lg shadow-limiar-500/20"
            >
              {t("home.player.ctaJoin")}
            </Link>
          )}
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1fr]">
        <div className="rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-950/80 to-void-950/60 p-6">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
            {t("home.playerIntroTitle")}
          </p>
          <p className="mt-3 text-sm text-slate-300">
            {t("home.playerIntroBody")}
          </p>
          <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-300">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
              {t("home.player.cardBoardTitle")}
            </p>
            {hasCampaignAccess ? (
              <>
                <p className="mt-2">
                  {activeSession?.isActive
                    ? `${t("home.player.sessionActive")} ${activeSession.number}`
                    : t("home.player.sessionInactive")}
                </p>
                {activeSession?.isActive ? (
                  <Link
                    to={routes.board.replace(":campaignId", selectedCampaignId ?? "")}
                    className="mt-4 inline-flex rounded-full bg-slate-100 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-900"
                  >
                    {t("home.player.enterCta")}
                  </Link>
                ) : (
                  <span className="mt-4 inline-flex rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                    {t("home.player.waitCta")}
                  </span>
                )}
              </>
            ) : (
              <>
                <p className="mt-2">{t("home.player.cardBoardBody")}</p>
                <span className="mt-4 inline-flex rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  {memberLoading ? t("home.player.loadingMembership") : t("home.player.joinToEnable")}
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};
