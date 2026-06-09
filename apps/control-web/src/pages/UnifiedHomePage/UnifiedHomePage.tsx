import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useAuth } from "../../features/auth";
import { useCampaigns, CampaignManagementPanel } from "../../features/campaign-select";
import { usePartyManagement } from "../../features/party-management/hooks/usePartyManagement";
import { useLocale } from "../../shared/hooks/useLocale";
import { useToast } from "../../shared/hooks/useToast";
import { useWorkspaceMode } from "../../shared/hooks/useWorkspaceMode";
import { campaignsRepo } from "../../shared/api/campaignsRepo";
import { partiesRepo, type PartySummary, type PartyInvite, type PartyActiveSession } from "../../shared/api/partiesRepo";
import { subscribe } from "../../shared/realtime/centrifugoClient";
import { Toast } from "../../shared/ui";
import { ActiveSessionCard } from "../PlayerHomePage/ActiveSessionCard";
import { PartyListItem } from "../PlayerHomePage/PartyListItem";
import { PendingInviteCard } from "../PlayerHomePage/PendingInviteCard";
import { PartyListCard } from "../GmHomePage/PartyListCard";
import { NewPartyForm } from "../GmHomePage/NewPartyForm";

const sameStringArray = (a: string[], b: string[]) =>
  a.length === b.length && a.every((v, i) => v === b[i]);

