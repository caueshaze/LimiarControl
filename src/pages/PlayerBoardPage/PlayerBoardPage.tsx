import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useLocale } from "../../shared/hooks/useLocale";
import { useCampaigns } from "../../features/campaign-select";
import { ShopPanel } from "../../features/shop";
import { SessionInventoryPanel } from "../../features/inventory";
import {
  SessionActivityToggle,
  useCampaignEvents,
  usePartyActiveSession,
  useSession,
  useSessionCommands,
} from "../../features/sessions";
import { routes } from "../../app/routes/routes";
import { useRollSession } from "../../features/dice-roller";
import { DiceVisualizer } from "../../features/dice-roller/components/DiceVisualizer";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";
import { partiesRepo } from "../../shared/api/partiesRepo";
import { sessionsRepo } from "../../shared/api/sessionsRepo";
import { inventoryRepo } from "../../shared/api/inventoryRepo";
import { itemsRepo } from "../../shared/api/itemsRepo";
import { sessionStatesRepo } from "../../shared/api/sessionStatesRepo";
import { useAuth } from "../../features/auth";
import type { InventoryItem } from "../../entities/inventory";
import type { Item } from "../../entities/item";
import type { CurrencyWallet } from "../../shared/api/inventoryRepo";
import { EMPTY_WALLET, normalizeWallet } from "../../features/shop/utils/shopCurrency";

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
  const { activeSession, refresh } = usePartyActiveSession(partyId);
  const effectiveCampaignId = campaignId ?? selectedCampaignId ?? activeSession?.campaignId ?? null;
  const { selectedSessionId, setSelectedSessionId } = useSession();
  const { lastCommand, clearCommand, sessionEndedAt, clearSessionEnded, shopOpen: shopAvailable } = useSessionCommands();
  const { lastEvent } = useCampaignEvents(effectiveCampaignId);
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
  const [playerWallet, setPlayerWallet] = useState<CurrencyWallet | null>(null);
  const [inventoryOpen, setInventoryOpen] = useState(false);
  const [inventoryFlash, setInventoryFlash] = useState(false);
  const navigate = useNavigate();
  const redirectTimeoutRef = useRef<number | null>(null);
  const prevActiveSessionIdRef = useRef<string | null>(null);

  const refreshInventoryData = useCallback(async () => {
    if (!effectiveCampaignId) {
      setMyInventory([]);
      return;
    }
    try {
      const inventory = await inventoryRepo.list(effectiveCampaignId, null, partyId);
      setMyInventory(inventory);
    } catch {
      setMyInventory([]);
    }
  }, [effectiveCampaignId, partyId]);

  const refreshPlayerWallet = useCallback(async () => {
    if (!activeSession?.id) {
      setPlayerWallet(null);
      return;
    }
    try {
      const record = await sessionStatesRepo.getMine(activeSession.id);
      const nextWallet = normalizeWallet(
        (record.state as { currency?: unknown } | null | undefined)?.currency
      );
      setPlayerWallet(nextWallet);
    } catch {
      setPlayerWallet(EMPTY_WALLET);
    }
  }, [activeSession?.id]);

  useEffect(() => {
    if (!effectiveCampaignId) return;
    Promise.all([
      inventoryRepo.list(effectiveCampaignId, null, partyId),
      itemsRepo.list(effectiveCampaignId),
    ]).then(([inv, items]) => {
      const itemMap: Record<string, Item> = {};
      for (const it of items) itemMap[it.id] = it;
      setCatalogItems(itemMap);
      setMyInventory(inv);
    }).catch(() => { setMyInventory([]); });
  }, [effectiveCampaignId, partyId]);

  useEffect(() => {
    void refreshPlayerWallet();
  }, [refreshPlayerWallet]);

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
    const handle = window.setInterval(() => {
      refresh().catch(() => { });
    }, activeSession ? 30_000 : 15_000);
    return () => window.clearInterval(handle);
  }, [effectiveCampaignId, activeSession?.id, refresh]);

  // Fallback redirect: detect when activeSession transitions from active to null
  useEffect(() => {
    if (activeSession?.id) {
      prevActiveSessionIdRef.current = activeSession.id;
    } else if (prevActiveSessionIdRef.current && effectiveCampaignId) {
      prevActiveSessionIdRef.current = null;
      navigate(routes.home, { replace: true });
    }
  }, [activeSession?.id, effectiveCampaignId, navigate]);

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
    if (shopAvailable) {
      setShopOpen(true);
    }
  }, [shopAvailable]);

  useEffect(() => {
    if (!lastEvent) {
      return;
    }
    const eventPartyId =
      typeof lastEvent.payload.partyId === "string" ? lastEvent.payload.partyId : null;
    if (eventPartyId && partyId && eventPartyId !== partyId) {
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
    if (lastEvent.type === "shop_opened") {
      setShopOpen(true);
      return;
    }
    if (lastEvent.type === "shop_closed") {
      setShopOpen(false);
      setPendingOpenShop(false);
      setShopSessionTarget(null);
      return;
    }
    if (lastEvent.type === "roll_requested") {
      const targetUserId =
        typeof lastEvent.payload.targetUserId === "string" ? lastEvent.payload.targetUserId : null;
      if (targetUserId && targetUserId !== user?.userId) {
        return;
      }
      setPendingRoll({
        expression: String(lastEvent.payload.expression ?? "d20"),
        issuedBy: typeof lastEvent.payload.issuedBy === "string" ? lastEvent.payload.issuedBy : undefined,
        reason: typeof lastEvent.payload.reason === "string" ? lastEvent.payload.reason : undefined,
        mode:
          lastEvent.payload.mode === "advantage" || lastEvent.payload.mode === "disadvantage"
            ? lastEvent.payload.mode
            : null,
      });
      setRollMode(null);
      setManualValue("");
      return;
    }
    if (lastEvent.type === "shop_purchase_created") {
      const eventUserId =
        typeof lastEvent.payload.userId === "string" ? lastEvent.payload.userId : null;
      if (eventUserId && eventUserId === user?.userId) {
        void refreshInventoryData();
        void refreshPlayerWallet();
      }
      return;
    }
    if (lastEvent.type === "shop_sale_created") {
      const eventUserId =
        typeof lastEvent.payload.userId === "string" ? lastEvent.payload.userId : null;
      if (eventUserId && eventUserId === user?.userId) {
        void refreshInventoryData();
        void refreshPlayerWallet();
      }
      return;
    }
    if (lastEvent.type === "session_state_updated") {
      const eventPlayerUserId =
        typeof lastEvent.payload.playerUserId === "string"
          ? lastEvent.payload.playerUserId
          : null;
      if (eventPlayerUserId && eventPlayerUserId === user?.userId) {
        void refreshPlayerWallet();
      }
      return;
    }
    if (lastEvent.type === "gm_granted_currency") {
      const eventPlayerUserId =
        typeof lastEvent.payload.playerUserId === "string"
          ? lastEvent.payload.playerUserId
          : null;
      if (eventPlayerUserId && eventPlayerUserId === user?.userId) {
        setPlayerWallet(
          normalizeWallet(
            (lastEvent.payload as { currentCurrency?: unknown } | null | undefined)?.currentCurrency
          )
        );
        showToast({
          variant: "success",
          title: "Coins received",
          description: "The GM added currency to your pouch.",
        });
      }
      return;
    }
    if (lastEvent.type === "gm_granted_item") {
      const eventPlayerUserId =
        typeof lastEvent.payload.playerUserId === "string"
          ? lastEvent.payload.playerUserId
          : null;
      if (eventPlayerUserId && eventPlayerUserId === user?.userId) {
        void refreshInventoryData();
        showToast({
          variant: "success",
          title: "New item received",
          description: `${String(lastEvent.payload.itemName ?? "Item")} added to your inventory.`,
        });
      }
      return;
    }
    if (lastEvent.type === "session_closed") {
      setShopOpen(false);
      setPendingOpenShop(false);
      setShopSessionTarget(null);
      setPendingRoll(null);
      setSelectedSessionId(null);
      clearSessionEnded();
      if (redirectTimeoutRef.current) {
        window.clearTimeout(redirectTimeoutRef.current);
        redirectTimeoutRef.current = null;
      }
      navigate(routes.home, { replace: true });
      return;
    }
  }, [
    lastEvent,
    partyId,
    user?.userId,
    refreshInventoryData,
    refreshPlayerWallet,
    setSelectedSessionId,
    clearSessionEnded,
    navigate,
    refresh,
    showToast,
    t,
  ]);

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

  const upsertInventoryEntry = useCallback((nextEntry: InventoryItem) => {
    setMyInventory((current) => {
      const source = current ?? [];
      const existing = source.find((entry) => entry.id === nextEntry.id);
      if (existing) {
        return source.map((entry) => (entry.id === nextEntry.id ? nextEntry : entry));
      }
      const sameItem = source.find((entry) => entry.itemId === nextEntry.itemId);
      if (sameItem) {
        return source.map((entry) =>
          entry.itemId === nextEntry.itemId
            ? { ...entry, quantity: nextEntry.quantity, isEquipped: nextEntry.isEquipped, notes: nextEntry.notes }
            : entry,
        );
      }
      return [nextEntry, ...source];
    });
  }, []);

  const applySoldInventoryEntry = useCallback((soldInventoryItemId: string, nextEntry: InventoryItem | null) => {
    setMyInventory((current) => {
      const source = current ?? [];
      if (nextEntry) {
        return source.map((entry) => (entry.id === soldInventoryItemId ? nextEntry : entry));
      }
      return source.filter((entry) => entry.id !== soldInventoryItemId);
    });
  }, []);

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />
      <header className="rounded-3xl border border-slate-800 bg-linear-to-br from-void-950 via-slate-950/80 to-limiar-900/30 p-6">
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
        {activeSession?.status === "ACTIVE" && partyId && (
          <div className="mt-4">
            <button
              type="button"
              onClick={() => navigate(`${routes.characterSheetParty.replace(":partyId", partyId)}?mode=play`)}
              className="inline-flex items-center rounded-full border border-limiar-500/30 bg-limiar-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-limiar-300 hover:bg-limiar-500/20"
            >
              Open Play Sheet
            </button>
          </div>
        )}
      </header>

      <div
        className={`grid gap-6 ${shopOpen ? "lg:grid-cols-[1.6fr_1fr]" : "lg:grid-cols-[1fr]"
          }`}
      >
        <div className="space-y-6">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
            <div className="rounded-2xl border border-slate-800 bg-linear-to-br from-slate-950/80 to-slate-900/50 p-5 text-sm text-slate-200">
              {(shopAvailable || lastCommand?.command === "open_shop") && !pendingRoll && !shopOpen && (
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
              {!shopAvailable && lastCommand?.command !== "open_shop" && !pendingRoll && (
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-4 text-slate-300">
                  {t("playerBoard.noCommands")}
                </div>
              )}
            </div>
          </div>

          {activeSession?.id && (
            <SessionActivityToggle
              refreshSignal={lastEvent ? `${lastEvent.type}:${lastEvent.version ?? ""}` : null}
              sessionId={activeSession.id}
            />
          )}
        </div>

        {shopOpen && activeSession?.id && effectiveCampaignId && (
          <div className="lg:sticky lg:top-24">
            <ShopPanel
              open={shopOpen}
              onClose={handleShopClose}
              sessionId={activeSession.id}
              campaignId={effectiveCampaignId}
              inventoryItems={myInventory}
              wallet={playerWallet}
              onBuy={(item, inventoryItem) => {
                upsertInventoryEntry(inventoryItem);
                void refreshInventoryData();
                void refreshPlayerWallet();
                setInventoryOpen(true);
                setInventoryFlash(true);
                window.setTimeout(() => setInventoryFlash(false), 1800);
                showToast({
                  variant: "success",
                  title: t("shop.buyTitle"),
                  description: `${item.name} ${t("shop.buyDescription")}`,
                });
              }}
              onBuyError={(message) =>
                showToast({
                  variant: "error",
                  title: t("shop.buyErrorTitle"),
                  description: message ?? t("shop.buyErrorDescription"),
                })
              }
              onSell={(item, result) => {
                const soldEntry = (myInventory ?? []).find((entry) => entry.itemId === result.itemId);
                if (soldEntry) {
                  applySoldInventoryEntry(soldEntry.id, result.inventoryItem);
                }
                setPlayerWallet(result.currentCurrency);
                setInventoryOpen(true);
                showToast({
                  variant: "success",
                  title: t("shop.sellSuccessTitle"),
                  description: `${item.name} ${t("shop.sellSuccessDescription")} ${result.refundLabel}.`,
                });
              }}
              onSellError={(message) =>
                showToast({
                  variant: "error",
                  title: t("shop.sellErrorTitle"),
                  description: message ?? t("shop.sellErrorDescription"),
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

      <SessionInventoryPanel
        flash={inventoryFlash}
        inventory={myInventory}
        itemsById={catalogItems}
        open={inventoryOpen}
        onToggleOpen={() => setInventoryOpen((value) => !value)}
      />

    </section>
  );
};
