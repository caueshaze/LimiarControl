import { useMemo } from "react";
import type { InventoryItem } from "../../entities/inventory";
import type { LocaleKey } from "../../shared/i18n";
import type { PendingRoll } from "./playerBoard.types";

type ActiveSessionLike = {
  status: "ACTIVE" | "LOBBY" | "CLOSED";
};

type Props = {
  activeSession: ActiveSessionLike | null;
  combatActive: boolean;
  effectiveCampaignId: string | null;
  inventory: InventoryItem[] | null;
  lastCommandType?: string;
  pendingRoll: PendingRoll | null;
  selectedCampaignName?: string | null;
  shopAvailable: boolean;
  shopOpen: boolean;
  t: (key: LocaleKey) => string;
};

export const usePlayerBoardSummary = ({
  activeSession,
  combatActive,
  effectiveCampaignId,
  inventory,
  lastCommandType,
  pendingRoll,
  selectedCampaignName,
  shopAvailable,
  shopOpen,
  t,
}: Props) => {
  const campaignTitle = useMemo(
    () => selectedCampaignName ?? t("playerBoard.noCampaign"),
    [selectedCampaignName, t],
  );

  const inventoryTotal = useMemo(
    () => inventory?.reduce((sum, entry) => sum + entry.quantity, 0) ?? 0,
    [inventory],
  );

  const sessionStatusLabel = useMemo(() => {
    if (activeSession?.status === "ACTIVE") return t("playerBoard.sessionActive");
    if (activeSession?.status === "LOBBY") return t("home.player.statusLobby");
    return t("playerBoard.sessionInactive");
  }, [activeSession?.status, t]);

  const sessionStatusTone = useMemo(() => {
    if (activeSession?.status === "ACTIVE") return "active" as const;
    if (activeSession?.status === "LOBBY") return "lobby" as const;
    return "idle" as const;
  }, [activeSession?.status]);

  const boardDescription = useMemo(() => {
    if (!effectiveCampaignId) return t("playerBoard.noCampaignHint");
    if (!activeSession) return t("playerBoard.waitingSession");
    return t("playerBoard.readyHint");
  }, [activeSession, effectiveCampaignId, t]);

  const commandTitle = useMemo(() => {
    if (pendingRoll) return t("playerBoard.rollRequest");
    if (shopOpen) return t("playerBoard.shopPopoutHeading");
    if (shopAvailable || lastCommandType === "open_shop") return t("playerBoard.shopOpenState");
    if (combatActive) return t("playerBoard.combatStartedTitle");
    if (activeSession) return t("playerBoard.tableWaitingState");
    return effectiveCampaignId ? t("playerBoard.waitingSession") : t("playerBoard.noCampaign");
  }, [activeSession, combatActive, effectiveCampaignId, lastCommandType, pendingRoll, shopAvailable, shopOpen, t]);

  const commandDescription = useMemo(() => {
    if (pendingRoll?.reason) return pendingRoll.reason;
    if (pendingRoll?.issuedBy) return `${t("playerBoard.requestedBy")} ${pendingRoll.issuedBy}`;
    if (shopOpen) return t("playerBoard.shopPopoutBody");
    if (shopAvailable || lastCommandType === "open_shop") return t("playerBoard.shopPrompt");
    if (combatActive) return t("playerBoard.combatStartedDescription");
    if (activeSession) return t("playerBoard.noCommands");
    return effectiveCampaignId ? t("playerBoard.waitingSession") : t("playerBoard.noCampaignHint");
  }, [activeSession, combatActive, effectiveCampaignId, lastCommandType, pendingRoll, shopAvailable, shopOpen, t]);

  return {
    boardDescription,
    campaignTitle,
    commandDescription,
    commandTitle,
    inventoryTotal,
    sessionStatusLabel,
    sessionStatusTone,
  };
};
