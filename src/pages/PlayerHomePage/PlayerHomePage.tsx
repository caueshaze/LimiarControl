import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useAuth } from "../../features/auth";
import { useLocale } from "../../shared/hooks/useLocale";
import { partiesRepo, type PartySummary, type PartyInvite, type PartyActiveSession } from "../../shared/api/partiesRepo";
import { connectCampaign } from "../../shared/realtime/wsClient";

export const PlayerHomePage = () => {
  const { user, token } = useAuth();
  const { t } = useLocale();
  const navigate = useNavigate();

  const [parties, setParties] = useState<PartySummary[]>([]);
  const [invites, setInvites] = useState<PartyInvite[]>([]);
  const [activeSessions, setActiveSessions] = useState<Record<string, PartyActiveSession>>({});
  const [loading, setLoading] = useState(true);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wsClientsRef = useRef<ReturnType<typeof connectCampaign>[]>([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [fetchedParties, fetchedInvites] = await Promise.all([
        partiesRepo.listMine(),
        partiesRepo.listInvites(),
      ]);
      const safeParties = Array.isArray(fetchedParties) ? fetchedParties : [];
      const safeInvites = Array.isArray(fetchedInvites) ? fetchedInvites : [];
      setParties(safeParties);
      setInvites(safeInvites);

      // Check active sessions for each party
      const sessionResults = await Promise.allSettled(
        safeParties.map(p =>
          partiesRepo.getPartyActiveSession(p.id)
            .then(s => ({ partyId: p.id, session: s }))
            .catch(() => null)
        )
      );
      const sessions: Record<string, PartyActiveSession> = {};
      for (const result of sessionResults) {
        if (result.status === "fulfilled" && result.value) {
          sessions[result.value.partyId] = result.value.session;
        }
      }
      setActiveSessions(sessions);
    } catch {
      setParties([]);
      setInvites([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    pollingRef.current = setInterval(loadData, 15_000);
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [loadData]);

  // Connect to each party's campaign WS for real-time session events
  useEffect(() => {
    wsClientsRef.current.forEach(c => c.close());
    wsClientsRef.current = [];
    if (!token || parties.length === 0) return;

    const SESSION_EVENTS = new Set(["session_lobby", "session_started", "session_closed"]);
    const campaignIds = [...new Set(parties.map(p => p.campaignId))];

    wsClientsRef.current = campaignIds.map(campaignId => {
      const client = connectCampaign(campaignId, token);
      client.onMessage((msg) => {
        const data = msg as { type?: string };
        if (data.type && SESSION_EVENTS.has(data.type)) {
          loadData();
        }
      });
      return client;
    });

    return () => {
      wsClientsRef.current.forEach(c => c.close());
      wsClientsRef.current = [];
    };
  }, [parties, token, loadData]);

  const handleJoin = async (partyId: string) => {
    try {
      await partiesRepo.joinInvite(partyId);
      await loadData();
    } catch (err: any) {
      alert(err?.message ?? "Failed to join party");
    }
  };

  const handleDecline = async (partyId: string) => {
    try {
      await partiesRepo.declineInvite(partyId);
      await loadData();
    } catch (err: any) {
      alert(err?.message ?? "Failed to decline invite");
    }
  };

  // Find any party with a LOBBY or ACTIVE session
  const lobbyParty = parties.find(p => activeSessions[p.id]?.status === "LOBBY");
  const activeParty = parties.find(p => activeSessions[p.id]?.status === "ACTIVE");
  const alertParty = lobbyParty ?? activeParty;
  const alertSession = alertParty ? activeSessions[alertParty.id] : null;

  return (
    <section className="space-y-8">

      {/* Session Alert Banner */}
      {alertParty && alertSession && (
        <div className="relative overflow-hidden rounded-3xl border border-limiar-500/30 bg-linear-to-br from-limiar-950/80 via-slate-950/90 to-void-950 p-6 shadow-[0_0_40px_rgba(34,197,94,0.08)]">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(34,197,94,0.06),transparent_60%)]" />
          <div className="relative flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="shrink-0">
                <span className="flex h-3 w-3 relative">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-limiar-400 opacity-60" />
                  <span className="relative inline-flex h-3 w-3 rounded-full bg-limiar-500" />
                </span>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-limiar-400">
                  {alertSession.status === "LOBBY" ? "Session Starting" : "Session Active"}
                </p>
                <p className="mt-0.5 text-base font-semibold text-white">
                  {alertSession.title} · <span className="text-slate-400 font-normal">{alertParty.name}</span>
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {alertSession.status === "LOBBY"
                    ? "Your GM is waiting for players to join."
                    : "A session is in progress. Enter the board!"}
                </p>
              </div>
            </div>
            <button
              onClick={() => navigate(routes.playerPartyDetails.replace(":partyId", alertParty.id))}
              className="shrink-0 rounded-full bg-limiar-500 px-6 py-2.5 text-sm font-bold uppercase tracking-widest text-white shadow-[0_0_16px_rgba(34,197,94,0.3)] hover:bg-limiar-400 transition-all active:scale-95"
            >
              {alertSession.status === "LOBBY" ? "Join Lobby" : "Enter Board"}
            </button>
          </div>
        </div>
      )}

      <header className="rounded-3xl border border-slate-800 bg-linear-to-br from-void-950 via-slate-950/80 to-limiar-900/30 p-6">
        <p className="text-xs uppercase tracking-[0.3em] text-limiar-300">
          {t("home.player.title")}
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-white">
          {t("home.player.welcome")} {user?.displayName || user?.username || "Player"}
        </h1>
        <p className="mt-3 text-sm text-slate-300">
          {t("home.player.subtitle")}
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1fr]">
        <div className="rounded-3xl border border-slate-800 bg-linear-to-br from-slate-950/80 to-void-950/60 p-6 space-y-6">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
            {t("home.playerIntroTitle")}
          </p>
          <p className="text-sm text-slate-300">
            {t("home.playerIntroBody")}
          </p>

          {loading ? (
            <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-400">
              Loading parties and invites...
            </div>
          ) : (
            <div className="space-y-6 mt-6">
              {/* Invites Section */}
              {invites.length > 0 && (
                <div className="rounded-2xl border border-limiar-800/50 bg-limiar-950/20 p-4">
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-limiar-400 mb-4">
                    Pending Invites ({invites.length})
                  </h3>
                  <div className="space-y-3">
                    {invites.map((invite) => (
                      <div key={invite.party.id} className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                        <div>
                          <p className="text-sm font-semibold text-white">{invite.party.name}</p>
                          <p className="text-xs text-slate-400">Campaign: {invite.campaignName}</p>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleDecline(invite.party.id)}
                            className="rounded-full border border-slate-700 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-slate-300 hover:bg-slate-800"
                          >
                            Decline
                          </button>
                          <button
                            onClick={() => handleJoin(invite.party.id)}
                            className="rounded-full bg-limiar-500 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-white hover:bg-limiar-400"
                          >
                            Join
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Joined Parties Section */}
              <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">
                  Your Parties ({parties.length})
                </h3>
                {parties.length === 0 ? (
                  <p className="text-sm text-slate-400">You haven't joined any parties yet.</p>
                ) : (
                  <div className="space-y-3">
                    {parties.map((party) => {
                      const session = activeSessions[party.id];
                      return (
                        <div key={party.id} className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                          <div className="flex items-center gap-3">
                            <p className="text-sm font-semibold text-white">{party.name}</p>
                            {session?.status === "LOBBY" && (
                              <span className="rounded-full bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-amber-400">
                                Lobby
                              </span>
                            )}
                            {session?.status === "ACTIVE" && (
                              <span className="flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-emerald-400">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                Live
                              </span>
                            )}
                          </div>
                          <Link
                            to={routes.playerPartyDetails.replace(":partyId", party.id)}
                            className="rounded-full border border-slate-700 bg-slate-900 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-slate-300 hover:bg-slate-800"
                          >
                            Party Menu
                          </Link>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};
