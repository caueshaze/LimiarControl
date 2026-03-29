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
import {
    PartyDetailsActiveSessionBanner,
    PartyDetailsCharacterSheetDraftsCard,
    PartyDetailsInventoryCard,
    PartyDetailsMissingSheetsBanner,
    PartyDetailsOverviewStrip,
    PartyDetailsPlayerSheetsCard,
} from "./PartyDetailsResourceCards";
import { usePartyDetailsResources } from "./usePartyDetailsResources";

export const PartyDetailsPage = () => {
    const { partyId } = useParams<{ partyId: string }>();
    const navigate = useNavigate();
    const { locale, t } = useLocale();

    const [party, setParty] = useState<PartyDetail | null>(null);
    const [sessions, setSessions] = useState<PartyActiveSession[]>([]);
    const [activeSession, setActiveSession] = useState<PartyActiveSession | null>(null);
    const [loading, setLoading] = useState(true);

    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState<UserSearchResult[]>([]);
    const [searching, setSearching] = useState(false);

    const [showStartModal, setShowStartModal] = useState(false);
    const [starting, setStarting] = useState(false);
    const [deletingParty, setDeletingParty] = useState(false);
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

    const { lastEvent, onlineUsers } = useCampaignEvents(partyCampaignId);
    const {
        drafts,
        loadError: resourcesError,
        loading: loadingResources,
        playerResources,
        reloadResources,
        summary: resourceSummary,
    } = usePartyDetailsResources({
        activeSession,
        locale,
        party,
    });

    useEffect(() => {
        if (!lastEvent || !partyCampaignId) return;
        if (lastEvent.type === "session_started") {
            if (lastEvent.payload.partyId && partyId && lastEvent.payload.partyId !== partyId) {
                return;
            }
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

    const handleDeleteParty = async () => {
        if (!party || deletingParty) return;

        const confirmed = confirm(
            `Delete the party "${party.name}" permanently?\n\nThis removes the party, its members, invitations, sessions, sheets, and party inventory.`
        );
        if (!confirmed) return;

        setDeletingParty(true);
        try {
            await partiesRepo.remove(party.id);
            navigate(routes.gmHome);
        } catch (err: any) {
            alert(err?.message ?? "Failed to delete party");
            setDeletingParty(false);
        }
    };

    if (loading) return <section className="space-y-8 p-6"><p className="text-slate-400">Loading party details...</p></section>;

    if (!party) {
        return (
            <section className="space-y-8 p-6">
                <p className="text-slate-400">Party not found.</p>
                <Link to={routes.gmHome} className="text-limiar-400 hover:underline">Return to GM Home</Link>
            </section>
        );
    }

    return (
        <>
        <section className="space-y-8">
            {missingSheetsPlayers.length > 0 && <PartyDetailsMissingSheetsBanner players={missingSheetsPlayers} />}

            <PartyDetailsHeader
                party={party}
                activeSession={activeSession}
                deletingParty={deletingParty}
                onStartSession={() => setShowStartModal(true)}
                onEndSession={handleEndSession}
                onDeleteParty={handleDeleteParty}
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

            {activeSession?.status === "ACTIVE" && <PartyDetailsActiveSessionBanner campaignId={party.campaignId} session={activeSession} />}

            <PartyDetailsOverviewStrip
                activeSessionStatus={resourceSummary.activeSessionStatus}
                invitedPlayers={resourceSummary.invitedPlayers}
                joinedPlayers={resourceSummary.joinedPlayers}
                readySheets={resourceSummary.readySheets}
                totalInventoryItems={resourceSummary.totalInventoryItems}
                totalPlayers={resourceSummary.totalPlayers}
            />

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
                <PartyDetailsPlayerSheetsCard
                    activeSessionPartyId={activeSession?.status === "ACTIVE" ? activeSession.partyId ?? party.id : null}
                    campaignId={party.campaignId}
                    loading={loadingResources}
                    partyId={party.id}
                    players={playerResources}
                />
                <div className="space-y-6">
                    <PartyDetailsCharacterSheetDraftsCard
                        drafts={drafts}
                        loading={loadingResources}
                        partyId={party.id}
                        players={playerResources}
                        onChanged={reloadResources}
                    />
                    <PartyDetailsInventoryCard
                        loadError={resourcesError}
                        loading={loadingResources}
                        players={playerResources}
                    />
                </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
                <PartyDetailsMembersCard
                    party={party}
                    searchQuery={searchQuery}
                    searching={searching}
                    searchResults={searchResults}
                    onSearchChange={setSearchQuery}
                    onInvite={handleInvite}
                />
                <PartyDetailsTimelineCard
                    sessions={sessions}
                    expandedSessionId={expandedSessionId}
                    onToggleSession={setExpandedSessionId}
                />
            </div>
        </section>

        <StartSessionModal isOpen={showStartModal} onClose={() => setShowStartModal(false)} onConfirm={handleStartSession} loading={starting} />
        </>
    );
};
