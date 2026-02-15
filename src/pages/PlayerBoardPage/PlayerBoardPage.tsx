import { useEffect, useMemo, useRef, useState } from "react";
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

type PendingRoll = {
  expression: string;
  issuedBy?: string;
};

export const PlayerBoardPage = () => {
  const { t } = useLocale();
  const { campaignId } = useParams<{ campaignId: string }>();
  const { selectedCampaign, selectedCampaignId, setSelectedCampaignLocal } = useCampaigns();
  const { activeSession, refresh } = useActiveSession(campaignId);
  const { selectedSessionId, setSelectedSessionId } = useSession();
  const { lastCommand, clearCommand, sessionEndedAt, clearSessionEnded } = useSessionCommands();
  const { lastEvent } = useCampaignEvents(campaignId);
  const { roll, events: rollEvents } = useRollSession();
  const { toast, showToast, clearToast } = useToast();
  const [pendingRoll, setPendingRoll] = useState<PendingRoll | null>(null);
  const [shopOpen, setShopOpen] = useState(false);
  const [pendingOpenShop, setPendingOpenShop] = useState(false);
  const [shopSessionTarget, setShopSessionTarget] = useState<string | null>(null);
  const navigate = useNavigate();
  const redirectTimeoutRef = useRef<number | null>(null);
  const effectiveCampaignId = campaignId ?? selectedCampaignId ?? activeSession?.campaignId ?? null;

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
      refresh().catch(() => {});
    }, 10000);
    return () => window.clearInterval(handle);
  }, [effectiveCampaignId, activeSession, refresh]);

  useEffect(() => {
    if (!lastCommand) {
      return;
    }
    if (lastCommand.command === "request_roll") {
      const expression = String(lastCommand.data?.expression ?? "d20");
      setPendingRoll({
        expression,
        issuedBy: lastCommand.issuedBy,
      });
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
  }, [lastCommand, activeSession?.id, selectedCampaignId, setSelectedCampaignLocal]);

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
      refresh().catch(() => {});
    }
    if (lastEvent.type === "session_closed") {
      refresh().catch(() => {});
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
    refresh().catch(() => {});
    if (redirectTimeoutRef.current) {
      window.clearTimeout(redirectTimeoutRef.current);
    }
    redirectTimeoutRef.current = window.setTimeout(() => {
      clearSessionEnded();
      navigate(routes.playerHome);
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
    roll(pendingRoll.expression);
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
        className={`grid gap-6 ${
          shopOpen ? "lg:grid-cols-[1.6fr_1fr]" : "lg:grid-cols-[1fr]"
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
                    onClick={() => setShopOpen(true)}
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
            <h2 className="mt-3 text-2xl font-semibold">
              {pendingRoll.expression.toUpperCase()}
            </h2>
            {pendingRoll.issuedBy && (
              <p className="mt-2 text-sm text-slate-300">
                {t("playerBoard.requestedBy")} {pendingRoll.issuedBy}
              </p>
            )}
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleRoll}
                className="flex-1 rounded-full bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white"
              >
                {t("playerBoard.rollNow")}
              </button>
              <button
                type="button"
                onClick={() => {
                  setPendingRoll(null);
                  clearCommand();
                }}
                className="rounded-full border border-slate-700 px-4 py-3 text-xs uppercase tracking-[0.2em] text-slate-300"
              >
                {t("playerBoard.dismiss")}
              </button>
            </div>
          </div>
        </div>
      )}
      <DiceVisualizer events={rollEvents} />

    </section>
  );
};
