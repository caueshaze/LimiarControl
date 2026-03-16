import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { partiesRepo, type PartyDetail, type PartyActiveSession } from "../../shared/api/partiesRepo";
import { usersRepo, type UserSearchResult } from "../../shared/api/usersRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import { StartSessionModal } from "../../features/sessions/components/StartSessionModal";
import { sessionsRepo, type ActivityEvent, type LobbyStatus } from "../../shared/api/sessionsRepo";
import { useCampaignEvents } from "../../features/sessions";

function formatOffset(seconds: number): string {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h${String(m).padStart(2, "0")}m`;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function SessionActivityLog({ sessionId }: { sessionId: string }) {
    const { t } = useLocale();
    const [events, setEvents] = useState<ActivityEvent[] | null>(null);

    useEffect(() => {
        sessionsRepo.getActivity(sessionId).then(setEvents).catch(() => setEvents([]));
    }, [sessionId]);

    if (events === null) return <p className="text-xs text-slate-500 py-2">Loading activity...</p>;
    if (events.length === 0) return <p className="text-xs text-slate-500 py-2">No activity recorded.</p>;

    return (
        <div className="mt-3 space-y-1.5">
            {events.map((ev, i) => {
                const actor = ev.displayName ?? ev.username ?? "Unknown";
                if (ev.type === "roll") {
                    return (
                        <div key={i} className="flex items-start gap-2 rounded-lg bg-slate-900/60 px-3 py-2">
                            <span className="text-sm">🎲</span>
                            <p className="flex-1 text-xs text-white">
                                <span className="font-semibold">{actor}</span>
                                {" rolled "}
                                <span className="font-mono text-limiar-300">{ev.expression}</span>
                                {" → "}
                                <span className="font-bold text-limiar-400">{ev.total}</span>
                                {ev.results.length > 1 && <span className="text-slate-500 ml-1">({ev.results.join(", ")})</span>}
                            </p>
                            {ev.label && <p className="mt-0.5 text-[11px] text-slate-400">{t("sessionActivity.reason")} {ev.label}</p>}
                            <span className="text-[10px] font-mono text-slate-600 shrink-0">{formatOffset(ev.sessionOffsetSeconds)}</span>
                        </div>
                    );
                }
                if (ev.type === "shop") {
                    return (
                        <div key={i} className="flex items-start gap-2 rounded-lg bg-slate-900/60 px-3 py-2">
                            <span className="text-sm">{ev.action === "opened" ? "🏪" : "🔒"}</span>
                            <p className="flex-1 text-xs text-white">
                                <span className="font-semibold">{actor}</span>
                                {ev.action === "opened" ? " opened the shop" : " closed the shop"}
                            </p>
                            <span className="text-[10px] font-mono text-slate-600 shrink-0">{formatOffset(ev.sessionOffsetSeconds)}</span>
                        </div>
                    );
                }
                return (
                    <div key={i} className="flex items-start gap-2 rounded-lg bg-slate-900/60 px-3 py-2">
                        <span className="text-sm">🛒</span>
                        <p className="flex-1 text-xs text-white">
                            <span className="font-semibold">{actor}</span>
                            {" bought "}
                            <span className="font-semibold text-amber-300">{ev.itemName}</span>
                            {ev.quantity > 1 && <span className="text-slate-400"> ×{ev.quantity}</span>}
                        </p>
                        <span className="text-[10px] font-mono text-slate-600 shrink-0">{formatOffset(ev.sessionOffsetSeconds)}</span>
                    </div>
                );
            })}
        </div>
    );
}

export const PartyDetailsPage = () => {
    const { partyId } = useParams<{ partyId: string }>();
    const navigate = useNavigate();
    const { t } = useLocale();

    const [party, setParty] = useState<PartyDetail | null>(null);
    const [sessions, setSessions] = useState<PartyActiveSession[]>([]);
    const [activeSession, setActiveSession] = useState<PartyActiveSession | null>(null);
    const [loading, setLoading] = useState(true);

    // Invite state
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState<UserSearchResult[]>([]);
    const [searching, setSearching] = useState(false);

    // Session modal
    const [showStartModal, setShowStartModal] = useState(false);
    const [starting, setStarting] = useState(false);
    const [expandedSessionId, setExpandedSessionId] = useState<string | null>(null);
    const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const [lobbyStatus, setLobbyStatus] = useState<LobbyStatus | null>(null);
    const [forceStarting, setForceStarting] = useState(false);
    const [missingSheetsPlayers, setMissingSheetsPlayers] = useState<{ userId: string; displayName: string }[]>([]);
    const partyCampaignId = party?.campaignId ?? null;

    const loadData = useCallback(async (showSpinner = false) => {
        if (!partyId) return;
        if (showSpinner) {
            setLoading(true);
        }
        try {
            const [partyData, sessionsData] = await Promise.all([
                partiesRepo.get(partyId),
                partiesRepo.listPartySessions(partyId),
            ]);
            setParty(partyData);
            setSessions(sessionsData);
            setActiveSession(sessionsData.find((s) => s.isActive) ?? null);
        } catch {
            // ignore
        } finally {
            if (showSpinner) {
                setLoading(false);
            }
        }
    }, [partyId]);

    const refreshLobbyStatus = useCallback(async (sessionId: string) => {
        try {
            const status = await sessionsRepo.getLobbyStatus(sessionId);
            setLobbyStatus(status);
        } catch {
            // ignore
        }
    }, []);

    useEffect(() => {
        void loadData(true);
        pollingRef.current = setInterval(() => {
            void loadData();
        }, 15_000);
        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
        };
    }, [loadData]);

    // Listen to campaign WS for real-time session events
    const { lastEvent, onlineUsers } = useCampaignEvents(partyCampaignId);

    useEffect(() => {
        if (!lastEvent || !partyCampaignId) return;
        if (lastEvent.type === "session_started") {
            if (lastEvent.payload.partyId && partyId && lastEvent.payload.partyId !== partyId) {
                return;
            }
            // Redirect GM to the dashboard when lobby transitions to active
            navigate(routes.campaignDashboard.replace(":campaignId", partyCampaignId));
            return;
        }
        if (lastEvent.type === "session_closed") {
            setLobbyStatus(null);
            void loadData();
            return;
        }
        if (lastEvent.type === "session_lobby") {
            if (lastEvent.payload.partyId && partyId && lastEvent.payload.partyId !== partyId) {
                return;
            }
            setLobbyStatus({
                sessionId: lastEvent.payload.sessionId,
                campaignId: lastEvent.payload.campaignId,
                partyId: lastEvent.payload.partyId,
                expected: lastEvent.payload.expectedPlayers,
                ready: lastEvent.payload.readyUserIds ?? [],
                readyCount: lastEvent.payload.readyCount ?? 0,
                totalCount: lastEvent.payload.totalCount ?? lastEvent.payload.expectedPlayers.length,
            });
            void loadData();
            return;
        }
        if (lastEvent.type === "player_joined_lobby") {
            if (lastEvent.payload.partyId && partyId && lastEvent.payload.partyId !== partyId) {
                return;
            }
            setLobbyStatus((current) => {
                if (!current || current.sessionId !== lastEvent.payload.sessionId) {
                    return current;
                }
                if (current.ready.includes(lastEvent.payload.userId)) {
                    return current;
                }
                return {
                    ...current,
                    ready: [...current.ready, lastEvent.payload.userId],
                    readyCount: lastEvent.payload.readyCount ?? current.readyCount + 1,
                };
            });
            return;
        }
        if (lastEvent.type === "party_member_updated") {
            void loadData();
        }
    }, [lastEvent, loadData, navigate, partyCampaignId, partyId]);

    useEffect(() => {
        if (!activeSession?.id || activeSession.status !== "LOBBY") {
            setLobbyStatus(null);
            return;
        }
        let cancelled = false;
        const syncLobby = async () => {
            try {
                const status = await sessionsRepo.getLobbyStatus(activeSession.id);
                if (!cancelled) {
                    setLobbyStatus(status);
                }
            } catch {
                // ignore
            }
        };
        void syncLobby();
        const interval = setInterval(syncLobby, 3000);
        return () => {
            cancelled = true;
            clearInterval(interval);
        };
    }, [activeSession?.id, activeSession?.status]);

    useEffect(() => {
        if (searchQuery.length < 2) {
            setSearchResults([]);
            return;
        }
        const delay = setTimeout(async () => {
            setSearching(true);
            try {
                const results = await usersRepo.search(searchQuery);
                setSearchResults(results);
            } catch {
                // ignore
            } finally {
                setSearching(false);
            }
        }, 400);
        return () => clearTimeout(delay);
    }, [searchQuery]);

    const handleInvite = async (userId: string) => {
        if (!partyId) return;
        try {
            await partiesRepo.addMember(partyId, { userId, role: "PLAYER", status: "invited" });
            setSearchQuery("");
            await loadData();
        } catch (err: any) {
            alert(err?.message ?? "Failed to invite user");
        }
    };

    const handleStartSession = async (title: string) => {
        if (!partyId || !party || starting) return;
        setStarting(true);
        setMissingSheetsPlayers([]);
        try {
            const createdSession = await partiesRepo.createPartySession(partyId, { title });
            setShowStartModal(false);
            setActiveSession(createdSession);
            setSessions((current) => [createdSession, ...current.filter((session) => session.id !== createdSession.id)]);
            if (createdSession.status === "LOBBY") {
                await refreshLobbyStatus(createdSession.id);
            } else {
                setLobbyStatus(null);
            }
            await loadData();
        } catch (err: any) {
            const detail = (err as { data?: { detail?: { code?: string; players?: { userId: string; displayName: string }[] } } })?.data?.detail;
            if (detail?.code === "missing_character_sheets") {
                setMissingSheetsPlayers(detail.players ?? []);
                setShowStartModal(false);
                return;
            }
            alert(err?.message ?? "Failed to start session");
        } finally {
            setStarting(false);
        }
    };

    const handleForceStart = async () => {
        if (!activeSession?.id || forceStarting) return;
        setForceStarting(true);
        setMissingSheetsPlayers([]);
        try {
            await sessionsRepo.forceStartLobby(activeSession.id);
            await loadData();
        } catch (err: any) {
            const detail = (err as { data?: { detail?: { code?: string; players?: { userId: string; displayName: string }[] } } })?.data?.detail;
            if (detail?.code === "missing_character_sheets") {
                setMissingSheetsPlayers(detail.players ?? []);
                return;
            }
            alert(err?.message ?? "Failed to start session");
        } finally {
            setForceStarting(false);
        }
    };

    const handleEndSession = async () => {
        if (!partyId || !activeSession) return;
        if (!confirm("Are you sure you want to end this session?")) return;
        try {
            await partiesRepo.closePartySession(partyId, activeSession.id);
            await loadData();
        } catch (err: any) {
            alert(err?.message ?? "Failed to end session");
        }
    };

    if (loading) {
        return (
            <section className="space-y-8 p-6">
                <p className="text-slate-400">Loading party details...</p>
            </section>
        );
    }

    if (!party) {
        return (
            <section className="space-y-8 p-6">
                <p className="text-slate-400">Party not found.</p>
                <Link to={routes.gmHome} className="text-limiar-400 hover:underline">
                    Return to GM Home
                </Link>
            </section>
        );
    }

    return (
        <>
        <section className="space-y-8">
            {missingSheetsPlayers.length > 0 && (
                <div className="rounded-3xl border border-amber-500/30 bg-amber-500/10 p-5">
                    <p className="text-sm font-semibold text-amber-300">
                        Nao e possivel iniciar a sessao. Os seguintes jogadores ainda nao possuem ficha:
                    </p>
                    <p className="mt-2 text-sm text-amber-100">
                        {missingSheetsPlayers.map((player) => player.displayName).join(", ")}
                    </p>
                </div>
            )}

            <header className="rounded-3xl border border-slate-800 bg-linear-to-br from-void-950 via-slate-950/80 to-limiar-900/30 p-6 flex flex-wrap justify-between items-start gap-4">
                <div>
                    <Link to={routes.home} className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400 hover:text-slate-200">
                        ← Home
                    </Link>
                    <p className="mt-3 text-xs uppercase tracking-[0.3em] text-limiar-300">
                        {t("gm.home.partyPanelTitle")}
                    </p>
                    <h1 className="mt-2 text-3xl font-semibold text-white">{party.name}</h1>
                    <p className="mt-3 text-sm text-slate-300">
                        Manage your group, invite players, and view timeline.
                    </p>
                </div>
                <div className="flex gap-3">
                    {activeSession?.status === "ACTIVE" ? (
                        <>
                            <button
                                onClick={handleEndSession}
                                className="rounded-full border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-red-400 hover:bg-red-500/20"
                            >
                                End Session
                            </button>
                            <Link
                                to={routes.campaignDashboard.replace(":campaignId", party.campaignId)}
                                className="rounded-full bg-emerald-500/20 border border-emerald-500/30 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-emerald-300 hover:bg-emerald-500/30"
                            >
                                Manage Session →
                            </Link>
                        </>
                    ) : activeSession?.status === "LOBBY" ? (
                        <button
                            onClick={handleEndSession}
                            className="rounded-full border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-red-400 hover:bg-red-500/20"
                        >
                            Cancel Lobby
                        </button>
                    ) : (
                        <button
                            onClick={() => setShowStartModal(true)}
                            className="rounded-full bg-limiar-500 px-6 py-2.5 text-sm font-semibold uppercase tracking-wider text-white shadow-lg shadow-limiar-500/20 hover:bg-limiar-400 transition"
                        >
                            Start New Session
                        </button>
                    )}
                </div>
            </header>

            {activeSession?.status === "LOBBY" && (
                <div className="rounded-3xl border border-amber-500/20 bg-amber-500/5 p-5 space-y-5">
                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                        <div>
                            <p className="text-xs uppercase tracking-widest text-amber-400">Lobby aberto</p>
                            <p className="mt-1 text-lg font-semibold text-white">{activeSession.title || "Untitled Session"}</p>
                            <p className="mt-1 text-sm text-slate-400">
                                Aguardando os jogadores confirmarem entrada para iniciar a sessao.
                            </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-3">
                            <span className="rounded-full bg-amber-500/10 border border-amber-500/20 px-3 py-1 text-xs font-semibold text-amber-300">
                                {lobbyStatus ? `${lobbyStatus.ready.length}/${lobbyStatus.expected.length} prontos` : "Carregando lobby"}
                            </span>
                            <button
                                onClick={handleForceStart}
                                disabled={forceStarting}
                                className="rounded-full border border-limiar-500/30 bg-limiar-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-limiar-300 hover:bg-limiar-500/20 disabled:opacity-50"
                            >
                                {forceStarting ? "Starting..." : "Force Start"}
                            </button>
                        </div>
                    </div>

                    {lobbyStatus ? (
                        lobbyStatus.expected.length > 0 ? (
                            <div className="grid gap-3 md:grid-cols-2">
                                {lobbyStatus.expected.map((player) => {
                                    const isReady = lobbyStatus.ready.includes(player.userId);
                                    const isOnline = Boolean(onlineUsers[player.userId]);
                                    return (
                                        <div
                                            key={player.userId}
                                            className={`flex items-center gap-3 rounded-2xl border px-4 py-3 ${
                                                isReady
                                                    ? "border-emerald-500/20 bg-emerald-500/10"
                                                    : "border-slate-800 bg-slate-900/40"
                                            }`}
                                        >
                                            <div className="relative">
                                                <div className={`flex h-9 w-9 items-center justify-center rounded-full border text-sm font-bold ${
                                                    isReady
                                                        ? "border-emerald-500/30 bg-emerald-500/20 text-emerald-200"
                                                        : "border-slate-700 bg-slate-800 text-slate-300"
                                                }`}>
                                                    {player.displayName.charAt(0).toUpperCase()}
                                                </div>
                                                <span className={`absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-slate-950 ${
                                                    isOnline ? "bg-emerald-400" : "bg-slate-600"
                                                }`} />
                                            </div>
                                            <div className="min-w-0">
                                                <p className={`truncate text-sm font-medium ${isReady ? "text-emerald-200" : "text-white"}`}>
                                                    {player.displayName}
                                                </p>
                                                <p className={`text-xs ${isReady ? "text-emerald-400" : isOnline ? "text-sky-400" : "text-slate-500"}`}>
                                                    {isReady ? "Entrou no lobby" : isOnline ? "Online" : "Offline"}
                                                </p>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <p className="text-sm text-slate-400">Nenhum player confirmado para este lobby.</p>
                        )
                    ) : (
                        <p className="text-sm text-slate-400">Carregando estado do lobby...</p>
                    )}
                </div>
            )}

            {activeSession?.status === "ACTIVE" && (
                <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 flex items-center justify-between">
                    <div>
                        <p className="text-xs uppercase tracking-widest text-emerald-400">Active Session</p>
                        <p className="mt-1 text-sm font-semibold text-white">{activeSession.title || "Untitled Session"}</p>
                    </div>
                    <span className="rounded-full bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-400">
                        LIVE
                    </span>
                </div>
            )}

            <div className="grid gap-6 lg:grid-cols-2">
                <div className="space-y-6">
                    <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6">
                        <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
                            Members & Invites
                        </h2>
                        <div className="mt-6 space-y-3">
                            {party.members.length === 0 ? (
                                <p className="text-sm text-slate-500">No members or invites yet.</p>
                            ) : (
                                party.members.map((m) => (
                                    <div key={m.userId} className="flex justify-between items-center rounded-xl border border-slate-800/60 bg-slate-900/40 p-3">
                                        <div>
                                            <span className="block text-sm text-white font-medium">{m.displayName || m.username || "Unknown Player"}</span>
                                            {m.username && <span className="block text-xs text-slate-500">@{m.username}</span>}
                                        </div>
                                        <div>
                                            <span className={
                                                `text-xs font-semibold uppercase tracking-wider px-2 py-1 rounded-full ` +
                                                (m.status === "joined" ? "bg-emerald-500/10 text-emerald-400" :
                                                    m.status === "invited" ? "bg-amber-500/10 text-amber-400" :
                                                        "bg-red-500/10 text-red-400")
                                            }>
                                                {m.status}
                                            </span>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>

                        <div className="mt-8 border-t border-slate-800 pt-6">
                            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                                {t("gm.home.partyUsersLabel")}
                            </label>
                            <p className="mt-1 mb-4 text-xs text-slate-400">{t("gm.home.partyUsersHint")}</p>

                            <input
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder={t("gm.home.partyUsersPlaceholder")}
                                className="w-full rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-sm text-white focus:border-limiar-500 focus:outline-none"
                            />

                            {searchQuery.length > 0 && searchQuery.length < 2 && (
                                <p className="mt-2 text-xs text-slate-500">{t("gm.home.partySearchHint")}</p>
                            )}

                            {searching && (
                                <p className="mt-2 text-xs text-slate-500">{t("gm.home.partySearchLoading")}</p>
                            )}

                            {!searching && searchQuery.length >= 2 && searchResults.length === 0 && (
                                <p className="mt-2 text-xs text-slate-500">{t("gm.home.partySearchEmpty")}</p>
                            )}

                            <div className="mt-4 space-y-2">
                                {searchResults.map((user) => {
                                    const alreadyInParty = party.members.some(m => m.userId === user.id);
                                    return (
                                        <div key={user.id} className="flex justify-between items-center rounded-xl bg-slate-900 p-3">
                                            <div>
                                                <p className="text-sm font-semibold text-white">{user.displayName || user.username}</p>
                                                <p className="text-xs text-slate-500">@{user.username}</p>
                                            </div>
                                            <button
                                                onClick={() => handleInvite(user.id)}
                                                disabled={alreadyInParty}
                                                className="rounded-full bg-slate-800 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-white hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                                {alreadyInParty ? "Added" : t("gm.home.partyUserAdd")}
                                            </button>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="space-y-6">
                    <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6">
                        <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
                            Sessions Timeline
                        </h2>
                        <div className="mt-6 space-y-3">
                            {sessions.length === 0 ? (
                                <p className="text-sm text-slate-500">No sessions recorded. Start one above!</p>
                            ) : (
                                sessions.map((s, idx) => {
                                    const isExpanded = expandedSessionId === s.id;
                                    return (
                                        <div key={s.id} className="rounded-2xl border border-slate-800 bg-slate-950/60 overflow-hidden">
                                            <button
                                                onClick={() => setExpandedSessionId(isExpanded ? null : s.id)}
                                                className="w-full text-left px-4 py-3 flex items-center justify-between gap-3 hover:bg-slate-900/40 transition-colors"
                                            >
                                                <div>
                                                    <p className="text-xs uppercase tracking-wider text-slate-500">
                                                        Session {idx + 1} &bull; {new Date(s.createdAt).toLocaleDateString()}
                                                    </p>
                                                    <p className="text-sm font-semibold text-white mt-0.5">{s.title}</p>
                                                </div>
                                                <div className="flex items-center gap-2 shrink-0">
                                                    <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-sm ${s.isActive ? 'bg-limiar-500/20 text-limiar-300' : 'bg-slate-800 text-slate-400'}`}>
                                                        {s.status}
                                                    </span>
                                                    <span className={`text-slate-500 text-xs transition-transform ${isExpanded ? "rotate-180" : ""}`}>▼</span>
                                                </div>
                                            </button>
                                            {isExpanded && (
                                                <div className="px-4 pb-4 border-t border-slate-800/60">
                                                    <SessionActivityLog sessionId={s.id} />
                                                </div>
                                            )}
                                        </div>
                                    );
                                })
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <StartSessionModal
            isOpen={showStartModal}
            onClose={() => setShowStartModal(false)}
            onConfirm={handleStartSession}
            loading={starting}
        />
        </>
    );
};
