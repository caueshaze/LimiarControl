import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { partiesRepo, type PartyDetail, type PartyActiveSession } from "../../shared/api/partiesRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import { useCampaignEvents } from "../../features/sessions";
import { useAuth } from "../../features/auth";
import { inventoryRepo } from "../../shared/api/inventoryRepo";
import { itemsRepo } from "../../shared/api/itemsRepo";
import { sessionsRepo, type LobbyStatus } from "../../shared/api/sessionsRepo";
import { characterSheetsRepo } from "../../shared/api/characterSheetsRepo";
import type { InventoryItem } from "../../entities/inventory";
import type { Item } from "../../entities/item";

export const PlayerPartyPage = () => {
    const { partyId } = useParams<{ partyId: string }>();
    const navigate = useNavigate();
    const { t } = useLocale();
    const { user } = useAuth();

    const [party, setParty] = useState<PartyDetail | null>(null);
    const [sessions, setSessions] = useState<PartyActiveSession[]>([]);
    const [loading, setLoading] = useState(true);
    const [myInventory, setMyInventory] = useState<InventoryItem[] | null>(null);
    const [catalogItems, setCatalogItems] = useState<Record<string, Item>>({});
    const [inventoryOpen, setInventoryOpen] = useState(false);

    // Lobby state
    const [lobbyStatus, setLobbyStatus] = useState<LobbyStatus | null>(null);
    const [joiningLobby, setJoiningLobby] = useState(false);
    const [hasJoinedLobby, setHasJoinedLobby] = useState(false);
    const wasLobbyRef = useRef(false);

    // Character sheet
    const [hasCharacterSheet, setHasCharacterSheet] = useState<boolean | null>(null);

    const loadData = useCallback(async () => {
        if (!partyId) return;
        setLoading(true);
        try {
            const [partyData, sessionsData] = await Promise.all([
                partiesRepo.get(partyId),
                partiesRepo.listPartySessions(partyId),
            ]);
            setParty(partyData);
            setSessions(sessionsData);
        } catch {
            // ignore
        } finally {
            setLoading(false);
        }
    }, [partyId]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    useEffect(() => {
        if (!partyId) return;
        characterSheetsRepo.getByParty(partyId)
            .then(() => setHasCharacterSheet(true))
            .catch((err: { status?: number }) => setHasCharacterSheet(err?.status === 404 ? false : null));
    }, [partyId]);

    const { lastEvent } = useCampaignEvents(party?.campaignId ?? null);
    const activeSession = sessions.find(s => s.isActive);

    useEffect(() => {
        if (!party?.campaignId) return;
        Promise.all([
            inventoryRepo.list(party.campaignId),
            itemsRepo.list(party.campaignId),
        ]).then(([inv, items]) => {
            const itemMap: Record<string, Item> = {};
            for (const it of items) itemMap[it.id] = it;
            setCatalogItems(itemMap);
            setMyInventory(inv);
        }).catch(() => { setMyInventory([]); });
    }, [party?.campaignId]);

    useEffect(() => {
        if (!lastEvent) return;
        if (lastEvent.type === "session_started") {
            setLobbyStatus(null);
            setHasJoinedLobby(false);
            loadData();
            // Auto-navigate to the board when lobby transitions to active
            if (partyId) {
                navigate(routes.board.replace(":partyId", partyId));
            }
            return;
        }
        if (lastEvent.type === "session_closed") {
            setLobbyStatus(null);
            setHasJoinedLobby(false);
            loadData();
        }
        if (lastEvent.type === "session_lobby") {
            // Refresh sessions to get the lobby session
            loadData();
            setHasJoinedLobby(false);
        }
        if (lastEvent.type === "party_member_updated") {
            loadData();
        }
        if (lastEvent.type === "player_joined_lobby") {
            if (activeSession?.id) {
                sessionsRepo.getLobbyStatus(activeSession.id).then(setLobbyStatus).catch(() => {});
            }
        }
    }, [lastEvent, loadData, partyId, navigate, activeSession?.id]);

    // Poll lobby status when in lobby
    useEffect(() => {
        if (activeSession?.status === "LOBBY") {
            wasLobbyRef.current = true;
            return;
        }
        if (activeSession?.status === "ACTIVE" && wasLobbyRef.current && partyId) {
            navigate(routes.board.replace(":partyId", partyId), { replace: true });
            wasLobbyRef.current = false;
        }
    }, [activeSession?.status, partyId, navigate]);
    useEffect(() => {
        if (!activeSession?.id || activeSession.status !== "LOBBY") {
            setLobbyStatus(null);
            return;
        }
        let cancelled = false;
        sessionsRepo.getLobbyStatus(activeSession.id).then(status => {
            if (!cancelled) setLobbyStatus(status);
        }).catch(() => {});
        const interval = setInterval(() => {
            sessionsRepo.getLobbyStatus(activeSession.id).then(status => {
                if (!cancelled) setLobbyStatus(status);
            }).catch(() => {});
        }, 3000);
        return () => {
            cancelled = true;
            clearInterval(interval);
        };
    }, [activeSession?.id, activeSession?.status]);

    const handleJoinLobby = async () => {
        if (!activeSession?.id || joiningLobby) return;
        setJoiningLobby(true);
        try {
            await sessionsRepo.joinLobby(activeSession.id);
            setHasJoinedLobby(true);
        } catch {
            // ignore
        } finally {
            setJoiningLobby(false);
        }
    };

    if (loading) {
        return (
            <section className="space-y-8 p-6 lg:p-10">
                <p className="text-slate-400">Loading party data...</p>
            </section>
        );
    }

    if (!party) {
        return (
            <section className="space-y-8 p-6 lg:p-10">
                <p className="text-slate-400">Party not found or you're not a member.</p>
                <Link to={routes.home} className="text-limiar-400 hover:underline">
                    Return Home
                </Link>
            </section>
        );
    }

    const isLobby = activeSession?.status === "LOBBY";
    const isMyTurnToJoin = isLobby && !hasJoinedLobby && user?.userId && lobbyStatus
        ? !lobbyStatus.ready.includes(user.userId)
        : false;
    const myMember = party?.members.find(m => m.userId === user?.userId);
    const isPlayer = myMember?.role === "PLAYER";

    return (
        <section className="space-y-8 lg:p-6 mx-auto max-w-6xl">

            {/* Session Lobby Notification */}
            {isLobby && (
                <div className="relative overflow-hidden rounded-3xl border border-limiar-500/30 bg-linear-to-br from-limiar-950/80 via-slate-950/90 to-void-950 p-8 shadow-[0_0_60px_rgba(34,197,94,0.1)]">
                    {/* Animated background glow */}
                    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(34,197,94,0.08),transparent_60%)]" />

                    <div className="relative flex flex-col md:flex-row md:items-start gap-8">
                        {/* Left: title + join button */}
                        <div className="flex-1 space-y-4">
                            <div className="flex items-center gap-3">
                                <span className="flex h-3 w-3 items-center justify-center">
                                    <span className="absolute inline-flex h-3 w-3 animate-ping rounded-full bg-limiar-400 opacity-75" />
                                    <span className="relative inline-flex h-2 w-2 rounded-full bg-limiar-500" />
                                </span>
                                <span className="text-xs font-bold uppercase tracking-[0.25em] text-limiar-400">
                                    Session Starting
                                </span>
                            </div>

                            <div>
                                <h2 className="text-2xl font-bold text-white">{activeSession?.title}</h2>
                                <p className="mt-1 text-sm text-slate-400">
                                    Your Game Master has started a session. Confirm your presence to begin!
                                </p>
                            </div>

                            {hasJoinedLobby || (user?.userId && lobbyStatus?.ready.includes(user.userId)) ? (
                                <div className="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-5 py-2.5">
                                    <span className="text-sm font-bold text-emerald-400">You're in! Waiting for others...</span>
                                </div>
                            ) : (
                                <button
                                    onClick={handleJoinLobby}
                                    disabled={joiningLobby}
                                    className="inline-flex items-center gap-2 rounded-full bg-limiar-500 px-8 py-3 text-sm font-bold uppercase tracking-widest text-white shadow-[0_0_20px_rgba(34,197,94,0.4)] hover:bg-limiar-400 hover:shadow-[0_0_30px_rgba(34,197,94,0.5)] disabled:opacity-50 transition-all duration-200 active:scale-95"
                                >
                                    {joiningLobby ? "Joining..." : "Join Session"}
                                </button>
                            )}
                        </div>

                        {/* Right: player readiness */}
                        {lobbyStatus && lobbyStatus.expected.length > 0 && (
                            <div className="md:w-56 space-y-3">
                                <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-slate-500">
                                    Players ({lobbyStatus.ready.length}/{lobbyStatus.expected.length})
                                </p>
                                <div className="space-y-2">
                                    {lobbyStatus.expected.map(p => {
                                        const isReady = lobbyStatus.ready.includes(p.userId);
                                        return (
                                            <div key={p.userId} className="flex items-center gap-3">
                                                <span className={`w-5 h-5 rounded-full border-2 flex items-center justify-center text-[10px] font-bold transition-all ${
                                                    isReady
                                                        ? "bg-emerald-500/20 border-emerald-500 text-emerald-400"
                                                        : "bg-slate-800 border-slate-600 text-slate-500"
                                                }`}>
                                                    {isReady ? "✓" : ""}
                                                </span>
                                                <span className={`text-sm ${isReady ? "text-emerald-300 font-medium" : "text-slate-400"}`}>
                                                    {p.displayName}
                                                </span>
                                                {!isReady && (
                                                    <span className="ml-auto text-[10px] text-slate-600 italic">waiting</span>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            <header className="rounded-3xl border border-slate-800 bg-linear-to-br from-void-950 via-slate-950/80 to-limiar-900/10 p-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                    <Link to={routes.home} className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400 hover:text-slate-200">
                        ← Home
                    </Link>
                    <h1 className="mt-3 text-4xl font-bold text-white tracking-tight">{party.name}</h1>
                    <p className="mt-3 text-sm text-slate-400 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-limiar-500/50"></span>
                        Awaiting Game Master
                    </p>
                </div>
                {activeSession && activeSession.status === "ACTIVE" ? (
                    <button
                        onClick={() => navigate(routes.board.replace(":partyId", party.id))}
                        className="rounded-full bg-limiar-500 px-8 py-3.5 text-sm font-bold uppercase tracking-widest text-white shadow-[0_0_20px_rgba(34,197,94,0.3)] hover:bg-limiar-400 hover:scale-105 transition-all duration-300"
                    >
                        Enter Board
                    </button>
                ) : !activeSession ? (
                    <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/40 px-6 py-4 text-center">
                        <p className="text-sm font-medium text-slate-300">No active session.</p>
                        <p className="text-xs text-slate-500 mt-1">Wait for your GM to start a new session.</p>
                    </div>
                ) : null}
            </header>

            {/* Character Sheet Card */}
            {isPlayer && hasCharacterSheet === false ? (
                <div className="relative overflow-hidden rounded-3xl border border-amber-500/30 bg-linear-to-br from-amber-950/40 via-slate-950/80 to-slate-950 p-6 flex flex-col md:flex-row md:items-center gap-6">
                    <div className="flex-1 space-y-2">
                        <p className="text-xs font-bold uppercase tracking-[0.25em] text-amber-400">Action Required</p>
                        <h3 className="text-xl font-bold text-white">You don't have a character sheet yet</h3>
                        <p className="text-sm text-slate-400">
                            Your Game Master cannot start a session until all players have filled in their character sheet.
                            Fill yours in now so the party is ready to play!
                        </p>
                    </div>
                    <Link
                        to={routes.characterSheetParty.replace(":partyId", partyId ?? "")}
                        className="shrink-0 inline-flex items-center gap-2 rounded-full bg-amber-500 px-8 py-3 text-sm font-bold uppercase tracking-widest text-slate-950 shadow-[0_0_20px_rgba(245,158,11,0.3)] hover:bg-amber-400 transition-all active:scale-95"
                    >
                        Create Character Sheet
                    </Link>
                </div>
            ) : isPlayer && hasCharacterSheet === true ? (
                <div className="rounded-3xl border border-slate-800 bg-slate-950/60 p-5 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                        <p className="text-sm font-medium text-slate-300">Character sheet filled in</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link
                            to={routes.characterSheetParty.replace(":partyId", partyId ?? "")}
                            className="rounded-full border border-slate-700 px-4 py-1.5 text-xs font-semibold text-slate-300 hover:border-slate-500 hover:text-white transition-colors"
                        >
                            Character Builder
                        </Link>
                        {activeSession?.status === "ACTIVE" && (
                            <Link
                                to={`${routes.characterSheetParty.replace(":partyId", partyId ?? "")}?mode=play`}
                                className="rounded-full border border-limiar-500/30 bg-limiar-500/10 px-4 py-1.5 text-xs font-semibold text-limiar-300 hover:bg-limiar-500/20 transition-colors"
                            >
                                Open Play Sheet
                            </Link>
                        )}
                    </div>
                </div>
            ) : null}

            <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
                {/* Members List */}
                <div className="space-y-6">
                    <div className="rounded-3xl border border-slate-800 bg-slate-950/60 p-6 md:p-8">
                        <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-3">
                            <span className="w-1 h-4 bg-limiar-500 rounded-full"></span>
                            Party Members
                        </h2>
                        <div className="space-y-3">
                            {party.members.map((m) => (
                                <div key={m.userId} className="flex justify-between items-center rounded-2xl border border-slate-800/40 bg-slate-900/40 p-4 hover:border-slate-700 transition-colors">
                                    <div className="flex items-center gap-4">
                                        <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-limiar-400 font-bold uppercase text-lg border border-slate-700">
                                            {(m.displayName || m.username || "?").charAt(0)}
                                        </div>
                                        <div>
                                            <span className="block text-base text-white font-medium">{m.displayName || m.username || "Unknown Player"}</span>
                                            {m.username && <span className="block text-xs text-slate-500">@{m.username}</span>}
                                        </div>
                                    </div>
                                    <div>
                                        <span className={
                                            `text-[10px] font-bold uppercase tracking-widest px-3 py-1 rounded-full ` +
                                            (m.role === "GM" ? "bg-purple-500/10 text-purple-400 border border-purple-500/20" :
                                                m.status === "joined" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                                                    m.status === "invited" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                                                        "bg-slate-500/10 text-slate-400 border border-slate-500/20")
                                        }>
                                            {m.role === "GM" ? "Game Master" : m.status}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* My Inventory */}
                <div className="rounded-3xl border border-slate-800 bg-slate-950/60 overflow-hidden">
                    <button
                        onClick={() => setInventoryOpen(v => !v)}
                        className="w-full flex items-center justify-between p-6 md:p-8 hover:bg-slate-900/20 transition-colors"
                    >
                        <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-3">
                            <span className="w-1 h-4 bg-amber-500 rounded-full"></span>
                            My Inventory
                        </h2>
                        <span className={`text-slate-500 text-xs transition-transform ${inventoryOpen ? "rotate-180" : ""}`}>▼</span>
                    </button>
                    {inventoryOpen && (
                        <div className="px-6 md:px-8 pb-6 border-t border-slate-800/60">
                            {myInventory === null ? (
                                <p className="text-sm text-slate-500 py-4">Loading inventory...</p>
                            ) : myInventory.length === 0 ? (
                                <p className="text-sm text-slate-500 py-4">No items yet. Buy from the shop during a session.</p>
                            ) : (
                                <div className="mt-4 space-y-2">
                                    {myInventory.map((item) => (
                                        <div key={item.id} className="flex items-center justify-between rounded-2xl border border-slate-800/40 bg-slate-900/40 px-4 py-3">
                                            <div>
                                                <p className="text-sm font-medium text-white">{catalogItems[item.itemId]?.name ?? item.itemId}</p>
                                                {catalogItems[item.itemId]?.type && <p className="text-xs text-slate-500">{catalogItems[item.itemId]?.type}</p>}
                                            </div>
                                            <div className="flex items-center gap-2 text-xs">
                                                <span className="rounded-full border border-slate-700 px-3 py-1 text-slate-300">×{item.quantity}</span>
                                                {item.isEquipped && (
                                                    <span className="rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-1 text-emerald-400">Equipped</span>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Timeline */}
                <div className="space-y-6">
                    <div className="rounded-3xl border border-slate-800 bg-slate-950/60 p-6 md:p-8">
                        <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-3">
                            <span className="w-1 h-4 bg-slate-600 rounded-full"></span>
                            Session History
                        </h2>
                        <div className="mt-6 space-y-6 relative before:absolute before:inset-0 before:ml-2.75 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-linear-to-b before:from-transparent before:via-slate-800 before:to-transparent">
                            {sessions.length === 0 ? (
                                <p className="text-sm text-slate-500 text-center py-8 relative">No past sessions yet.</p>
                            ) : (
                                sessions.map((s, idx) => (
                                    <div key={s.id} className="relative flex items-start justify-between pl-8 border-b border-slate-800/50 pb-6 last:border-0 last:pb-0">
                                        <div className="absolute left-0 top-1.5 w-6 h-6 bg-slate-950 border-2 border-slate-800 rounded-full flex items-center justify-center">
                                            {s.isActive ? (
                                                <span className="w-2 h-2 bg-limiar-500 rounded-full animate-pulse"></span>
                                            ) : (
                                                <span className="text-[10px] font-bold text-slate-500">{idx + 1}</span>
                                            )}
                                        </div>
                                        <div>
                                            <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">
                                                {new Date(s.createdAt).toLocaleDateString()}
                                            </p>
                                            <p className="text-base font-medium text-slate-200">
                                                {s.title}
                                            </p>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
};
