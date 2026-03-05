import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useLocale } from "../../shared/hooks/useLocale";
import { useCampaigns } from "../../features/campaign-select";
import { ShopPanel } from "../../features/shop";
import { useActiveSession, useCampaignEvents, useSession, useSessionCommands } from "../../features/sessions";
import { routes } from "../../app/routes/routes";
import { useRollSession } from "../../features/dice-roller";
import { DiceVisualizer } from "../../features/dice-roller/components/DiceVisualizer";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";
import { partiesRepo } from "../../shared/api/partiesRepo";
import { sessionsRepo } from "../../shared/api/sessionsRepo";
import { inventoryRepo } from "../../shared/api/inventoryRepo";
import { itemsRepo } from "../../shared/api/itemsRepo";
import { useAuth } from "../../features/auth";
import type { InventoryItem } from "../../entities/inventory";
import type { Item } from "../../entities/item";
import type { ActivityEvent } from "../../shared/api/sessionsRepo";

function formatOffset(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h${String(m).padStart(2, "0")}m`;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function ActivityRow({ event }: { event: ActivityEvent }) {
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
          {event.label && <p className="text-xs text-slate-400 mt-0.5">{event.label}</p>}
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

type PendingRoll = {
  expression: string;
  issuedBy?: string;
  reason?: string;
  mode?: "advantage" | "disadvantage" | null;
};

export const PlayerBoardPage = () => {
  const { t } = useLocale();
  const { user } = useAuth();
  const { partyId } = useParams<{ partyId: string }>();
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const { selectedCampaign, selectedCampaignId, setSelectedCampaignLocal } = useCampaigns();

  useEffect(() => {
    if (!partyId) return;
    partiesRepo.get(partyId)
      .then((party) => setCampaignId(party.campaignId))
      .catch(() => {});
  }, [partyId]);
  const { activeSession, refresh } = useActiveSession(campaignId);
  const { selectedSessionId, setSelectedSessionId } = useSession();
  const { lastCommand, clearCommand, sessionEndedAt, clearSessionEnded } = useSessionCommands();
  const { lastEvent } = useCampaignEvents(campaignId);
  const { roll, events: rollEvents } = useRollSession();
  const { toast, showToast, clearToast } = useToast();
  const [pendingRoll, setPendingRoll] = useState<PendingRoll | null>(null);
  const [rollMode, setRollMode] = useState<"virtual" | "manual" | null>(null);
  const [manualValue, setManualValue] = useState("");
  const [shopOpen, setShopOpen] = useState(false);
  const [pendingOpenShop, setPendingOpenShop] = useState(false);
  const [shopSessionTarget, setShopSessionTarget] = useState<string | null>(null);
  const [myInventory, setMyInventory] = useState<InventoryItem[] | null>(null);
  const [catalogItems, setCatalogItems] = useState<Record<string, Item>>({});
  const [inventoryOpen, setInventoryOpen] = useState(false);
  const [activityFeed, setActivityFeed] = useState<ActivityEvent[]>([]);
  const activityIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const navigate = useNavigate();
  const redirectTimeoutRef = useRef<number | null>(null);
  const effectiveCampaignId = campaignId ?? selectedCampaignId ?? activeSession?.campaignId ?? null;

  useEffect(() => {
    if (!campaignId) return;
    Promise.all([
      inventoryRepo.list(campaignId),
      itemsRepo.list(campaignId),
    ]).then(([inv, items]) => {
      const itemMap: Record<string, Item> = {};
      for (const it of items) itemMap[it.id] = it;
      setCatalogItems(itemMap);
      setMyInventory(inv);
    }).catch(() => { setMyInventory([]); });
  }, [campaignId]);

  const refreshActivity = useCallback(async () => {
    if (!activeSession?.id) return;
    try {
      const events = await sessionsRepo.getActivity(activeSession.id);
      setActivityFeed(events);
    } catch { /* ignore */ }
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
    if (campaignId && selectedCampaignId !== campaignId) {
      setSelectedCampaignLocal(campaignId);
    }
    if (!activeSession?.id) {
      return;
    }
    if (selectedSessionId !== activeSession.id) {
      setSelectedSessionId(activeSession.id);
    }
    if (!selectedCampaignId && activeSession.campaignId) {
      setSelectedCampaignLocal(activeSession.campaignId);
    }
  }, [campaignId, selectedCampaignId, activeSession?.id, selectedSessionId, setSelectedSessionId, setSelectedCampaignLocal]);

  useEffect(() => {
    if (!effectiveCampaignId) {
      return;
    }
    if (!activeSession && selectedSessionId) {
      setSelectedSessionId(null);
    }
  }, [activeSession, effectiveCampaignId, selectedSessionId, setSelectedSessionId]);

  useEffect(() => {
    if (!effectiveCampaignId) {
      return;
    }
    if (activeSession) {
      return;
    }
    const handle = window.setInterval(() => {
      refresh().catch(() => { });
    }, 10000);
    return () => window.clearInterval(handle);
  }, [effectiveCampaignId, activeSession, refresh]);

  useEffect(() => {
    if (!lastCommand) {
      return;
    }
    if (lastCommand.command === "request_roll") {
      const targetUserId = lastCommand.data?.targetUserId as string | undefined;
      if (targetUserId && targetUserId !== user?.userId) {
        return; // not for this player
      }
      const expression = String(lastCommand.data?.expression ?? "d20");
      const reason = lastCommand.data?.reason as string | undefined;
      const mode = (lastCommand.data?.mode ?? null) as "advantage" | "disadvantage" | null;
      setPendingRoll({ expression, issuedBy: lastCommand.issuedBy, reason, mode });
      setRollMode(null);
      setManualValue("");
    }
    if (lastCommand.command === "open_shop") {
      const commandCampaignId = lastCommand.data?.campaignId as string | undefined;
      if (commandCampaignId && !selectedCampaignId) {
        setSelectedCampaignLocal(commandCampaignId);
      }
      const targetSessionId = String(
        (lastCommand.data?.sessionId as string | undefined) ?? activeSession?.id ?? ""
      );
      if (!activeSession?.id) {
        setPendingOpenShop(true);
        setShopSessionTarget(targetSessionId || null);
        return;
      }
      if (targetSessionId && targetSessionId !== activeSession.id) {
        return;
      }
      setShopSessionTarget(activeSession.id);
      setShopOpen(true);
    }
    if (lastCommand.command === "close_shop") {
      setShopOpen(false);
      setPendingOpenShop(false);
      setShopSessionTarget(null);
    }
  }, [lastCommand, activeSession?.id, selectedCampaignId, setSelectedCampaignLocal, user]);

  useEffect(() => {
    if (!pendingOpenShop || !activeSession?.id) {
      return;
    }
    if (shopSessionTarget && shopSessionTarget !== activeSession.id) {
      setPendingOpenShop(false);
      setShopSessionTarget(null);
      return;
    }
    setShopSessionTarget(activeSession.id);
    setShopOpen(true);
    setPendingOpenShop(false);
  }, [pendingOpenShop, activeSession?.id, shopSessionTarget]);

  useEffect(() => {
    if (!lastEvent) return;
    refreshActivity();
  }, [lastEvent, refreshActivity]);

  useEffect(() => {
    if (!lastEvent) {
      return;
    }
    if (lastEvent.type === "session_started" || lastEvent.type === "session_resumed") {
      showToast({
        variant: "info",
        title: t("playerBoard.sessionStartedTitle"),
        description: t("playerBoard.sessionStartedDescription"),
        duration: 3000,
      });
      refresh().catch(() => { });
    }
    if (lastEvent.type === "session_closed") {
      refresh().catch(() => { });
    }
  }, [lastEvent, refresh, showToast, t]);

  useEffect(() => {
    if (!sessionEndedAt) {
      return;
    }
    setShopOpen(false);
    setPendingRoll(null);
    setSelectedSessionId(null);
    showToast({
      variant: "success",
      title: t("playerBoard.sessionEndedTitle"),
      description: t("playerBoard.sessionEndedDescription"),
      duration: 3500,
    });
    refresh().catch(() => { });
    if (redirectTimeoutRef.current) {
      window.clearTimeout(redirectTimeoutRef.current);
    }
    redirectTimeoutRef.current = window.setTimeout(() => {
      clearSessionEnded();
      navigate(routes.home);
      redirectTimeoutRef.current = null;
    }, 3200);
  }, [
    sessionEndedAt,
    setSelectedSessionId,
    clearSessionEnded,
    refresh,
    showToast,
    t,
    navigate,
  ]);

  useEffect(() => {
    return () => {
      if (redirectTimeoutRef.current) {
        window.clearTimeout(redirectTimeoutRef.current);
      }
    };
  }, []);

  const campaignTitle = useMemo(() => {
    if (selectedCampaign) {
      return selectedCampaign.name;
    }
    return t("playerBoard.noCampaign");
  }, [selectedCampaign, t]);

  const handleRoll = () => {
    if (!pendingRoll) {
      return;
    }
    roll(pendingRoll.expression, pendingRoll.reason, pendingRoll.mode);
    setPendingRoll(null);
    clearCommand();
  };

  const handleShopClose = () => {
    setShopOpen(false);
    clearCommand();
  };

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />
      <header className="rounded-3xl border border-slate-800 bg-gradient-to-br from-void-950 via-slate-950/80 to-limiar-900/30 p-6">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400 hover:text-slate-200"
        >
          ← Voltar
        </button>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
          {t("playerBoard.subtitle")}
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-white">{campaignTitle}</h1>
        <p className="mt-2 text-sm text-slate-300">
          {effectiveCampaignId
            ? activeSession
              ? t("playerBoard.readyHint")
              : t("playerBoard.waitingSession")
            : t("playerBoard.noCampaignHint")}
        </p>
        {!effectiveCampaignId && (
          <div className="mt-4">
            <a
              href={routes.join}
              className="inline-flex items-center rounded-full bg-limiar-500 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white"
            >
              {t("playerBoard.goJoin")}
            </a>
          </div>
        )}
      </header>

      <div
        className={`grid gap-6 ${shopOpen ? "lg:grid-cols-[1.6fr_1fr]" : "lg:grid-cols-[1fr]"
          }`}
      >
        <div className="space-y-6">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
            <h2 className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-400">
              {t("playerBoard.activityTitle")}
            </h2>
            <div className="mt-4 rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-950/80 to-slate-900/50 p-5 text-sm text-slate-200">
              {lastCommand?.command === "open_shop" && (
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span>{t("playerBoard.shopPrompt")}</span>
                  <button
                    type="button"
                    onClick={() => { setShopOpen(true); clearCommand(); }}
                    className="rounded-full bg-limiar-500 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white"
                  >
                    {t("playerBoard.goShop")}
                  </button>
                </div>
              )}
              {lastCommand?.command !== "open_shop" && !pendingRoll && (
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-4 text-slate-300">
                  {t("playerBoard.noCommands")}
                </div>
              )}
            </div>
          </div>
        </div>

        {shopOpen && activeSession?.id && effectiveCampaignId && (
          <div className="lg:sticky lg:top-24">
            <ShopPanel
              open={shopOpen}
              onClose={handleShopClose}
              sessionId={activeSession.id}
              campaignId={effectiveCampaignId}
              onBuy={() =>
                showToast({
                  variant: "success",
                  title: t("shop.buyTitle"),
                  description: t("shop.buyFallback"),
                })
              }
              onBuyError={() =>
                showToast({
                  variant: "error",
                  title: t("shop.buyErrorTitle"),
                  description: t("shop.buyErrorDescription"),
                })
              }
            />
          </div>
        )}
      </div>

      {pendingRoll && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4">
          <div className="w-full max-w-md rounded-3xl border border-limiar-400/30 bg-void-950 p-6 text-slate-100 shadow-2xl shadow-limiar-900/40">
            <p className="text-xs uppercase tracking-[0.3em] text-limiar-200">
              {t("playerBoard.rollRequest")}
            </p>
            {pendingRoll.reason && (
              <p className="mt-2 text-base font-semibold text-white">{pendingRoll.reason}</p>
            )}
            <div className={`flex items-center gap-3 ${pendingRoll.reason ? "mt-1" : "mt-3"}`}>
              <h2 className="text-2xl font-semibold text-limiar-300">
                {pendingRoll.expression.toUpperCase()}
              </h2>
              {pendingRoll.mode === "advantage" && (
                <span className="rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-emerald-400">
                  Advantage
                </span>
              )}
              {pendingRoll.mode === "disadvantage" && (
                <span className="rounded-full bg-red-500/15 border border-red-500/30 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-red-400">
                  Disadvantage
                </span>
              )}
            </div>
            {pendingRoll.issuedBy && (
              <p className="mt-2 text-sm text-slate-400">
                {t("playerBoard.requestedBy")} {pendingRoll.issuedBy}
              </p>
            )}

            {rollMode === null && (
              <div className="mt-5 grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setRollMode("virtual")}
                  className="rounded-2xl bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-limiar-400"
                >
                  🎲 Virtual
                </button>
                <button
                  type="button"
                  onClick={() => setRollMode("manual")}
                  className="rounded-2xl border border-slate-600 bg-slate-800 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-700"
                >
                  ✍️ Manual
                </button>
              </div>
            )}

            {rollMode === "virtual" && (
              <div className="mt-5 flex gap-3">
                <button
                  type="button"
                  onClick={handleRoll}
                  className="flex-1 rounded-full bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white"
                >
                  {t("playerBoard.rollNow")}
                </button>
                <button type="button" onClick={() => setRollMode(null)} className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400">
                  ←
                </button>
              </div>
            )}

            {rollMode === "manual" && (
              <div className="mt-5 space-y-3">
                {pendingRoll.mode && (
                  <p className="text-xs text-slate-400">
                    {pendingRoll.mode === "advantage"
                      ? "Role 2 dados e insira o maior resultado."
                      : "Role 2 dados e insira o menor resultado."}
                  </p>
                )}
                <label className="text-xs uppercase tracking-widest text-slate-400">Resultado obtido</label>
                <input
                  type="number"
                  min={1}
                  value={manualValue}
                  onChange={(e) => setManualValue(e.target.value)}
                  placeholder="Ex: 17"
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-center text-2xl font-bold text-white focus:border-limiar-500 focus:outline-none"
                  autoFocus
                />
                <div className="flex gap-3">
                  <button
                    type="button"
                    disabled={!manualValue || isNaN(Number(manualValue))}
                    onClick={async () => {
                      if (!activeSession?.id || !manualValue) return;
                      await sessionsRepo.manualRoll(activeSession.id, {
                        expression: pendingRoll.expression,
                        result: Number(manualValue),
                        label: pendingRoll.reason ?? null,
                      });
                      setPendingRoll(null);
                      setRollMode(null);
                      setManualValue("");
                      clearCommand();
                    }}
                    className="flex-1 rounded-full bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
                  >
                    Confirmar
                  </button>
                  <button type="button" onClick={() => setRollMode(null)} className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400">
                    ←
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      <DiceVisualizer events={rollEvents} />

      {/* Activity Feed */}
      {activeSession && (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
          <h2 className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-400 mb-4">
            Session Activity
          </h2>
          {activityFeed.length === 0 ? (
            <p className="text-sm text-slate-500">No activity yet.</p>
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {[...activityFeed].reverse().map((ev, i) => (
                <ActivityRow key={i} event={ev} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Inventory Panel */}
      <div className="rounded-3xl border border-slate-800 bg-slate-950/60 overflow-hidden">
        <button
          type="button"
          onClick={() => setInventoryOpen(v => !v)}
          className="w-full flex items-center justify-between p-6 hover:bg-slate-900/20 transition-colors"
        >
          <h2 className="text-sm font-bold uppercase tracking-[0.3em] text-slate-400 flex items-center gap-3">
            <span className="w-1 h-4 bg-amber-500 rounded-full" />
            {t("playerBoard.inventoryTitle") || "My Inventory"}
            {myInventory !== null && (
              <span className="text-xs font-normal text-slate-500 normal-case tracking-normal">
                ({myInventory.length})
              </span>
            )}
          </h2>
          <span className={`text-slate-500 text-xs transition-transform ${inventoryOpen ? "rotate-180" : ""}`}>▼</span>
        </button>
        {inventoryOpen && (
          <div className="px-6 pb-6 border-t border-slate-800/60">
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
                      {catalogItems[item.itemId]?.type && (
                        <p className="text-xs text-slate-500">{catalogItems[item.itemId]?.type}</p>
                      )}
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

    </section>
  );
};
