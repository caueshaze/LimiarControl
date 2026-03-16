import { useNavigate, useParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import { getCampaignSystemLabel, type CampaignSystemType } from "../../entities/campaign";
import { useLocale } from "../../shared/hooks/useLocale";
import { useActiveSession, useSession, useCampaignEvents, useSessionCommands } from "../../features/sessions";
import { campaignsRepo } from "../../shared/api/campaignsRepo";
import { sessionsRepo, type ActivityEvent, type LobbyStatus } from "../../shared/api/sessionsRepo";
import { partiesRepo, type PartyMemberSummary } from "../../shared/api/partiesRepo";
import { membersRepo } from "../../shared/api/membersRepo";
import { inventoryRepo } from "../../shared/api/inventoryRepo";
import { itemsRepo } from "../../shared/api/itemsRepo";
import { sessionStatesRepo } from "../../shared/api/sessionStatesRepo";
import type { Item } from "../../entities/item";
import { StartSessionModal } from "../../features/sessions/components/StartSessionModal";
import { SessionTimer } from "../../shared/ui/SessionTimer";
import { DiceVisualizer } from "../../features/dice-roller/components/DiceVisualizer";
import { useRollSession } from "../../features/dice-roller";
import type { InventoryItem } from "../../entities/inventory";
import type { CurrencyWallet } from "../../shared/api/inventoryRepo";
import { EMPTY_WALLET, formatWallet, normalizeWallet } from "../../features/shop/utils/shopCurrency";

function formatOffset(seconds: number): string {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h${String(m).padStart(2, "0")}m`;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function ActivityRow({ event }: { event: ActivityEvent }) {
    const { t } = useLocale();
    const actor = event.displayName ?? event.username ?? "Unknown";
    if (event.type === "roll") {
        return (
            <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
                <span className="mt-0.5 text-base">🎲</span>
                <div className="flex-1 min-w-0">
                    <p className="text-sm text-white">
                        <span className="font-semibold">{actor}</span>
                        {" rolled "}
                        <span className="font-mono text-limiar-300">{event.expression}</span>
                        {" → "}
                        <span className="font-bold text-limiar-400">{event.total}</span>
                        {event.results.length > 1 && (
                            <span className="text-xs text-slate-500 ml-1">({event.results.join(", ")})</span>
                        )}
                    </p>
                    {event.label && <p className="text-xs text-slate-400 mt-0.5">{t("sessionActivity.reason")} {event.label}</p>}
                </div>
                <span className="text-xs font-mono text-slate-500 shrink-0">{formatOffset(event.sessionOffsetSeconds)}</span>
            </div>
        );
    }
    if (event.type === "shop") {
        return (
            <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
                <span className="mt-0.5 text-base">{event.action === "opened" ? "🏪" : "🔒"}</span>
                <div className="flex-1 min-w-0">
                    <p className="text-sm text-white">
                        <span className="font-semibold">{actor}</span>
                        {event.action === "opened" ? " opened the shop" : " closed the shop"}
                    </p>
                </div>
                <span className="text-xs font-mono text-slate-500 shrink-0">{formatOffset(event.sessionOffsetSeconds)}</span>
            </div>
        );
    }
    return (
        <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
            <span className="mt-0.5 text-base">🛒</span>
            <div className="flex-1 min-w-0">
                <p className="text-sm text-white">
                    <span className="font-semibold">{actor}</span>
                    {" bought "}
                    <span className="font-semibold text-amber-300">{event.itemName}</span>
                    {event.quantity > 1 && <span className="text-slate-400"> ×{event.quantity}</span>}
                </p>
            </div>
            <span className="text-xs font-mono text-slate-500 shrink-0">{formatOffset(event.sessionOffsetSeconds)}</span>
        </div>
    );
}

type CommandFeedback = {
    tone: "success" | "error";
    type: "open_shop" | "close_shop" | "request_roll";
    message: string;
};

type GrantFeedback = {
    tone: "success" | "error";
    message: string;
};

export const GmDashboardPage = () => {
    const { campaignId } = useParams<{ campaignId: string }>();
    const navigate = useNavigate();
    const { selectedCampaign, selectedCampaignId, selectCampaign } = useCampaigns();
    const { t } = useLocale();
    const effectiveCampaignId = campaignId ?? selectedCampaignId ?? null;
    const { activeSession, loading, activate, endSession, refresh: refreshSession } = useActiveSession(effectiveCampaignId);
    const { selectedSessionId, setSelectedSessionId } = useSession();
    const { shopOpen: shopActive } = useSessionCommands();
    const { events: rollEvents } = useRollSession();

    const [creating, setCreating] = useState(false);
    const [_gmName, setGmName] = useState<string | null>(null);
    const [overviewName, setOverviewName] = useState<string | null>(null);
    const [overviewSystem, setOverviewSystem] = useState<CampaignSystemType | null>(null);

    const [_overviewError, setOverviewError] = useState<string | null>(null);
    const [commandSending, setCommandSending] = useState(false);
    const [rollExpression, setRollExpression] = useState("d20");
    const [rollReason, setRollReason] = useState("");
    const [rollAdvantage, setRollAdvantage] = useState<"normal" | "advantage" | "disadvantage">("normal");
    const [showStartModal, setShowStartModal] = useState(false);
    const [activityFeed, setActivityFeed] = useState<ActivityEvent[]>([]);
    const activityIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const [partyPlayers, setPartyPlayers] = useState<PartyMemberSummary[]>([]);
    const [rollTargetUserId, setRollTargetUserId] = useState<string | null>(null);
    const [memberIdByUserId, setMemberIdByUserId] = useState<Record<string, string>>({});
    const [inventoryByMemberId, setInventoryByMemberId] = useState<Record<string, InventoryItem[]>>({});
    const [walletByUserId, setWalletByUserId] = useState<Record<string, CurrencyWallet>>({});
    const [inventoryOpenForUserId, setInventoryOpenForUserId] = useState<string | null>(null);
    const [catalogItems, setCatalogItems] = useState<Record<string, Item>>({});
    const [commandFeedback, setCommandFeedback] = useState<CommandFeedback | null>(null);
    const [shopUiOpen, setShopUiOpen] = useState(false);
    const [grantFeedbackByUserId, setGrantFeedbackByUserId] = useState<Record<string, GrantFeedback>>({});
    const [currencyDraftByUserId, setCurrencyDraftByUserId] = useState<
        Record<string, { amount: string; coin: keyof CurrencyWallet }>
    >({});
    const [itemDraftByUserId, setItemDraftByUserId] = useState<
        Record<string, { itemId: string; quantity: string }>
    >({});
    const [grantingCurrencyForUserId, setGrantingCurrencyForUserId] = useState<string | null>(null);
    const [grantingItemForUserId, setGrantingItemForUserId] = useState<string | null>(null);
    const commandFeedbackTimeoutRef = useRef<number | null>(null);

    const rollOptions = useMemo(
        () => ["d4", "d6", "d8", "d10", "d12", "d20"],
        []
    );

    const [lobbyStatus, setLobbyStatus] = useState<LobbyStatus | null>(null);
    const [forceStarting, setForceStarting] = useState(false);
    const [missingSheetsPlayers, setMissingSheetsPlayers] = useState<{ userId: string; displayName: string }[]>([]);

    const { lastEvent, onlineUsers } = useCampaignEvents(effectiveCampaignId);
    const sortedCatalogItems = useMemo(
        () => Object.values(catalogItems).sort((left, right) => left.name.localeCompare(right.name)),
        [catalogItems]
    );

    const refreshPlayerInventory = useCallback(async (userId: string) => {
        const memberId = memberIdByUserId[userId];
        if (!memberId || !effectiveCampaignId) return;
        try {
            const items = await inventoryRepo.list(effectiveCampaignId, memberId, activeSession?.partyId);
            setInventoryByMemberId(prev => ({ ...prev, [memberId]: items }));
        } catch {
            // ignore
        }
    }, [activeSession?.partyId, effectiveCampaignId, memberIdByUserId]);

    const refreshPlayerWallet = useCallback(async (userId: string) => {
        if (!activeSession?.id) return;
        try {
            const state = await sessionStatesRepo.getByPlayer(activeSession.id, userId);
            const nextWallet = normalizeWallet(
                (state.state as { currency?: unknown } | null | undefined)?.currency
            );
            setWalletByUserId(prev => ({ ...prev, [userId]: nextWallet }));
        } catch {
            setWalletByUserId(prev => ({ ...prev, [userId]: EMPTY_WALLET }));
        }
    }, [activeSession?.id]);

    const refreshActivity = useCallback(async () => {
        if (!activeSession?.id) return;
        try {
            const events = await sessionsRepo.getActivity(activeSession.id);
            setActivityFeed(events);
        } catch {
            // ignore
        }
    }, [activeSession?.id]);

    useEffect(() => {
        if (!activeSession?.id) {
            setActivityFeed([]);
            if (activityIntervalRef.current) {
                clearInterval(activityIntervalRef.current);
                activityIntervalRef.current = null;
            }
            return;
        }
        refreshActivity();
        activityIntervalRef.current = setInterval(refreshActivity, 10_000);
        return () => {
            if (activityIntervalRef.current) {
                clearInterval(activityIntervalRef.current);
                activityIntervalRef.current = null;
            }
        };
    }, [activeSession?.id, refreshActivity]);

    useEffect(() => {
        if (shopActive) {
            setShopUiOpen(true);
        }
    }, [shopActive]);

    useEffect(() => {
        if (!lastEvent) return;
        refreshActivity();
        // When lobby transitions to active, refresh session state
        if (lastEvent.type === "session_started" || lastEvent.type === "session_lobby" || lastEvent.type === "session_closed") {
            refreshSession();
        }
        if (lastEvent.type === "shop_opened") {
            if (lastEvent.payload.partyId && activeSession?.partyId && lastEvent.payload.partyId !== activeSession.partyId) {
                return;
            }
            setShopUiOpen(true);
        }
        if (lastEvent.type === "shop_closed") {
            if (lastEvent.payload.partyId && activeSession?.partyId && lastEvent.payload.partyId !== activeSession.partyId) {
                return;
            }
            setShopUiOpen(false);
        }
        if (lastEvent.type === "session_lobby") {
            setLobbyStatus({
                sessionId: lastEvent.payload.sessionId,
                campaignId: lastEvent.payload.campaignId,
                partyId: lastEvent.payload.partyId,
                expected: lastEvent.payload.expectedPlayers,
                ready: lastEvent.payload.readyUserIds ?? [],
                readyCount: lastEvent.payload.readyCount ?? 0,
                totalCount: lastEvent.payload.totalCount ?? lastEvent.payload.expectedPlayers.length,
            });
        }
        if (lastEvent.type === "player_joined_lobby") {
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
        }
        if (lastEvent.type === "party_member_updated" && activeSession?.partyId) {
            partiesRepo.get(activeSession.partyId).then((party) => {
                const players = party.members.filter((m) => m.role === "PLAYER" && m.status === "joined");
                setPartyPlayers(players);
            }).catch(() => {});
        }
        if (lastEvent.type === "shop_purchase_created" || lastEvent.type === "shop_sale_created") {
            const eventUserId =
                typeof lastEvent.payload.userId === "string" ? lastEvent.payload.userId : null;
            if (eventUserId) {
                void refreshPlayerInventory(eventUserId);
                void refreshPlayerWallet(eventUserId);
            }
        }
        if (lastEvent.type === "gm_granted_item") {
            const eventUserId =
                typeof lastEvent.payload.playerUserId === "string" ? lastEvent.payload.playerUserId : null;
            if (eventUserId) {
                void refreshPlayerInventory(eventUserId);
            }
        }
        if (lastEvent.type === "gm_granted_currency") {
            const eventUserId =
                typeof lastEvent.payload.playerUserId === "string" ? lastEvent.payload.playerUserId : null;
            if (eventUserId) {
                setWalletByUserId(prev => ({
                    ...prev,
                    [eventUserId]: normalizeWallet(
                        (lastEvent.payload as { currentCurrency?: unknown } | null | undefined)?.currentCurrency
                    ),
                }));
            }
        }
        if (lastEvent.type === "session_state_updated") {
            const eventUserId =
                typeof lastEvent.payload.playerUserId === "string" ? lastEvent.payload.playerUserId : null;
            if (eventUserId && partyPlayers.some((player) => player.userId === eventUserId)) {
                void refreshPlayerWallet(eventUserId);
            }
        }
    }, [activeSession?.partyId, lastEvent, partyPlayers, refreshActivity, refreshPlayerInventory, refreshPlayerWallet, refreshSession]);

    useEffect(() => {
        if (!effectiveCampaignId) { setCatalogItems({}); return; }
        itemsRepo.list(effectiveCampaignId).then(items => {
            const map: Record<string, Item> = {};
            for (const it of items) map[it.id] = it;
            setCatalogItems(map);
        }).catch(() => {});
    }, [effectiveCampaignId]);

    useEffect(() => {
        if (!activeSession?.partyId || !effectiveCampaignId) {
            setPartyPlayers([]);
            setMemberIdByUserId({});
            setInventoryByMemberId({});
            setWalletByUserId({});
            return;
        }
        Promise.all([
            partiesRepo.get(activeSession.partyId),
            membersRepo.list(effectiveCampaignId),
        ]).then(([party, campaignMembers]) => {
            const players = party.members.filter(m => m.role === "PLAYER" && m.status === "joined");
            setPartyPlayers(players);
            const map: Record<string, string> = {};
            for (const cm of campaignMembers) {
                map[cm.userId] = cm.id;
            }
            setMemberIdByUserId(map);
        }).catch(() => {});
    }, [activeSession?.partyId, effectiveCampaignId]);

    useEffect(() => {
        if (!effectiveCampaignId) {
            return;
        }
        if (selectedCampaignId !== effectiveCampaignId) {
            selectCampaign(effectiveCampaignId);
        }
    }, [effectiveCampaignId, selectedCampaignId, selectCampaign]);

    useEffect(() => {
        if (!effectiveCampaignId) {
            setGmName(null);
            return;
        }
        campaignsRepo
            .overview(effectiveCampaignId)
            .then((data) => {
                setGmName(data.gmName ?? null);
                setOverviewName(data.name);
                setOverviewSystem(data.systemType);
                setOverviewError(null);
            })
            .catch((error: { message?: string }) => {
                setGmName(null);
                setOverviewName(null);
                setOverviewSystem(null);
                setOverviewError(error?.message ?? "Failed to load campaign");
            });
    }, [effectiveCampaignId]);

    useEffect(() => {
        if (!activeSession?.id) return;
        if (selectedSessionId !== activeSession.id) {
            setSelectedSessionId(activeSession.id);
        }
    }, [activeSession?.id, selectedSessionId, setSelectedSessionId]);

    const handleOpenInventory = async (userId: string) => {
        if (inventoryOpenForUserId === userId) {
            setInventoryOpenForUserId(null);
            return;
        }
        setInventoryOpenForUserId(userId);
        await Promise.all([
            refreshPlayerInventory(userId),
            refreshPlayerWallet(userId),
        ]);
    };

    const handleGrantCurrency = async (userId: string) => {
        if (!activeSession?.id || grantingCurrencyForUserId) return;
        const draft = currencyDraftByUserId[userId] ?? { amount: "", coin: "gp" as keyof CurrencyWallet };
        const amount = Number(draft.amount);
        if (!Number.isFinite(amount) || amount <= 0) {
            setGrantFeedbackByUserId(prev => ({
                ...prev,
                [userId]: { tone: "error", message: "Enter a valid amount before sending currency." },
            }));
            return;
        }
        setGrantingCurrencyForUserId(userId);
        setGrantFeedbackByUserId(prev => ({
            ...prev,
            [userId]: { tone: "success", message: "Sending currency..." },
        }));
        try {
            const result = await sessionsRepo.grantCurrency(activeSession.id, {
                playerUserId: userId,
                currency: { [draft.coin]: amount },
            });
            setWalletByUserId(prev => ({
                ...prev,
                [userId]: normalizeWallet(result.currentCurrency),
            }));
            setCurrencyDraftByUserId(prev => ({
                ...prev,
                [userId]: { amount: "", coin: draft.coin },
            }));
            setGrantFeedbackByUserId(prev => ({
                ...prev,
                [userId]: { tone: "success", message: `Currency delivered. Current funds: ${formatWallet(result.currentCurrency)}.` },
            }));
        } catch (error) {
            setGrantFeedbackByUserId(prev => ({
                ...prev,
                [userId]: {
                    tone: "error",
                    message: (error as { message?: string })?.message ?? "Could not deliver currency right now.",
                },
            }));
        } finally {
            setGrantingCurrencyForUserId(null);
        }
    };

    const handleGrantItem = async (userId: string) => {
        if (!activeSession?.id || grantingItemForUserId) return;
        const draft = itemDraftByUserId[userId] ?? { itemId: sortedCatalogItems[0]?.id ?? "", quantity: "1" };
        const quantity = Number(draft.quantity);
        if (!draft.itemId) {
            setGrantFeedbackByUserId(prev => ({
                ...prev,
                [userId]: { tone: "error", message: "Choose an item before sending it." },
            }));
            return;
        }
        if (!Number.isFinite(quantity) || quantity <= 0) {
            setGrantFeedbackByUserId(prev => ({
                ...prev,
                [userId]: { tone: "error", message: "Enter a valid quantity before sending the item." },
            }));
            return;
        }
        const memberId = memberIdByUserId[userId];
        setGrantingItemForUserId(userId);
        setGrantFeedbackByUserId(prev => ({
            ...prev,
            [userId]: { tone: "success", message: "Sending item..." },
        }));
        try {
            const result = await sessionsRepo.grantItem(activeSession.id, {
                playerUserId: userId,
                itemId: draft.itemId,
                quantity,
            });
            if (memberId) {
                setInventoryByMemberId(prev => {
                    const current = prev[memberId] ?? [];
                    const existing = current.find(item => item.id === result.inventoryItem.id);
                    return {
                        ...prev,
                        [memberId]: existing
                            ? current.map(item => item.id === result.inventoryItem.id ? result.inventoryItem : item)
                            : [result.inventoryItem, ...current],
                    };
                });
            }
            setItemDraftByUserId(prev => ({
                ...prev,
                [userId]: { itemId: draft.itemId, quantity: "1" },
            }));
            setGrantFeedbackByUserId(prev => ({
                ...prev,
                [userId]: {
                    tone: "success",
                    message: `${result.itemName} x${result.quantity} delivered successfully.`,
                },
            }));
        } catch (error) {
            setGrantFeedbackByUserId(prev => ({
                ...prev,
                [userId]: {
                    tone: "error",
                    message: (error as { message?: string })?.message ?? "Could not deliver the item right now.",
                },
            }));
        } finally {
            setGrantingItemForUserId(null);
        }
    };

    // Poll lobby status when session is in LOBBY state
    useEffect(() => {
        if (!activeSession?.id || activeSession.status !== "LOBBY") {
            setLobbyStatus(null);
            return;
        }
        let cancelled = false;
        sessionsRepo.getLobbyStatus(activeSession.id).then(s => {
            if (!cancelled) setLobbyStatus(s);
        }).catch(() => {});
        const interval = setInterval(() => {
            sessionsRepo.getLobbyStatus(activeSession.id).then(s => {
                if (!cancelled) setLobbyStatus(s);
            }).catch(() => {});
        }, 2000);
        return () => { cancelled = true; clearInterval(interval); };
    }, [activeSession?.id, activeSession?.status]);

    const handleForceStart = async () => {
        if (!activeSession?.id || forceStarting) return;
        setForceStarting(true);
        setMissingSheetsPlayers([]);
        try {
            const updated = await sessionsRepo.forceStartLobby(activeSession.id);
            if (updated?.id) setSelectedSessionId(updated.id);
        } catch (err: unknown) {
            const detail = (err as { data?: { detail?: { code?: string; players?: { userId: string; displayName: string }[] } } })?.data?.detail;
            if (detail?.code === "missing_character_sheets") {
                setMissingSheetsPlayers(detail.players ?? []);
            }
        } finally {
            setForceStarting(false);
        }
    };

    const handleActivateClick = () => setShowStartModal(true);

    const handleConfirmStart = async (name: string) => {
        if (creating) return;
        setCreating(true);
        setMissingSheetsPlayers([]);
        try {
            const session = await activate(name);
            if (session?.id) setSelectedSessionId(session.id);
            setShowStartModal(false);
        } catch (err: unknown) {
            const detail = (err as { data?: { detail?: { code?: string; players?: { userId: string; displayName: string }[] } } })?.data?.detail;
            if (detail?.code === "missing_character_sheets") {
                setMissingSheetsPlayers(detail.players ?? []);
                setShowStartModal(false);
            }
        } finally {
            setCreating(false);
        }
    };

    const handleEndSession = async () => {
        if (!confirm(t("common.close") ?? "Are you sure you want to end this session?")) return;
        const partyId = activeSession?.partyId;
        await endSession();
        if (partyId) {
            navigate(routes.partyDetails.replace(":partyId", partyId));
        } else {
            navigate(routes.home);
        }
    };

    const handleCommand = async (
        type: "open_shop" | "close_shop" | "request_roll",
        payload?: Record<string, unknown>
    ) => {
        if (!activeSession?.id || commandSending) return;
        setCommandSending(true);
        setCommandFeedback(null);
        try {
            const extra: Record<string, unknown> = {};
            if (type === "request_roll" && rollTargetUserId) {
                extra.targetUserId = rollTargetUserId;
            }
            if (type === "request_roll") {
                if (rollReason.trim()) extra.reason = rollReason.trim();
                if (rollAdvantage !== "normal") extra.mode = rollAdvantage;
            }
            await sessionsRepo.command(activeSession.id, {
                type,
                payload: { ...(payload ?? {}), ...extra },
            });
            if (type === "open_shop") {
                setShopUiOpen(true);
            }
            if (type === "close_shop") {
                setShopUiOpen(false);
            }
            const message =
                type === "open_shop"
                    ? "Shop command accepted by the server."
                    : type === "close_shop"
                        ? "Close shop command accepted by the server."
                        : "Roll request accepted by the server.";
            if (commandFeedbackTimeoutRef.current) {
                window.clearTimeout(commandFeedbackTimeoutRef.current);
            }
            setCommandFeedback({ tone: "success", type, message });
            commandFeedbackTimeoutRef.current = window.setTimeout(() => {
                setCommandFeedback(null);
                commandFeedbackTimeoutRef.current = null;
            }, 4000);
        } catch (error) {
            const message = (error as { message?: string })?.message ?? "Command failed before the server accepted it.";
            if (commandFeedbackTimeoutRef.current) {
                window.clearTimeout(commandFeedbackTimeoutRef.current);
            }
            setCommandFeedback({ tone: "error", type, message });
            commandFeedbackTimeoutRef.current = window.setTimeout(() => {
                setCommandFeedback(null);
                commandFeedbackTimeoutRef.current = null;
            }, 5000);
        } finally {
            setCommandSending(false);
        }
    };

    useEffect(() => {
        return () => {
            if (commandFeedbackTimeoutRef.current) {
                window.clearTimeout(commandFeedbackTimeoutRef.current);
            }
        };
    }, []);

    return (
        <section className="space-y-8">
            {/* Header / Context */}
            <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-6">
                <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-limiar-300">
                        GM Command Center
                    </p>
                    <h1 className="mt-2 text-3xl font-bold text-white">
                        {selectedCampaign?.name ?? overviewName ?? "Untitled Campaign"}
                    </h1>
                    <p className="mt-1 text-sm text-slate-400">
                        {overviewSystem ? getCampaignSystemLabel(overviewSystem) : "No System"}
                    </p>
                </div>
                <div className="flex gap-3">
                </div>
            </header>

            {/* Missing character sheets warning */}
            {missingSheetsPlayers.length > 0 && (
                <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4">
                    <div className="flex items-start gap-3">
                        <span className="mt-0.5 text-amber-400 text-lg shrink-0">&#9888;</span>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-amber-300">
                                Session blocked — players without a character sheet:
                            </p>
                            <ul className="mt-2 space-y-1">
                                {missingSheetsPlayers.map(p => (
                                    <li key={p.userId} className="text-sm text-amber-200">
                                        {p.displayName}
                                    </li>
                                ))}
                            </ul>
                            <p className="mt-2 text-xs text-amber-500">
                                All players must fill and save their character sheet before the session can start.
                            </p>
                        </div>
                        <button
                            onClick={() => setMissingSheetsPlayers([])}
                            className="text-amber-500 hover:text-amber-300 text-xs shrink-0"
                        >
                            &#10005;
                        </button>
                    </div>
                </div>
            )}

            {/* Session Management */}
            <div className="grid gap-6">
                <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg font-semibold text-white">Session Status</h2>
                        {activeSession && (
                            <div className="flex items-center gap-3">
                                <button
                                    onClick={handleEndSession}
                                    className="rounded-full border border-red-500/30 bg-red-500/10 px-3 py-1 text-xs font-semibold text-red-400 hover:bg-red-500/20"
                                >
                                    {activeSession.status === "LOBBY" ? "Cancel Lobby" : "End Session"}
                                </button>
                                <span className={`rounded-full px-3 py-1 text-xs font-semibold border ${
                                    activeSession.status === "LOBBY"
                                        ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                                        : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                }`}>
                                    {activeSession.status === "LOBBY" ? "LOBBY" : "LIVE"}
                                </span>
                            </div>
                        )}
                    </div>

                    <div className="mt-6 rounded-2xl bg-slate-950/50 border border-slate-800/50 overflow-hidden">
                        {loading ? (
                            <div className="flex items-center justify-center py-10">
                                <span className="text-slate-400">Loading session...</span>
                            </div>
                        ) : activeSession?.status === "LOBBY" ? (
                            /* ── Waiting Room ── */
                            <div className="p-6 space-y-6">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                                            <span className="text-xs font-bold uppercase tracking-widest text-amber-400">Lobby</span>
                                        </div>
                                        <h3 className="text-xl font-bold text-white">{activeSession.title}</h3>
                                        <p className="text-xs text-slate-500 mt-0.5">#{activeSession.number} · Waiting for players to join</p>
                                    </div>
                                    <button
                                        onClick={handleForceStart}
                                        disabled={forceStarting}
                                        className="rounded-full border border-limiar-500/30 bg-limiar-500/10 px-4 py-2 text-xs font-bold uppercase tracking-widest text-limiar-400 hover:bg-limiar-500/20 disabled:opacity-50 transition-all"
                                    >
                                        {forceStarting ? "Starting..." : "Force Start"}
                                    </button>
                                </div>

                                {lobbyStatus && lobbyStatus.expected.length > 0 ? (
                                    <div className="space-y-2">
                                        <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-slate-500">
                                            Players ({lobbyStatus.ready.length}/{lobbyStatus.expected.length} ready)
                                        </p>
                                        <div className="grid grid-cols-2 gap-2">
                                            {lobbyStatus.expected.map(p => {
                                                const isReady = lobbyStatus.ready.includes(p.userId);
                                                const isOnline = !!onlineUsers[p.userId];
                                                return (
                                                    <div key={p.userId} className={`flex items-center gap-3 rounded-xl px-4 py-3 border transition-all ${
                                                        isReady
                                                            ? "bg-emerald-500/10 border-emerald-500/20"
                                                            : "bg-slate-900/40 border-slate-800/40"
                                                    }`}>
                                                        <div className="relative shrink-0">
                                                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border ${
                                                                isReady ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300" : "bg-slate-800 border-slate-700 text-slate-400"
                                                            }`}>
                                                                {p.displayName.charAt(0).toUpperCase()}
                                                            </div>
                                                            <span className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-slate-950 ${isOnline ? "bg-emerald-400" : "bg-slate-600"}`} />
                                                        </div>
                                                        <div className="min-w-0">
                                                            <p className={`text-sm font-medium truncate ${isReady ? "text-emerald-300" : "text-slate-300"}`}>
                                                                {p.displayName}
                                                            </p>
                                                            <p className={`text-[10px] ${isReady ? "text-emerald-500" : "text-slate-600"}`}>
                                                                {isReady ? "Ready" : isOnline ? "Online" : "Offline"}
                                                            </p>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                ) : (
                                    <p className="text-sm text-slate-500 text-center py-4">No players to wait for.</p>
                                )}
                            </div>
                        ) : activeSession ? (
                            <div className="flex flex-col items-center justify-center space-y-4 py-10">
                                <h3 className="text-2xl font-bold text-white">{activeSession.title || "Untitled Session"}</h3>
                                <div className="text-4xl font-mono text-limiar-400">
                                    <SessionTimer startedAt={activeSession.startedAt ?? activeSession.createdAt} />
                                </div>
                                <div className="flex gap-2 text-sm text-slate-500">
                                    <span>#{activeSession.number}</span>
                                    <span className="text-emerald-400">● Active</span>
                                </div>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center space-y-4 py-10">
                                <p className="text-slate-400 mb-2">No active session</p>
                                <button
                                    onClick={handleActivateClick}
                                    disabled={creating}
                                    className="rounded-full bg-limiar-500 px-8 py-3 text-sm font-bold uppercase tracking-widest text-white shadow-lg shadow-limiar-500/20 hover:bg-limiar-400 disabled:opacity-50 transition-all active:scale-95"
                                >
                                    Start Session
                                </button>
                            </div>
                        )}
                    </div>

                    {/* Session Actions */}
                    {activeSession?.status === "ACTIVE" && (
                        <div className="mt-6 grid gap-4 lg:grid-cols-2">
                            <div className="rounded-2xl border border-slate-800 bg-linear-to-br from-slate-950/60 to-slate-900/40 p-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-500">
                                            Shop Control
                                        </label>
                                        <p className="mt-1 text-xs text-slate-400">
                                            Broadcast the shop command to players.
                                        </p>
                                    </div>
                                    <span
                                        className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${shopUiOpen
                                            ? "border-emerald-500/40 text-emerald-300"
                                            : "border-slate-700 text-slate-400"
                                            }`}
                                    >
                                        {shopUiOpen ? "Live" : "Closed"}
                                    </span>
                                </div>
                                <button
                                    onClick={() => handleCommand(shopUiOpen ? "close_shop" : "open_shop")}
                                    disabled={commandSending}
                                    className={`mt-4 w-full rounded-2xl px-4 py-3 text-xs font-semibold uppercase tracking-[0.25em] transition-colors ${shopUiOpen
                                        ? "bg-rose-900/40 text-rose-200 hover:bg-rose-900/60"
                                        : "bg-limiar-500/80 text-white hover:bg-limiar-500"
                                        }`}
                                >
                                    {shopUiOpen ? "Close Shop" : "Open Shop"}
                                </button>
                                {commandFeedback && (commandFeedback.type === "open_shop" || commandFeedback.type === "close_shop") && (
                                    <div className={`mt-3 rounded-2xl border px-3 py-2 text-[11px] ${
                                        commandFeedback.tone === "success"
                                            ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                                            : "border-rose-500/20 bg-rose-500/10 text-rose-200"
                                    }`}>
                                        {commandFeedback.message}
                                    </div>
                                )}
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-linear-to-br from-slate-950/60 to-slate-900/40 p-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-500">
                                            Dice Request
                                        </label>
                                        <p className="mt-1 text-xs text-slate-400">
                                            Choose a die, target player (optional) and request.
                                        </p>
                                    </div>
                                </div>
                                <div className="mt-4 space-y-3">
                                    <div className="flex flex-wrap items-center gap-3">
                                        <select
                                            value={rollExpression}
                                            onChange={(e) => setRollExpression(e.target.value)}
                                            className="flex-1 rounded-2xl bg-slate-900 border border-slate-700 px-3 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white focus:outline-none focus:border-limiar-500"
                                        >
                                            {rollOptions.map((opt) => (
                                                <option key={opt} value={opt} className="text-slate-900">
                                                    {opt.toUpperCase()}
                                                </option>
                                            ))}
                                        </select>
                                        <select
                                            value={rollTargetUserId ?? ""}
                                            onChange={(e) => setRollTargetUserId(e.target.value || null)}
                                            className="flex-1 rounded-2xl bg-slate-900 border border-slate-700 px-3 py-2 text-xs text-white focus:outline-none focus:border-limiar-500"
                                        >
                                            <option value="">All players</option>
                                            {partyPlayers.map((p) => (
                                                <option key={p.userId} value={p.userId}>
                                                    {p.displayName || p.username || "Player"}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                    <input
                                        type="text"
                                        value={rollReason}
                                        onChange={(e) => setRollReason(e.target.value)}
                                        placeholder="Reason (e.g. Perception check)"
                                        className="w-full rounded-2xl bg-slate-900 border border-slate-700 px-3 py-2 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-limiar-500"
                                    />
                                    <div className="flex rounded-2xl overflow-hidden border border-slate-700 text-[10px] font-bold uppercase tracking-widest">
                                        {(["normal", "advantage", "disadvantage"] as const).map(opt => (
                                            <button
                                                key={opt}
                                                type="button"
                                                onClick={() => setRollAdvantage(opt)}
                                                className={`flex-1 py-2 transition-colors ${
                                                    rollAdvantage === opt
                                                        ? opt === "advantage"
                                                            ? "bg-emerald-500/20 text-emerald-400"
                                                            : opt === "disadvantage"
                                                                ? "bg-red-500/20 text-red-400"
                                                                : "bg-slate-700 text-white"
                                                        : "bg-slate-900 text-slate-500 hover:bg-slate-800"
                                                }`}
                                            >
                                                {opt === "normal" ? "Normal" : opt === "advantage" ? "Adv." : "Disadv."}
                                            </button>
                                        ))}
                                    </div>
                                    <button
                                        onClick={() => handleCommand("request_roll", { expression: rollExpression })}
                                        disabled={commandSending}
                                        className="w-full rounded-2xl bg-slate-800 px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-slate-200 hover:bg-slate-700"
                                    >
                                        Request Roll{rollTargetUserId ? ` → ${partyPlayers.find(p => p.userId === rollTargetUserId)?.displayName ?? "Player"}` : ""}
                                    </button>
                                    {commandFeedback?.type === "request_roll" && (
                                        <div className={`rounded-2xl border px-3 py-2 text-[11px] ${
                                            commandFeedback.tone === "success"
                                                ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                                                : "border-rose-500/20 bg-rose-500/10 text-rose-200"
                                        }`}>
                                            {commandFeedback.message}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </div>

            {activeSession?.status === "ACTIVE" && partyPlayers.length > 0 && (
                <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
                    <h2 className="text-lg font-semibold text-white mb-4">Party Inventories</h2>
                    <div className="space-y-3">
                        {partyPlayers.map((player) => {
                            const memberId = memberIdByUserId[player.userId];
                            const items = memberId ? inventoryByMemberId[memberId] : undefined;
                            const isOpen = inventoryOpenForUserId === player.userId;
                            const isOnline = !!onlineUsers[player.userId];
                            const playSheetRoute = activeSession?.partyId
                                ? `${routes.characterSheetParty.replace(":partyId", activeSession.partyId)}?${new URLSearchParams({
                                    mode: "play",
                                    playerId: player.userId,
                                    playerName: player.displayName || player.username || "Player",
                                    ...(effectiveCampaignId ? { campaignId: effectiveCampaignId } : {}),
                                    from: "gm-dashboard",
                                }).toString()}`
                                : null;
                            return (
                                <div key={player.userId} className="rounded-2xl border border-slate-800 overflow-hidden">
                                    <button
                                        onClick={() => handleOpenInventory(player.userId)}
                                        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-900/40 transition-colors"
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className="relative">
                                                <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-limiar-400 font-bold text-sm border border-slate-700">
                                                    {(player.displayName || player.username || "?").charAt(0).toUpperCase()}
                                                </div>
                                                <span className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-slate-900 ${isOnline ? "bg-emerald-400" : "bg-slate-600"}`} />
                                            </div>
                                            <div>
                                                <span className="text-sm font-medium text-white">{player.displayName || player.username || "Player"}</span>
                                                <span className={`block text-[10px] ${isOnline ? "text-emerald-500" : "text-slate-600"}`}>
                                                    {isOnline ? "Online" : "Offline"}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            {playSheetRoute && (
                                                <button
                                                    type="button"
                                                    onClick={(event) => {
                                                        event.stopPropagation();
                                                        navigate(playSheetRoute);
                                                    }}
                                                    className="rounded-full border border-limiar-500/30 bg-limiar-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-limiar-300 hover:bg-limiar-500/20"
                                                >
                                                    Play Sheet
                                                </button>
                                            )}
                                            <span className={`text-slate-500 text-xs transition-transform ${isOpen ? "rotate-180" : ""}`}>▼</span>
                                        </div>
                                    </button>
                                    {isOpen && (
                                        <div className="px-4 pb-4 border-t border-slate-800/60">
                                            {!items ? (
                                                <p className="text-xs text-slate-500 py-2">Loading...</p>
                                            ) : items.length === 0 ? (
                                                <p className="text-xs text-slate-500 py-2">No items yet.</p>
                                            ) : (
                                                <div className="mt-3 space-y-2">
                                                    {items.map((item) => (
                                                        <div key={item.id} className="flex items-center justify-between rounded-xl bg-slate-900/60 px-3 py-2">
                                                            <span className="text-sm text-white">{catalogItems[item.itemId]?.name ?? item.itemId}</span>
                                                            <div className="flex items-center gap-2 text-xs text-slate-400">
                                                                <span>×{item.quantity}</span>
                                                                {item.isEquipped && <span className="rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-emerald-400">Equipped</span>}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                            <div className="mt-4 grid gap-3 lg:grid-cols-2">
                                                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
                                                    <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">
                                                        Give Currency
                                                    </p>
                                                    <p className="mt-2 text-xs text-slate-400">
                                                        Current funds: <span className="font-semibold text-white">{formatWallet(walletByUserId[player.userId] ?? EMPTY_WALLET)}</span>
                                                    </p>
                                                    <div className="mt-3 flex gap-2">
                                                        <input
                                                            type="number"
                                                            min={1}
                                                            value={currencyDraftByUserId[player.userId]?.amount ?? ""}
                                                            onChange={(event) =>
                                                                setCurrencyDraftByUserId(prev => ({
                                                                    ...prev,
                                                                    [player.userId]: {
                                                                        amount: event.target.value,
                                                                        coin: prev[player.userId]?.coin ?? "gp",
                                                                    },
                                                                }))
                                                            }
                                                            placeholder="10"
                                                            className="w-24 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
                                                        />
                                                        <select
                                                            value={currencyDraftByUserId[player.userId]?.coin ?? "gp"}
                                                            onChange={(event) =>
                                                                setCurrencyDraftByUserId(prev => ({
                                                                    ...prev,
                                                                    [player.userId]: {
                                                                        amount: prev[player.userId]?.amount ?? "",
                                                                        coin: event.target.value as keyof CurrencyWallet,
                                                                    },
                                                                }))
                                                            }
                                                            className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs uppercase text-white focus:border-limiar-500 focus:outline-none"
                                                        >
                                                            {(["cp", "sp", "ep", "gp", "pp"] as Array<keyof CurrencyWallet>).map((coin) => (
                                                                <option key={coin} value={coin}>
                                                                    {coin}
                                                                </option>
                                                            ))}
                                                        </select>
                                                        <button
                                                            type="button"
                                                            onClick={() => handleGrantCurrency(player.userId)}
                                                            disabled={grantingCurrencyForUserId === player.userId}
                                                            className="rounded-xl bg-emerald-500/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white hover:bg-emerald-500 disabled:opacity-60"
                                                        >
                                                            {grantingCurrencyForUserId === player.userId ? "Sending..." : "Give"}
                                                        </button>
                                                    </div>
                                                </div>
                                                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
                                                    <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">
                                                        Give Item
                                                    </p>
                                                    <div className="mt-3 flex flex-wrap gap-2">
                                                        <select
                                                            value={itemDraftByUserId[player.userId]?.itemId ?? sortedCatalogItems[0]?.id ?? ""}
                                                            onChange={(event) =>
                                                                setItemDraftByUserId(prev => ({
                                                                    ...prev,
                                                                    [player.userId]: {
                                                                        itemId: event.target.value,
                                                                        quantity: prev[player.userId]?.quantity ?? "1",
                                                                    },
                                                                }))
                                                            }
                                                            className="min-w-[12rem] flex-1 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
                                                        >
                                                            {sortedCatalogItems.length === 0 ? (
                                                                <option value="">No items</option>
                                                            ) : (
                                                                sortedCatalogItems.map((item) => (
                                                                    <option key={item.id} value={item.id}>
                                                                        {item.name}
                                                                    </option>
                                                                ))
                                                            )}
                                                        </select>
                                                        <input
                                                            type="number"
                                                            min={1}
                                                            value={itemDraftByUserId[player.userId]?.quantity ?? "1"}
                                                            onChange={(event) =>
                                                                setItemDraftByUserId(prev => ({
                                                                    ...prev,
                                                                    [player.userId]: {
                                                                        itemId: prev[player.userId]?.itemId ?? sortedCatalogItems[0]?.id ?? "",
                                                                        quantity: event.target.value,
                                                                    },
                                                                }))
                                                            }
                                                            className="w-20 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
                                                        />
                                                        <button
                                                            type="button"
                                                            onClick={() => handleGrantItem(player.userId)}
                                                            disabled={grantingItemForUserId === player.userId || sortedCatalogItems.length === 0}
                                                            className="rounded-xl bg-limiar-500/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white hover:bg-limiar-500 disabled:opacity-60"
                                                        >
                                                            {grantingItemForUserId === player.userId ? "Sending..." : "Give"}
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                            {grantFeedbackByUserId[player.userId] && (
                                                <div className={`mt-3 rounded-2xl border px-3 py-2 text-[11px] ${
                                                    grantFeedbackByUserId[player.userId].tone === "success"
                                                        ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                                                        : "border-rose-500/20 bg-rose-500/10 text-rose-200"
                                                }`}>
                                                    {grantFeedbackByUserId[player.userId].message}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {activeSession?.status === "ACTIVE" && (
                <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
                    <h2 className="text-lg font-semibold text-white mb-4">Session Activity</h2>
                    {activityFeed.length === 0 ? (
                        <p className="text-sm text-slate-500">No activity yet. Roll some dice or open the shop!</p>
                    ) : (
                        <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                            {[...activityFeed].reverse().map((ev, i) => (
                                <ActivityRow key={i} event={ev} />
                            ))}
                        </div>
                    )}
                </div>
            )}
            </div>

            <StartSessionModal
                isOpen={showStartModal}
                onClose={() => setShowStartModal(false)}
                onConfirm={handleConfirmStart}
                loading={creating}
            />

            <DiceVisualizer events={rollEvents} />
        </section>
    );
};
