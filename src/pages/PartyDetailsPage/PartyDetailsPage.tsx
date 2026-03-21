import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { partiesRepo, type PartyDetail, type PartyActiveSession } from "../../shared/api/partiesRepo";
import { usersRepo, type UserSearchResult } from "../../shared/api/usersRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import { StartSessionModal } from "../../features/sessions/components/StartSessionModal";
import { sessionsRepo, type LobbyStatus } from "../../shared/api/sessionsRepo";
import { useCampaignEvents } from "../../features/sessions";
import {
    PartyDetailsHeader,
    PartyDetailsLobbyCard,
    PartyDetailsMembersCard,
    PartyDetailsTimelineCard,
} from "./PartyDetailsPageSections";

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

            <PartyDetailsHeader
                party={party}
                activeSession={activeSession}
                onStartSession={() => setShowStartModal(true)}
                onEndSession={handleEndSession}
            />

            {activeSession?.status === "LOBBY" && (
                <PartyDetailsLobbyCard
                    activeSession={activeSession}
                    lobbyStatus={lobbyStatus}
                    onlineUsers={onlineUsers}
                    forceStarting={forceStarting}
                    onForceStart={handleForceStart}
                />
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
                    <PartyDetailsMembersCard
                        party={party}
                        searchQuery={searchQuery}
                        searching={searching}
                        searchResults={searchResults}
                        onSearchChange={setSearchQuery}
                        onInvite={handleInvite}
                    />
                </div>

                <div className="space-y-6">
                    <PartyDetailsTimelineCard
                        sessions={sessions}
                        expandedSessionId={expandedSessionId}
                        onToggleSession={setExpandedSessionId}
                    />
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
