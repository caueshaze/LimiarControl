import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import { useLocale } from "../../shared/hooks/useLocale";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";
import { useSession } from "../../features/sessions";
import { useAuth } from "../../features/auth";
import { campaignsRepo } from "../../shared/api/campaignsRepo";
import { partiesRepo, type PartyInvite } from "../../shared/api/partiesRepo";

export const JoinPage = () => {
  const { selectCampaign, upsertCampaign } = useCampaigns();
  const { setSelectedSessionId } = useSession();
  const { user } = useAuth();
  const { t } = useLocale();
  const { toast, showToast, clearToast } = useToast();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [partyInvites, setPartyInvites] = useState<PartyInvite[]>([]);
  const [invitesLoading, setInvitesLoading] = useState(false);
  const [inviteActionId, setInviteActionId] = useState<string | null>(null);

  useEffect(() => {
    setInvitesLoading(true);
    partiesRepo
      .listInvites()
      .then((data) => {
        setPartyInvites(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        setPartyInvites([]);
      })
      .finally(() => setInvitesLoading(false));
  }, []);

  const handleAcceptInvite = async (invite: PartyInvite) => {
    setInviteActionId(invite.party.id);
    try {
      await partiesRepo.joinInvite(invite.party.id);
      setPartyInvites((current) => current.filter((item) => item.party.id !== invite.party.id));
      const overview = await campaignsRepo.overview(invite.party.campaignId);
      upsertCampaign(overview);
      selectCampaign(invite.party.campaignId);
      setSelectedSessionId(invite.activeSession?.id ?? null);
      showToast({
        variant: "success",
        title: t("join.successTitle"),
        description: `Party ${invite.party.name} accepted.`,
      });
      if (invite.activeSession?.isActive) {
        window.setTimeout(
          () => navigate(routes.board.replace(":partyId", invite.party.id)),
          500
        );
      }
    } catch (error: any) {
      showToast({
        variant: "error",
        title: t("join.errorTitle"),
        description: error?.message ?? t("join.errorDescription"),
      });
    } finally {
      setInviteActionId(null);
    }
  };

  const handleDeclineInvite = async (invite: PartyInvite) => {
    setInviteActionId(invite.party.id);
    try {
      await partiesRepo.declineInvite(invite.party.id);
      setPartyInvites((current) => current.filter((item) => item.party.id !== invite.party.id));
      showToast({
        variant: "success",
        title: t("join.declineSuccess"),
        description: `Party ${invite.party.name} was declined.`,
      });
    } catch (error: any) {
      showToast({
        variant: "error",
        title: t("join.errorTitle"),
        description: error?.message ?? t("join.errorDescription"),
      });
    } finally {
      setInviteActionId(null);
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
      <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
        {user?.displayName && (
          <p className="text-xs text-slate-300">
            {t("join.signedInAs")} {user.displayName}
          </p>
        )}
        <div className="rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2 text-xs text-slate-400">
          <p className="text-slate-200">{t("join.helpTitle")}</p>
          <p className="mt-1">{t("join.helpBody")}</p>
        </div>
      </div>

      <section className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
        <header>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
            {t("join.invitesList")}
          </p>
        </header>
        {invitesLoading && (
          <p className="text-xs text-slate-400">{t("join.loading")}</p>
        )}
        {!invitesLoading && partyInvites.length === 0 && (
          <p className="text-xs text-slate-400">{t("join.empty")}</p>
        )}
        {!invitesLoading &&
          partyInvites.map((invite) => (
            <div
              key={invite.party.id}
              className="rounded-xl border border-slate-800 bg-slate-950/70 p-3"
            >
              <p className="text-sm font-semibold text-slate-100">{invite.party.name}</p>
              <p className="mt-1 text-xs text-slate-400">{invite.campaignName}</p>
              <p className="mt-1 text-[11px] text-slate-500">
                {invite.activeSession?.isActive
                  ? `${t("join.activeSession")} #${invite.activeSession.number} ${invite.activeSession.title}`
                  : t("join.noActiveSession")}
              </p>
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  disabled={inviteActionId === invite.party.id}
                  onClick={() => handleAcceptInvite(invite)}
                  className="rounded-full bg-limiar-500 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-60"
                >
                  {t("join.accept")}
                </button>
                <button
                  type="button"
                  disabled={inviteActionId === invite.party.id}
                  onClick={() => handleDeclineInvite(invite)}
                  className="rounded-full border border-slate-700 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-300 disabled:opacity-60"
                >
                  {t("join.decline")}
                </button>
              </div>
            </div>
          ))}
      </section>
    </section>
  );
};
