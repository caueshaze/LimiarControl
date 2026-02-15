import { Link, useParams } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import { getCampaignSystemLabel, type CampaignSystemType } from "../../entities/campaign";
import { useLocale } from "../../shared/hooks/useLocale";
import { useActiveSession, useSession } from "../../features/sessions";
import { campaignsRepo } from "../../shared/api/campaignsRepo";
import { sessionsRepo } from "../../shared/api/sessionsRepo";
import { StartSessionModal } from "../../features/sessions/components/StartSessionModal";
import { SessionTimer } from "../../shared/ui/SessionTimer";
import { DiceVisualizer } from "../../features/dice-roller/components/DiceVisualizer";
import { useRollSession } from "../../features/dice-roller";

export const GmDashboardPage = () => {
    const { campaignId } = useParams<{ campaignId: string }>();
    const { selectedCampaign, selectedCampaignId, selectCampaign } = useCampaigns();
    const { t } = useLocale();
    const { activeSession, loading, activate, endSession } = useActiveSession();
    const { selectedSessionId, setSelectedSessionId } = useSession();
    const { events: rollEvents } = useRollSession();

    // State to track if shop is explicitly "opened" by GM command (local approximation)
    const [shopActive, setShopActive] = useState(false);

    const [creating, setCreating] = useState(false);
    const [gmName, setGmName] = useState<string | null>(null);
    const [overviewName, setOverviewName] = useState<string | null>(null);
    const [overviewSystem, setOverviewSystem] = useState<CampaignSystemType | null>(null);
    const [overviewJoinCode, setOverviewJoinCode] = useState<string | null>(null);
    const [overviewError, setOverviewError] = useState<string | null>(null);
    const [commandSending, setCommandSending] = useState(false);
    const [rollExpression, setRollExpression] = useState("d20");
    const [showStartModal, setShowStartModal] = useState(false);

    const rollOptions = useMemo(
        () => ["d4", "d6", "d8", "d10", "d12", "d20"],
        []
    );

    const effectiveCampaignId = campaignId ?? selectedCampaignId ?? null;

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
                setOverviewJoinCode((data as { joinCode?: string | null }).joinCode ?? null);
                setOverviewError(null);
            })
            .catch((error: { message?: string }) => {
                setGmName(null);
                setOverviewName(null);
                setOverviewSystem(null);
                setOverviewJoinCode(null);
                setOverviewError(error?.message ?? "Failed to load campaign");
            });
    }, [effectiveCampaignId]);

    useEffect(() => {
        if (!activeSession?.id) return;
        if (selectedSessionId !== activeSession.id) {
            setSelectedSessionId(activeSession.id);
        }
    }, [activeSession?.id, selectedSessionId, setSelectedSessionId]);

    const handleActivateClick = () => setShowStartModal(true);

    const handleConfirmStart = async (name: string, _date: string) => {
        if (creating) return;
        setCreating(true);
        try {
            const session = await activate(name);
            if (session?.id) setSelectedSessionId(session.id);
            setShowStartModal(false);
        } finally {
            setCreating(false);
        }
    };

    const handleEndSession = async () => {
        if (!confirm(t("session.confirmEnd") ?? "Are you sure you want to end this session?")) return;
        await endSession();
        setShopActive(false);
    };

    const handleCommand = async (
        type: "open_shop" | "close_shop" | "request_roll",
        payload?: Record<string, unknown>
    ) => {
        if (!activeSession?.id || commandSending) return;
        setCommandSending(true);
        try {
            await sessionsRepo.command(activeSession.id, {
                type,
                payload: {
                    ...(payload ?? {}),
                },
            });
            if (type === "open_shop") setShopActive(true);
            if (type === "close_shop") setShopActive(false);
        } finally {
            setCommandSending(false);
        }
    };

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
                    {effectiveCampaignId && (
                        <Link
                            to={routes.campaignSessions.replace(":campaignId", effectiveCampaignId)}
                            className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-300 hover:border-slate-500 hover:text-white"
                        >
                            Back to sessions
                        </Link>
                    )}
                    {overviewJoinCode && (
                        <span className="rounded-full border border-limiar-500/40 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-limiar-200">
                            Campaign code {overviewJoinCode}
                        </span>
                    )}
                </div>
            </header>

            {/* Session Management */}
            <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
                <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg font-semibold text-white">Session Status</h2>
                        {activeSession && (
                            <div className="flex items-center gap-3">
                                <button
                                    onClick={handleEndSession}
                                    className="rounded-full border border-red-500/30 bg-red-500/10 px-3 py-1 text-xs font-semibold text-red-400 hover:bg-red-500/20"
                                >
                                    End Session
                                </button>
                                <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/20">
                                    LIVE
                                </span>
                            </div>
                        )}
                    </div>

                    <div className="mt-6 flex flex-col items-center justify-center space-y-4 rounded-2xl bg-slate-950/50 py-10 border border-slate-800/50">
                        {loading ? (
                            <span className="text-slate-400">Loading session...</span>
                        ) : activeSession ? (
                            <>
                                <h3 className="text-2xl font-bold text-white">{activeSession.title || "Untitled Session"}</h3>
                                <div className="text-4xl font-mono text-limiar-400">
                                    <SessionTimer startedAt={activeSession.startedAt ?? activeSession.createdAt} />
                                </div>
                                <div className="flex gap-2 text-sm text-slate-500">
                                    <span>#{activeSession.number}</span>
                                    <span>·</span>
                                    <span>Join Code: <span className="text-slate-300 font-mono select-all cursor-pointer">{activeSession.joinCode}</span></span>
                                </div>
                            </>
                        ) : (
                            <>
                                <p className="text-slate-400 mb-2">No active session</p>
                                <button
                                    onClick={handleActivateClick}
                                    disabled={creating}
                                    className="rounded-full bg-limiar-500 px-8 py-3 text-sm font-bold uppercase tracking-widest text-white shadow-lg shadow-limiar-500/20 hover:bg-limiar-400 disabled:opacity-50 transition-all active:scale-95"
                                >
                                    Start Session
                                </button>
                            </>
                        )}
                    </div>

                    {/* Session Actions */}
                    {activeSession && (
                        <div className="mt-6 grid gap-4 lg:grid-cols-2">
                            <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-950/60 to-slate-900/40 p-4">
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
                                        className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${shopActive
                                            ? "border-emerald-500/40 text-emerald-300"
                                            : "border-slate-700 text-slate-400"
                                            }`}
                                    >
                                        {shopActive ? "Live" : "Closed"}
                                    </span>
                                </div>
                                <button
                                    onClick={() => handleCommand(shopActive ? "close_shop" : "open_shop")}
                                    disabled={commandSending}
                                    className={`mt-4 w-full rounded-2xl px-4 py-3 text-xs font-semibold uppercase tracking-[0.25em] transition-colors ${shopActive
                                        ? "bg-rose-900/40 text-rose-200 hover:bg-rose-900/60"
                                        : "bg-limiar-500/80 text-white hover:bg-limiar-500"
                                        }`}
                                >
                                    {shopActive ? "Close Shop" : "Open Shop"}
                                </button>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-950/60 to-slate-900/40 p-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-500">
                                            Dice Request
                                        </label>
                                        <p className="mt-1 text-xs text-slate-400">
                                            Choose a die and request a roll.
                                        </p>
                                    </div>
                                </div>
                                <div className="mt-4 flex flex-wrap items-center gap-3">
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
                                    <button
                                        onClick={() => handleCommand("request_roll", { expression: rollExpression })}
                                        disabled={commandSending}
                                        className="rounded-2xl bg-slate-800 px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-slate-200 hover:bg-slate-700"
                                    >
                                        Request Roll
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Quick Actions Grid */}
                <div className="grid gap-4 content-start">
                    <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
                        <h2 className="text-lg font-semibold text-white mb-4">Management</h2>
                        <div className="grid gap-3">
                            <Link
                                to={routes.npcs}
                                className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3 text-sm font-semibold text-slate-200 hover:border-limiar-500/50 hover:bg-slate-900 transition-colors group"
                            >
                                <span>NPCs & Bestiary</span>
                                <span className="text-limiar-500 opacity-0 group-hover:opacity-100 transition-opacity">→</span>
                            </Link>
                            <Link
                                to={routes.catalog}
                                className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3 text-sm font-semibold text-slate-200 hover:border-limiar-500/50 hover:bg-slate-900 transition-colors group"
                            >
                                <span>Item Catalog</span>
                                <span className="text-limiar-500 opacity-0 group-hover:opacity-100 transition-opacity">→</span>
                            </Link>
                            <Link
                                to={routes.shop}
                                className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3 text-sm font-semibold text-slate-200 hover:border-limiar-500/50 hover:bg-slate-900 transition-colors group"
                            >
                                <span>Manage Shop</span>
                                <span className="text-limiar-500 opacity-0 group-hover:opacity-100 transition-opacity">→</span>
                            </Link>
                            <Link
                                to={routes.inventory}
                                className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3 text-sm font-semibold text-slate-200 hover:border-limiar-500/50 hover:bg-slate-900 transition-colors group"
                            >
                                <span>Party Inventory</span>
                                <span className="text-limiar-500 opacity-0 group-hover:opacity-100 transition-opacity">→</span>
                            </Link>
                        </div>
                    </div>
                </div>
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
