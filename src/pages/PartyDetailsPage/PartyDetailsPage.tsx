import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { partiesRepo, type PartyDetail, type PartyActiveSession } from "../../shared/api/partiesRepo";
import { usersRepo, type UserSearchResult } from "../../shared/api/usersRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import { StartSessionModal } from "../../features/sessions/components/StartSessionModal";
import { sessionsRepo, type ActivityEvent } from "../../shared/api/sessionsRepo";
import { useCampaignEvents } from "../../features/sessions";

function formatOffset(seconds: number): string {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h${String(m).padStart(2, "0")}m`;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function SessionActivityLog({ sessionId }: { sessionId: string }) {
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
                                {ev.label && <span className="text-slate-400 ml-1">— {ev.label}</span>}
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

    const loadData = async () => {
        if (!partyId) return;
        setLoading(true);
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
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
        pollingRef.current = setInterval(loadData, 15_000);
        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
        };
    }, [partyId]);

    // Listen to campaign WS for real-time session events
    const { lastEvent } = useCampaignEvents(party?.campaignId ?? null);

    useEffect(() => {
        if (!lastEvent || !party) return;
        if (lastEvent.type === "session_started") {
            // Redirect GM to the dashboard when lobby transitions to active
            navigate(routes.campaignDashboard.replace(":campaignId", party.campaignId));
        }
        if (lastEvent.type === "session_closed" || lastEvent.type === "session_lobby" || lastEvent.type === "party_member_updated") {
            loadData();
        }
    }, [lastEvent, party, navigate]);

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
        try {
            await partiesRepo.createPartySession(partyId, { title });
            setShowStartModal(false);
            navigate(routes.campaignDashboard.replace(":campaignId", party.campaignId));
        } catch (err: any) {
            alert(err?.message ?? "Failed to start session");
        } finally {
            setStarting(false);
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
                    {activeSession ? (
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

            {activeSession && (
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
