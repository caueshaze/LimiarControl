import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useAuth } from "../../features/auth";
import { useLocale } from "../../shared/hooks/useLocale";
import { campaignsRepo } from "../../shared/api/campaignsRepo";
import { partiesRepo, type PartySummary, type PartyInvite, type PartyActiveSession } from "../../shared/api/partiesRepo";
import { subscribe } from "../../shared/realtime/centrifugoClient";
import { ActiveSessionCard } from "./ActiveSessionCard";
import { PartyListItem } from "./PartyListItem";
import { EmptyPartyState } from "./EmptyPartyState";
import { PendingInviteCard } from "./PendingInviteCard";
import { PlayerWorkspaceHero } from "./PlayerWorkspaceHero";

const sameStringArray = (left: string[], right: string[]) =>
  left.length === right.length && left.every((value, index) => value === right[index]);

export const PlayerHomePage = () => {
  const { user } = useAuth();
  const { t } = useLocale();
  const navigate = useNavigate();

  const [parties, setParties] = useState<PartySummary[]>([]);
  const [invites, setInvites] = useState<PartyInvite[]>([]);
  const [activeSessions, setActiveSessions] = useState<Record<string, PartyActiveSession>>({});
  const [campaignNames, setCampaignNames] = useState<Record<string, string>>({});
  const [campaignIds, setCampaignIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const activeSessionsPollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const subscriptionCleanupsRef = useRef<Array<() => void>>([]);
  const partiesRef = useRef<PartySummary[]>([]);

  const refreshActiveSessions = useCallback(async (targetParties?: PartySummary[]) => {
    const sourceParties = targetParties ?? partiesRef.current;
    if (sourceParties.length === 0) {
      setActiveSessions({});
      return;
    }

    const sessionResults = await Promise.allSettled(
      sourceParties.map((party) =>
        partiesRepo.getPartyActiveSession(party.id)
          .then((session) => ({ partyId: party.id, session }))
          .catch(() => null),
      ),
    );

    const sessions: Record<string, PartyActiveSession> = {};
    for (const result of sessionResults) {
      if (result.status === "fulfilled" && result.value) {
        sessions[result.value.partyId] = result.value.session;
      }
    }
    setActiveSessions(sessions);
  }, []);

  const loadData = useCallback(async (showSpinner = false) => {
    if (showSpinner) setLoading(true);
    try {
      const [fetchedCampaigns, fetchedParties, fetchedInvites] = await Promise.all([
        campaignsRepo.list(),
        partiesRepo.listMine(),
        partiesRepo.listInvites(),
      ]);
      const safeParties = Array.isArray(fetchedParties) ? fetchedParties : [];
      const safeInvites = Array.isArray(fetchedInvites) ? fetchedInvites : [];
      const safeCampaignIds = Array.isArray(fetchedCampaigns)
        ? [...new Set(fetchedCampaigns.map((campaign) => campaign.id))].sort()
        : [];
      const safeCampaignNames = Array.isArray(fetchedCampaigns)
        ? Object.fromEntries(fetchedCampaigns.map((campaign) => [campaign.id, campaign.name]))
        : {};
      setCampaignIds((current) => (sameStringArray(current, safeCampaignIds) ? current : safeCampaignIds));
      setCampaignNames(safeCampaignNames);
      setParties(safeParties);
      setInvites(safeInvites);
      partiesRef.current = safeParties;
    } catch {
      setParties([]);
      setInvites([]);
      setCampaignNames({});
      setCampaignIds([]);
      partiesRef.current = [];
      setActiveSessions({});
    } finally {
      if (showSpinner) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData(true).then(() => refreshActiveSessions());
    pollingRef.current = setInterval(() => { void loadData(); }, 30_000);
    activeSessionsPollingRef.current = setInterval(() => { void refreshActiveSessions(); }, 60_000);
    const handleFocus = () => { void loadData(); void refreshActiveSessions(); };
    window.addEventListener("focus", handleFocus);
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
      if (activeSessionsPollingRef.current) clearInterval(activeSessionsPollingRef.current);
      window.removeEventListener("focus", handleFocus);
    };
  }, [loadData, refreshActiveSessions]);

  useEffect(() => {
    partiesRef.current = parties;
  }, [parties]);

  const upsertActiveSession = useCallback((partyId: string, session: PartyActiveSession | null) => {
    setActiveSessions((current) => {
      const next = { ...current };
      if (session) {
        next[partyId] = session;
      } else {
        delete next[partyId];
      }
      return next;
    });
  }, []);

  useEffect(() => {
    subscriptionCleanupsRef.current.forEach((cleanup) => cleanup());
    subscriptionCleanupsRef.current = [];
    if (campaignIds.length === 0) return;

    const REFRESH_EVENTS = new Set(["session_lobby", "session_started", "session_closed", "party_member_updated"]);

    subscriptionCleanupsRef.current = campaignIds.map((campaignId) =>
      subscribe(`campaign:${campaignId}`, {
        onPublication: (msg) => {
          const data = msg as { payload?: { partyId?: string | null }; type?: string };
          if (data.type && REFRESH_EVENTS.has(data.type)) void loadData();
          if (data.type === "session_lobby" || data.type === "session_started") {
            const matchedParty = data.payload?.partyId
              ? partiesRef.current.find((party) => party.id === data.payload?.partyId)
              : partiesRef.current.find((party) => party.campaignId === campaignId);
            if (matchedParty) {
              void partiesRepo.getPartyActiveSession(matchedParty.id)
                .then((session) => { upsertActiveSession(matchedParty.id, session); })
                .catch(() => {});
            }
          }
          if (data.type === "session_closed") {
            const matchedParty = data.payload?.partyId
              ? partiesRef.current.find((party) => party.id === data.payload?.partyId)
              : partiesRef.current.find((party) => party.campaignId === campaignId);
            if (matchedParty) upsertActiveSession(matchedParty.id, null);
          }
          if (data.type === "session_started") {
            const matchedParty = data.payload?.partyId
              ? partiesRef.current.find((party) => party.id === data.payload?.partyId)
              : partiesRef.current.find((party) => party.campaignId === campaignId);
            if (matchedParty) navigate(routes.board.replace(":partyId", matchedParty.id));
          }
        },
      }),
    );

    return () => {
      subscriptionCleanupsRef.current.forEach((cleanup) => cleanup());
      subscriptionCleanupsRef.current = [];
    };
  }, [campaignIds, loadData, navigate, upsertActiveSession]);

  const handleJoin = async (partyId: string) => {
    try {
      await partiesRepo.joinInvite(partyId);
      await loadData();
      await refreshActiveSessions();
    } catch (err: any) {
      alert(err?.message ?? "Failed to join party");
    }
  };

  const handleDecline = async (partyId: string) => {
    try {
      await partiesRepo.declineInvite(partyId);
      await loadData();
      await refreshActiveSessions();
    } catch (err: any) {
      alert(err?.message ?? "Failed to decline invite");
    }
  };

  const lobbyParty = parties.find((p) => activeSessions[p.id]?.status === "LOBBY");
  const activeParty = parties.find((p) => activeSessions[p.id]?.status === "ACTIVE");
  const alertParty = lobbyParty ?? activeParty;
  const alertSession = alertParty ? activeSessions[alertParty.id] : null;
  const liveCount = Object.values(activeSessions).filter(
    (session) => session.status === "ACTIVE" || session.status === "LOBBY",
  ).length;
  const heroStatus = alertSession?.status === "ACTIVE"
    ? "ACTIVE"
    : alertSession?.status === "LOBBY"
      ? "LOBBY"
      : "IDLE";

  return (
    <section className="space-y-6">
      <PlayerWorkspaceHero
        displayName={user?.displayName || user?.username || "Player"}
        partiesCount={parties.length}
        invitesCount={invites.length}
        liveCount={liveCount}
        status={heroStatus}
        focusPartyName={alertParty?.name ?? null}
        onOpenCurrent={
          alertParty
            ? () => navigate(routes.playerPartyDetails.replace(":partyId", alertParty.id))
            : undefined
        }
        onOpenInvites={
          invites.length > 0
            ? () =>
                document
                  .getElementById("player-home-invites")
                  ?.scrollIntoView({ behavior: "smooth", block: "start" })
            : undefined
        }
        onOpenAdmin={user?.isSystemAdmin ? () => navigate(routes.adminHome) : undefined}
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.92fr)]">
        <div className="space-y-6">
          {alertParty && alertSession ? (
            <ActiveSessionCard
              partyName={alertParty.name}
              campaignName={campaignNames[alertParty.campaignId]}
              sessionTitle={alertSession.title}
              sessionNumber={alertSession.number}
              sessionStatus={alertSession.status as "LOBBY" | "ACTIVE"}
              onEnter={() => navigate(routes.playerPartyDetails.replace(":partyId", alertParty.id))}
            />
          ) : null}

          <section className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
            <header className="border-b border-white/8 pb-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
                {t("home.player.yourParties")}
              </p>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
                {t("home.player.partiesDescription")}
              </p>
            </header>

            <div className="mt-5 space-y-3">
              {loading ? (
                <div className="rounded-[24px] border border-white/8 bg-white/3 p-4 text-sm text-slate-400">
                  {t("home.player.loadingParties")}
                </div>
              ) : parties.length === 0 ? (
                <EmptyPartyState />
              ) : (
                parties.map((party) => {
                  const session = activeSessions[party.id];
                  const sessionStatus: "ACTIVE" | "LOBBY" | null =
                    session?.status === "ACTIVE" || session?.status === "LOBBY"
                      ? session.status
                      : null;
                  return (
                    <PartyListItem
                      key={party.id}
                      partyName={party.name}
                      campaignName={campaignNames[party.campaignId]}
                      sessionTitle={session?.title}
                      sessionStatus={sessionStatus}
                      onClick={() => navigate(routes.playerPartyDetails.replace(":partyId", party.id))}
                    />
                  );
                })
              )}
            </div>
          </section>
        </div>

        <aside id="player-home-invites" className="space-y-6">
          <section className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
            <header className="border-b border-white/8 pb-5">
              <div className="flex items-center justify-between gap-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-limiar-100/80">
                  {t("home.player.pendingInvites")}
                </p>
                <span className="rounded-full border border-limiar-300/15 bg-limiar-400/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-limiar-100">
                  {invites.length}
                </span>
              </div>
              <p className="mt-3 text-sm leading-7 text-slate-300">
                {t("home.player.invitesDescription")}
              </p>
            </header>

            <div className="mt-5 space-y-3">
              {invites.length === 0 ? (
                <div className="rounded-[24px] border border-dashed border-white/10 bg-white/3 p-5 text-sm leading-7 text-slate-400">
                  {t("home.player.emptyInvitesDescription")}
                </div>
              ) : (
                invites.map((invite) => (
                  <PendingInviteCard
                    key={invite.party.id}
                    invite={invite}
                    onDecline={() => handleDecline(invite.party.id)}
                    onJoin={() => handleJoin(invite.party.id)}
                  />
                ))
              )}
            </div>
          </section>
        </aside>
      </div>
    </section>
  );
};
