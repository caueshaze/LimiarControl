import { useEffect, useMemo, useRef, useState } from "react";
import { routes } from "../../app/routes/routes";
import { sessionsRepo, type ActiveSession } from "../../shared/api/sessionsRepo";
import type { LocaleKey } from "../../shared/i18n";
import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import type { CurrencyWallet } from "../../shared/api/inventoryRepo";
import type { Item } from "../../entities/item";
import type { InventoryItem } from "../../entities/inventory";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import type { CommandFeedback } from "./gmDashboard.types";
import { useGmDashboardRewardActions } from "./useGmDashboardRewardActions";

type Props = {
  activate: (name: string) => Promise<ActiveSession | null>;
  activeSession: ActiveSession | null;
  endSession: () => Promise<boolean | null>;
  memberIdByUserId: Record<string, string>;
  navigate: (to: string) => void;
  partyPlayers: PartyMemberSummary[];
  playerSheetByUserId: Record<string, CharacterSheet>;
  refreshPlayerInventory: (userId: string) => Promise<void>;
  refreshPlayerSheet: (userId: string) => Promise<void>;
  refreshPlayerWallet: (userId: string) => Promise<void>;
  setRestUiState: React.Dispatch<React.SetStateAction<"exploration" | "short_rest" | "long_rest">>;
  setCombatUiActive: React.Dispatch<React.SetStateAction<boolean>>;
  setInventoryByMemberId: React.Dispatch<React.SetStateAction<Record<string, InventoryItem[]>>>;
  setSelectedSessionId: (sessionId: string | null) => void;
  setShopUiOpen: React.Dispatch<React.SetStateAction<boolean>>;
  setWalletByUserId: React.Dispatch<React.SetStateAction<Record<string, CurrencyWallet>>>;
  sortedCatalogItems: Item[];
  t: (key: LocaleKey) => string;
};

export const useGmDashboardActions = ({
  activate,
  activeSession,
  endSession,
  memberIdByUserId,
  navigate,
  partyPlayers,
  playerSheetByUserId,
  refreshPlayerInventory,
  refreshPlayerSheet,
  refreshPlayerWallet,
  setRestUiState,
  setCombatUiActive,
  setInventoryByMemberId,
  setSelectedSessionId,
  setShopUiOpen,
  setWalletByUserId,
  sortedCatalogItems,
  t,
}: Props) => {
  const [creating, setCreating] = useState(false);
  const [commandSending, setCommandSending] = useState(false);
  const [rollExpression, setRollExpression] = useState("d20");
  const [rollReason, setRollReason] = useState("");
  const [rollAdvantage, setRollAdvantage] = useState<"normal" | "advantage" | "disadvantage">("normal");
  const [showStartModal, setShowStartModal] = useState(false);
  const [rollTargetUserId, setRollTargetUserId] = useState<string | null>(null);
  const [inventoryOpenForUserId, setInventoryOpenForUserId] = useState<string | null>(null);
  const [commandFeedback, setCommandFeedback] = useState<CommandFeedback | null>(null);
  const [forceStarting, setForceStarting] = useState(false);
  const [missingSheetsPlayers, setMissingSheetsPlayers] = useState<{ userId: string; displayName: string }[]>([]);
  const commandFeedbackTimeoutRef = useRef<number | null>(null);
  const rewardActions = useGmDashboardRewardActions({
    activeSession,
    memberIdByUserId,
    playerSheetByUserId,
    refreshPlayerSheet,
    setInventoryByMemberId,
    setWalletByUserId,
    sortedCatalogItems,
  });

  const rollOptions = useMemo(() => ["d4", "d6", "d8", "d10", "d12", "d20"], []);

  const handleOpenInventory = async (userId: string) => {
    if (inventoryOpenForUserId === userId) {
      setInventoryOpenForUserId(null);
      return;
    }
    setInventoryOpenForUserId(userId);
    await Promise.all([refreshPlayerInventory(userId), refreshPlayerWallet(userId)]);
  };

  const handleForceStart = async () => {
    if (!activeSession?.id || forceStarting) return;
    setForceStarting(true);
    setMissingSheetsPlayers([]);
    try {
      const updated = await sessionsRepo.forceStartLobby(activeSession.id);
      if (updated?.id) setSelectedSessionId(updated.id);
    } catch (error: unknown) {
      const detail = (error as {
        data?: { detail?: { code?: string; players?: { userId: string; displayName: string }[] } };
      })?.data?.detail;
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
    } catch (error: unknown) {
      const detail = (error as {
        data?: { detail?: { code?: string; players?: { userId: string; displayName: string }[] } };
      })?.data?.detail;
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
    navigate(partyId ? routes.partyDetails.replace(":partyId", partyId) : routes.home);
  };

  const handleCommand = async (
    type: CommandFeedback["type"],
    payload?: Record<string, unknown>,
  ) => {
    if (!activeSession?.id || commandSending) return;
    setCommandSending(true);
    setCommandFeedback(null);
    try {
      const extra: Record<string, unknown> = {};
      if (type === "request_roll" && rollTargetUserId) extra.targetUserId = rollTargetUserId;
      if (type === "request_roll" && rollReason.trim()) extra.reason = rollReason.trim();
      if (type === "request_roll" && rollAdvantage !== "normal") extra.mode = rollAdvantage;
      await sessionsRepo.command(activeSession.id, { type, payload: { ...(payload ?? {}), ...extra } });
      if (type === "open_shop") setShopUiOpen(true);
      if (type === "close_shop") setShopUiOpen(false);
      if (type === "start_combat") setCombatUiActive(true);
      if (type === "end_combat") setCombatUiActive(false);
      if (type === "start_short_rest") setRestUiState("short_rest");
      if (type === "start_long_rest") setRestUiState("long_rest");
      if (type === "end_rest") setRestUiState("exploration");
      const message =
        type === "open_shop"
          ? "Shop command accepted by the server."
          : type === "close_shop"
            ? "Close shop command accepted by the server."
            : type === "start_combat"
              ? "Combat is now live for the session."
              : type === "end_combat"
                ? "Combat mode was closed for the session."
                : type === "start_short_rest"
                  ? "Short rest started for the whole table."
                  : type === "start_long_rest"
                    ? "Long rest started for the whole table."
                    : type === "end_rest"
                      ? "The active rest was ended for the whole table."
                      : "Roll request accepted by the server.";
      if (commandFeedbackTimeoutRef.current) window.clearTimeout(commandFeedbackTimeoutRef.current);
      setCommandFeedback({ tone: "success", type, message });
      commandFeedbackTimeoutRef.current = window.setTimeout(() => {
        setCommandFeedback(null);
        commandFeedbackTimeoutRef.current = null;
      }, 4000);
    } catch (error) {
      const message = (error as { message?: string })?.message ?? "Command failed before the server accepted it.";
      if (commandFeedbackTimeoutRef.current) window.clearTimeout(commandFeedbackTimeoutRef.current);
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

  return {
    commandFeedback,
    commandSending,
    creating,
    forceStarting,
    handleActivateClick,
    handleCommand,
    handleConfirmStart,
    handleEndSession,
    handleForceStart,
    handleOpenInventory,
    inventoryOpenForUserId,
    missingSheetsPlayers,
    rollAdvantage,
    rollExpression,
    rollOptions,
    rollReason,
    rollTargetUserId,
    setMissingSheetsPlayers,
    setRollAdvantage,
    setRollExpression,
    setRollReason,
    setRollTargetUserId,
    setShowStartModal,
    showStartModal,
    sortedCatalogItems,
    ...rewardActions,
  };
};
