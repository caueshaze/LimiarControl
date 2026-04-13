import { useEffect, useRef, useState } from "react";
import { routes } from "../../app/routes/routes";
import { isRollEventKnown } from "../../features/rolls/knownRollEvents";
import { usePlayerBoardRollRequests } from "./usePlayerBoardRollRequests";
import type { UsePlayerBoardRealtimeProps } from "./player-board-realtime.types";

export const usePlayerBoardRealtime = ({
  activeSession,
  clearCommand,
  clearSessionEnded,
  effectiveCampaignId,
  lastCommand,
  lastEvent,
  navigate,
  partyId,
  refresh,
  refreshInventoryData,
  roll,
  selectedCampaignId,
  sessionEndedAt,
  setSelectedCampaignLocal,
  setSelectedSessionId,
  showToast,
  shopAvailable,
  t,
  userId = null,
}: UsePlayerBoardRealtimeProps) => {
  const [shopOpen, setShopOpen] = useState(false);
  const [pendingOpenShop, setPendingOpenShop] = useState(false);
  const [shopSessionTarget, setShopSessionTarget] = useState<string | null>(null);
  const [inventoryOpen, setInventoryOpen] = useState(false);
  const [inventoryFlash, setInventoryFlash] = useState(false);
  const redirectTimeoutRef = useRef<number | null>(null);
  const prevActiveSessionIdRef = useRef<string | null>(null);
  const handledLastEventRef = useRef(lastEvent);
  const navigateBackToParty = (replace = false) => {
    navigate(
      partyId
        ? routes.playerPartyDetails.replace(":partyId", partyId)
        : routes.home,
      replace ? { replace: true } : undefined,
    );
  };
  const {
    clearPendingRoll,
    handleAuthoritativeRollResolved,
    handleManualRoll,
    handleRoll,
    manualValue,
    pendingRoll,
    rollMode,
    setManualValue,
    setRollMode,
  } = usePlayerBoardRollRequests({
    activeSessionId: activeSession?.id ?? null,
    clearCommand,
    lastCommand,
    lastEvent,
    roll,
    showToast,
    t,
    userId,
  });

  useEffect(() => {
    if (activeSession?.id) {
      prevActiveSessionIdRef.current = activeSession.id;
    } else if (prevActiveSessionIdRef.current && effectiveCampaignId) {
      prevActiveSessionIdRef.current = null;
      navigateBackToParty(true);
    }
  }, [activeSession?.id, effectiveCampaignId, navigate, partyId]);
  useEffect(() => {
    if (!lastCommand) return;
    if (lastCommand.command === "open_shop") {
      const commandCampaignId = lastCommand.data?.campaignId as string | undefined;
      if (commandCampaignId && !selectedCampaignId) {
        setSelectedCampaignLocal(commandCampaignId);
      }
      const targetSessionId = String(
        (lastCommand.data?.sessionId as string | undefined) ?? activeSession?.id ?? "",
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
  }, [activeSession?.id, lastCommand, selectedCampaignId, setSelectedCampaignLocal]);

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
  }, [activeSession?.id, pendingOpenShop, shopSessionTarget]);

  useEffect(() => {
    if (shopAvailable) {
      setShopOpen(true);
    }
  }, [shopAvailable]);

  useEffect(() => {
    if (!shopAvailable && lastCommand?.command !== "open_shop" && !pendingOpenShop) {
      setShopOpen(false);
    }
  }, [shopAvailable, lastCommand?.command, pendingOpenShop]);
  useEffect(() => {
    if (!lastEvent) return;
    if (handledLastEventRef.current === lastEvent) {
      return;
    }
    handledLastEventRef.current = lastEvent;
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
      refresh().catch(() => {});
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
    if (lastEvent.type === "combat_started") {
      showToast({
        variant: "info",
        title: t("playerBoard.combatStartedTitle"),
        description: t("playerBoard.combatStartedDescription"),
      });
      return;
    }
    if (lastEvent.type === "combat_ended") {
      showToast({
        variant: "info",
        title: t("playerBoard.combatEndedTitle"),
        description: t("playerBoard.combatEndedDescription"),
      });
      return;
    }
    if (lastEvent.type === "shop_purchase_created" || lastEvent.type === "shop_sale_created") {
      const eventUserId =
        typeof lastEvent.payload.userId === "string" ? lastEvent.payload.userId : null;
      if (eventUserId && eventUserId === userId) {
        void refreshInventoryData();
      }
      return;
    }
    if (lastEvent.type === "gm_granted_currency") {
      const eventPlayerUserId =
        typeof lastEvent.payload.playerUserId === "string"
          ? lastEvent.payload.playerUserId
          : null;
      if (eventPlayerUserId && eventPlayerUserId === userId) {
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
      if (eventPlayerUserId && eventPlayerUserId === userId) {
        showToast({
          variant: "success",
          title: "New item received",
          description: `${String(lastEvent.payload.itemName ?? "Item")} added to your inventory.`,
        });
      }
      return;
    }
    if (lastEvent.type === "gm_granted_xp") {
      const eventPlayerUserId =
        typeof lastEvent.payload.playerUserId === "string"
          ? lastEvent.payload.playerUserId
          : null;
      if (eventPlayerUserId && eventPlayerUserId === userId) {
        showToast({
          variant: "success",
          title: "XP received",
          description: `The GM granted ${String(lastEvent.payload.grantedAmount ?? 0)} XP.`,
        });
      }
      return;
    }
    if (lastEvent.type === "level_up_approved") {
      const eventPlayerUserId =
        typeof lastEvent.payload.playerUserId === "string"
          ? lastEvent.payload.playerUserId
          : null;
      if (eventPlayerUserId && eventPlayerUserId === userId) {
        showToast({
          variant: "success",
          title: "Level-up approved",
          description: "Your character sheet has been updated.",
        });
      }
      return;
    }
    if (lastEvent.type === "level_up_denied") {
      const eventPlayerUserId =
        typeof lastEvent.payload.playerUserId === "string"
          ? lastEvent.payload.playerUserId
          : null;
      if (eventPlayerUserId && eventPlayerUserId === userId) {
        showToast({
          variant: "info",
          title: "Level-up denied",
          description: "The GM cleared your pending request.",
        });
      }
      return;
    }
    if (lastEvent.type === "roll_resolved") {
      const p = lastEvent.payload;
      if (!isRollEventKnown(String(p.event_id ?? ""))) {
        showToast({
          variant: "info",
          title: `${String(p.actor_display_name ?? "")}: ${String(p.roll_type ?? "")}`,
          description: `${String(p.formula ?? "")} = ${String(p.total ?? 0)}${p.success === true ? " ✓" : p.success === false ? " ✗" : ""}`,
          duration: 4000,
        });
      }
      return;
    }
    if (lastEvent.type === "session_closed") {
      setShopOpen(false);
      setPendingOpenShop(false);
      setShopSessionTarget(null);
      clearPendingRoll();
      setSelectedSessionId(null);
      clearSessionEnded();
      if (redirectTimeoutRef.current) {
        window.clearTimeout(redirectTimeoutRef.current);
        redirectTimeoutRef.current = null;
      }
      navigateBackToParty(true);
    }
  }, [
    activeSession?.id,
    clearPendingRoll,
    clearSessionEnded,
    lastEvent,
    navigate,
    partyId,
    refresh,
    refreshInventoryData,
    setSelectedSessionId,
    showToast,
    t,
    userId,
  ]);

  useEffect(() => {
    if (!sessionEndedAt) {
      return;
    }
    setShopOpen(false);
    clearPendingRoll();
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
      navigateBackToParty();
      redirectTimeoutRef.current = null;
    }, 3200);
  }, [
    clearPendingRoll,
    clearSessionEnded,
    navigate,
    refresh,
    sessionEndedAt,
    setSelectedSessionId,
    showToast,
    t,
    partyId,
  ]);

  useEffect(() => {
    return () => {
      if (redirectTimeoutRef.current) window.clearTimeout(redirectTimeoutRef.current);
    };
  }, []);

  const handleShopClose = () => {
    setShopOpen(false);
    clearCommand();
  };

  const handleOpenShop = () => {
    setShopOpen(true);
    clearCommand();
  };

  return {
    clearPendingRoll,
    handleAuthoritativeRollResolved,
    handleManualRoll,
    handleOpenShop,
    handleRoll,
    handleShopClose,
    inventoryFlash,
    inventoryOpen,
    manualValue,
    pendingRoll,
    rollMode,
    setInventoryFlash,
    setInventoryOpen,
    setManualValue,
    setRollMode,
    shopOpen,
  };
};