export const UnifiedHomePage = () => {
  const { user } = useAuth();
  const { t } = useLocale();
  const { toast, clearToast } = useToast();
  const navigate = useNavigate();

  // ── GM side ──────────────────────────────────────────────────────────────
  const { campaigns: allCampaigns, selectCampaign } = useCampaigns();
  // Only show campaigns where the current user is actually the GM
  const campaigns = allCampaigns.filter((c) => c.roleMode === "GM");
  const {
    parties: gmParties,
    partyName,
    setPartyName,
    campaignId: newPartyCampaignId,
    setCampaignId: setNewPartyCampaignId,
    createParty,
    saving,
    error: partyError,
  } = usePartyManagement(campaigns);

  const handleOpenParty = (party: PartySummary) => {
    if (party.campaignId) selectCampaign(party.campaignId);
    navigate(routes.partyDetails.replace(":partyId", party.id));
  };

  const handleCreateParty = async () => {
    const result = await createParty();
    if (result.ok && result.party?.id) {
      if (result.party.campaignId) selectCampaign(result.party.campaignId);
      navigate(routes.partyDetails.replace(":partyId", result.party.id));
    }
  };

  // ── Player side ───────────────────────────────────────────────────────────
  const [playerParties, setPlayerParties] = useState<PartySummary[]>([]);
  const [invites, setInvites] = useState<PartyInvite[]>([]);
  const [activeSessions, setActiveSessions] = useState<Record<string, PartyActiveSession>>({});
  const [campaignNames, setCampaignNames] = useState<Record<string, string>>({});
  const [campaignIds, setCampaignIds] = useState<string[]>([]);
  const [playerLoading, setPlayerLoading] = useState(true);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const activeSessionsPollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const subscriptionCleanupsRef = useRef<Array<() => void>>([]);
  const partiesRef = useRef<PartySummary[]>([]);

  const refreshActiveSessions = useCallback(async (targetParties?: PartySummary[]) => {
    const source = targetParties ?? partiesRef.current;
    if (source.length === 0) { setActiveSessions({}); return; }
    const results = await Promise.allSettled(
      source.map((p) =>
        partiesRepo.findPartyActiveSession(p.id)
          .then((s) => ({ partyId: p.id, session: s }))
          .catch(() => null),
      ),
    );
    const sessions: Record<string, PartyActiveSession> = {};
    for (const r of results) {
      if (r.status === "fulfilled" && r.value?.session) {
        sessions[r.value.partyId] = r.value.session;
      }
    }
    setActiveSessions(sessions);
  }, []);

  const loadPlayerData = useCallback(async (showSpinner = false) => {
    if (showSpinner) setPlayerLoading(true);
    try {
      const [fetchedCampaigns, fetchedParties, fetchedInvites] = await Promise.all([
        campaignsRepo.list(),
        partiesRepo.listMine(),
        partiesRepo.listInvites(),
      ]);
      // Only show parties where the user is a player member, not the GM
      const safeParties = Array.isArray(fetchedParties)
        ? fetchedParties.filter((p) => p.gmUserId !== user?.userId)
        : [];
      const safeInvites = Array.isArray(fetchedInvites) ? fetchedInvites : [];
      const safeNames = Array.isArray(fetchedCampaigns)
        ? Object.fromEntries(fetchedCampaigns.map((c) => [c.id, c.name]))
        : {};
      const safeCampaignIds = Array.isArray(fetchedCampaigns)
        ? [...new Set(fetchedCampaigns.map((c) => c.id))].sort()
        : [];
      setCampaignNames(safeNames);
      setPlayerParties(safeParties);
      setInvites(safeInvites);
      // Only update campaignIds if values actually changed — prevents subscription loop
      setCampaignIds((prev) => sameStringArray(prev, safeCampaignIds) ? prev : safeCampaignIds);
      partiesRef.current = safeParties;
      await refreshActiveSessions(safeParties);
    } catch {
      setPlayerParties([]);
      setInvites([]);
    } finally {
      setPlayerLoading(false);
    }
  }, [refreshActiveSessions]);

  useEffect(() => {
    void loadPlayerData(true);
    pollingRef.current = setInterval(() => void loadPlayerData(), 30_000);
    activeSessionsPollingRef.current = setInterval(() => void refreshActiveSessions(), 60_000);
    const focusHandler = () => void loadPlayerData();
    window.addEventListener("focus", focusHandler);
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
      if (activeSessionsPollingRef.current) clearInterval(activeSessionsPollingRef.current);
      window.removeEventListener("focus", focusHandler);
    };
  }, [loadPlayerData, refreshActiveSessions]);

  useEffect(() => {
    const cleanups = subscriptionCleanupsRef.current;
    cleanups.forEach((fn) => fn());
    subscriptionCleanupsRef.current = [];
    for (const campaignId of campaignIds) {
      const cleanup = subscribe(`campaign:${campaignId}`, {
        onPublication: (msg) => {
          const data = msg as { type?: string };
          if (
            data.type === "session_lobby" ||
            data.type === "session_started" ||
            data.type === "session_closed"
          ) {
            void loadPlayerData();
          }
        },
      });
      subscriptionCleanupsRef.current.push(cleanup);
    }
    return () => {
      subscriptionCleanupsRef.current.forEach((fn) => fn());
    };
  }, [campaignIds, loadPlayerData]);

  // First active session for the alert
  const firstActiveEntry = Object.entries(activeSessions)[0] ?? null;
  const firstActiveParty = firstActiveEntry
    ? playerParties.find((p) => p.id === firstActiveEntry[0]) ?? null
    : null;
  const firstActiveSession = firstActiveEntry?.[1] ?? null;

  const handleJoin = async (partyId: string) => {
    try {
      await partiesRepo.joinInvite(partyId);
      await loadPlayerData();
      await refreshActiveSessions();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Falha ao aceitar convite";
      alert(msg);
    }
  };

  const handleDecline = async (partyId: string) => {
    try {
      await partiesRepo.declineInvite(partyId);
      await loadPlayerData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Falha ao recusar convite";
      alert(msg);
    }
  };

  const displayName = user?.displayName || user?.username || "Aventureiro";
  const { mode: focusMode } = useWorkspaceMode();

  const timeOfDay = (() => {
    const h = new Date().getHours();
    if (h >= 6 && h < 12) return "morning" as const;
    if (h >= 12 && h < 18) return "afternoon" as const;
    return "night" as const;
  })();

  const timeConfig = {
    morning: {
      greeting: "Bom dia",
      orbLeft: "bg-amber-400/18",
      orbRight: "bg-yellow-300/12",
      gradient: "radial-gradient(circle_at_top_left,rgba(251,191,36,0.18),transparent_28%),radial-gradient(circle_at_80%_10%,rgba(252,211,77,0.1),transparent_22%),linear-gradient(180deg,rgba(28,18,5,0.88),rgba(2,6,23,0.96))",
      nameColor: "from-amber-200 via-yellow-100 to-white",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" className="h-8 w-8 text-amber-300" stroke="currentColor" strokeWidth={1.5}>
          <circle cx="12" cy="12" r="4" />
          <path strokeLinecap="round" d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M2 12h2M20 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
        </svg>
      ),
    },
    afternoon: {
      greeting: "Boa tarde",
      orbLeft: "bg-orange-400/16",
      orbRight: "bg-amber-300/12",
      gradient: "radial-gradient(circle_at_top_left,rgba(251,146,60,0.18),transparent_28%),radial-gradient(circle_at_80%_10%,rgba(251,191,36,0.12),transparent_22%),linear-gradient(180deg,rgba(25,12,3,0.88),rgba(2,6,23,0.96))",
      nameColor: "from-orange-200 via-amber-100 to-white",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" className="h-8 w-8 text-orange-300" stroke="currentColor" strokeWidth={1.5}>
          <circle cx="12" cy="12" r="4" />
          <path strokeLinecap="round" d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M2 12h2M20 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
        </svg>
      ),
    },
    night: {
      greeting: "Boa noite",
      orbLeft: "bg-indigo-500/18",
      orbRight: "bg-violet-400/12",
      gradient: "radial-gradient(circle_at_top_left,rgba(99,102,241,0.2),transparent_28%),radial-gradient(circle_at_80%_10%,rgba(139,92,246,0.14),transparent_22%),linear-gradient(180deg,rgba(5,2,15,0.92),rgba(2,6,23,0.98))",
      nameColor: "from-indigo-200 via-violet-100 to-white",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" className="h-8 w-8 text-indigo-300" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 12.79A9 9 0 1111.21 3a7 7 0 109.79 9.79z" />
        </svg>
      ),
    },
  } as const;

  const [gmTab, setGmTab] = useState<"campaigns" | "parties">("campaigns");

  return (
    <>
      <Toast toast={toast} onClose={clearToast} />
      <section className="space-y-6">

        {/* Hero */}
        <div className="relative overflow-hidden rounded-[34px] border border-white/8 bg-[#070712] px-6 py-8 shadow-[0_30px_90px_rgba(0,0,0,0.28)] sm:px-8">
          <div
            className="pointer-events-none absolute inset-0"
            style={{ background: timeConfig[timeOfDay].gradient }}
          />
          <div className="pointer-events-none absolute inset-0 opacity-[0.06] bg-[linear-gradient(rgba(255,255,255,0.18)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.18)_1px,transparent_1px)] bg-size-[48px_48px]" />
          <div className={`pointer-events-none absolute -left-20 top-8 h-60 w-60 rounded-full ${timeConfig[timeOfDay].orbLeft} blur-[120px] motion-safe:animate-[landing-drift_16s_ease-in-out_infinite]`} />
          <div className={`pointer-events-none absolute right-0 top-0 h-72 w-72 rounded-full ${timeConfig[timeOfDay].orbRight} blur-[130px] motion-safe:animate-[landing-float_14s_ease-in-out_infinite]`} />
          <div className="relative">
            <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-limiar-300">
              {t("home.subtitle")}
            </p>
            <div className="mt-2 flex items-center gap-3">
              <div className="motion-safe:animate-[landing-float_6s_ease-in-out_infinite]">
                {timeConfig[timeOfDay].icon}
              </div>
              <h1 className="font-display text-3xl font-bold sm:text-4xl">
                <span className={`bg-gradient-to-r ${timeConfig[timeOfDay].nameColor} bg-clip-text text-transparent`}>
                  {timeConfig[timeOfDay].greeting},
                </span>{" "}
                <span className="text-white">{displayName}.</span>
              </h1>
            </div>
            <div className="mt-4 flex flex-wrap gap-3">
              {invites.length > 0 && (
                <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-xs text-amber-300">
                  {invites.length} convite{invites.length > 1 ? "s" : ""} pendente{invites.length > 1 ? "s" : ""}
                </span>
              )}
              {user?.isSystemAdmin && (
                <button
                  type="button"
                  onClick={() => navigate(routes.adminHome)}
                  className="rounded-full border border-limiar-400/30 bg-limiar-400/10 px-3 py-1 text-xs text-limiar-300 transition hover:bg-limiar-400/20"
                >
                  Admin
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Active session alert */}
        {firstActiveParty && firstActiveSession && (
          <ActiveSessionCard
            partyName={firstActiveParty.name}
            campaignName={campaignNames[firstActiveParty.campaignId ?? ""] ?? undefined}
            sessionTitle={firstActiveSession.title ?? ""}
            sessionNumber={firstActiveSession.number}
            sessionStatus={firstActiveSession.status as "LOBBY" | "ACTIVE"}
            onEnter={() => navigate(routes.board.replace(":partyId", firstActiveParty.id))}
          />
        )}

        {/* Main content */}
        <div>

          {/* ── Como Mestre ───────────────────────────────── */}
          <div key={`gm-${focusMode}`} className={`rounded-[34px] border border-amber-400/20 bg-[linear-gradient(180deg,rgba(26,12,55,0.4),rgba(2,6,23,0.92))] p-1 shadow-[0_24px_70px_rgba(2,6,23,0.32)] ${focusMode === "GM" ? "animate-[landing-rise_0.4s_ease-out]" : "hidden"}`}>
            <div className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6">
              <header className="mb-5 border-b border-white/8 pb-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
                  Como Mestre
                </p>
                <div className="mt-2 flex items-center justify-between gap-4">
                  <h2 className="font-display text-lg font-bold text-white">
                    {gmTab === "campaigns" ? "Campanhas" : "Mesas"}
                  </h2>
                  {/* Tab switch */}
                  <div className="relative flex h-7 items-center rounded-full border border-white/10 bg-white/4 p-0.5">
                    <span
                      aria-hidden
                      className={`absolute top-0.5 bottom-0.5 w-[calc(50%-1px)] rounded-full transition-all duration-300 ease-in-out ${
                        gmTab === "campaigns"
                          ? "left-0.5 bg-amber-400/20"
                          : "left-[calc(50%+0.5px)] bg-limiar-500/20"
                      }`}
                    />
                    <button
                      type="button"
                      onClick={() => setGmTab("campaigns")}
                      className={`relative z-10 w-24 text-[10px] font-bold uppercase tracking-[0.18em] transition-colors duration-200 ${
                        gmTab === "campaigns" ? "text-amber-200" : "text-slate-500 hover:text-slate-300"
                      }`}
                    >
                      Campanhas
                    </button>
                    <button
                      type="button"
                      onClick={() => setGmTab("parties")}
                      className={`relative z-10 w-24 text-[10px] font-bold uppercase tracking-[0.18em] transition-colors duration-200 ${
                        gmTab === "parties" ? "text-limiar-300" : "text-slate-500 hover:text-slate-300"
                      }`}
                    >
                      Mesas
                    </button>
                  </div>
                </div>
              </header>

              {gmTab === "campaigns" ? (
                <div className="animate-[landing-rise_0.35s_ease-out]">
                  <CampaignManagementPanel />
                </div>
              ) : (
                <div className="animate-[landing-rise_0.35s_ease-out] space-y-4">
                  {gmParties.length > 0 ? (
                    <div className="space-y-2">
                      {gmParties.map((party) => (
                        <PartyListCard
                          key={party.id}
                          party={party}
                          campaignName={campaigns.find((c) => c.id === party.campaignId)?.name}
                          onOpen={() => handleOpenParty(party)}
                        />
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-500">Nenhuma mesa criada ainda.</p>
                  )}
                  <div className="border-t border-white/6 pt-4">
                    <NewPartyForm
                      campaigns={campaigns}
                      partyName={partyName}
                      setPartyName={setPartyName}
                      campaignId={newPartyCampaignId}
                      setCampaignId={setNewPartyCampaignId}
                      onCreate={handleCreateParty}
                      saving={saving}
                      error={partyError}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ── Como Jogador ──────────────────────────────── */}
          <div key={`player-${focusMode}`} className={`rounded-[34px] border border-sky-400/20 bg-[linear-gradient(180deg,rgba(8,26,55,0.4),rgba(2,6,23,0.92))] p-1 shadow-[0_24px_70px_rgba(2,6,23,0.32)] ${focusMode === "PLAYER" ? "animate-[landing-rise_0.4s_ease-out]" : "hidden"}`}>
            <div className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6">
              <header className="mb-5 border-b border-white/8 pb-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
                  Como Jogador
                </p>
                <h2 className="mt-1 font-display text-lg font-bold text-white">
                  Suas Mesas
                </h2>
              </header>

              {playerLoading ? (
                <p className="text-sm text-slate-500">Carregando mesas...</p>
              ) : playerParties.length === 0 ? (
                <p className="text-sm text-slate-500">
                  Você ainda não está em nenhuma mesa. Aguarde um convite de um mestre.
                </p>
              ) : (
                <div className="space-y-2">
                  {playerParties.map((party) => {
                    const session = activeSessions[party.id] ?? null;
                    return (
                      <PartyListItem
                        key={party.id}
                        partyName={party.name}
                        campaignName={campaignNames[party.campaignId ?? ""] ?? undefined}
                        sessionStatus={session ? (session.status as "ACTIVE" | "LOBBY") : null}
                        sessionTitle={session?.title ?? undefined}
                        onClick={() => navigate(routes.playerPartyDetails.replace(":partyId", party.id))}
                      />
                    );
                  })}
                </div>
              )}

              {invites.length > 0 && (
                <div className="mt-5 border-t border-white/6 pt-5">
                  <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-amber-400/70">
                    Convites Pendentes
                  </p>
                  <div className="space-y-2">
                    {invites.map((invite) => (
                      <PendingInviteCard
                        key={invite.party.id}
                        invite={invite}
                        onJoin={() => void handleJoin(invite.party.id)}
                        onDecline={() => void handleDecline(invite.party.id)}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

        </div>
      </section>
    </>
  );
};
