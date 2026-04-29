import { useState } from "react";
import { sessionStatesRepo } from "../../shared/api/sessionStatesRepo";
import { characterSheetsRepo } from "../../shared/api/characterSheetsRepo";
import type { CurrencyWallet } from "../../shared/api/inventoryRepo";
import { sessionsRepo, type ActiveSession, type SessionGrantItemResult } from "../../shared/api/sessionsRepo";
import { formatWallet, normalizeWallet } from "../../features/shop/utils/shopCurrency";
import { toCopper, type CurrencyUnit } from "../../shared/utils/money";
import type { Item } from "../../entities/item";
import type { InventoryItem } from "../../entities/inventory";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import { clampHP } from "../../features/character-sheet/utils/calculations";
import { useLocale } from "../../shared/hooks/useLocale";
import type { CurrencyDraft, GrantFeedback, HpActionState, ItemDraft } from "./gmDashboard.types";

type Props = {
  activeSession: ActiveSession | null;
  memberIdByUserId: Record<string, string>;
  playerSheetByUserId: Record<string, CharacterSheet>;
  refreshPlayerSheet: (userId: string) => Promise<void>;
  setInventoryByMemberId: React.Dispatch<React.SetStateAction<Record<string, InventoryItem[]>>>;
  setWalletByUserId: React.Dispatch<React.SetStateAction<Record<string, CurrencyWallet>>>;
  sortedCatalogItems: Item[];
};

export const useGmDashboardRewardActions = ({
  activeSession,
  memberIdByUserId,
  playerSheetByUserId,
  refreshPlayerSheet,
  setInventoryByMemberId,
  setWalletByUserId,
  sortedCatalogItems,
}: Props) => {
  const { t } = useLocale();
  const [grantFeedbackByUserId, setGrantFeedbackByUserId] = useState<Record<string, GrantFeedback>>({});
  const [currencyDraftByUserId, setCurrencyDraftByUserId] = useState<Record<string, CurrencyDraft>>({});
  const [itemDraftByUserId, setItemDraftByUserId] = useState<Record<string, ItemDraft>>({});
  const [xpDraftByUserId, setXpDraftByUserId] = useState<Record<string, string>>({});
  const [hpDraftByUserId, setHpDraftByUserId] = useState<Record<string, string>>({});
  const [grantingCurrencyForUserId, setGrantingCurrencyForUserId] = useState<string | null>(null);
  const [grantingItemForUserId, setGrantingItemForUserId] = useState<string | null>(null);
  const [grantingXpForUserId, setGrantingXpForUserId] = useState<string | null>(null);
  const [hpActionState, setHpActionState] = useState<HpActionState | null>(null);
  const [levelUpActionState, setLevelUpActionState] = useState<{
    action: "approve" | "deny";
    userId: string;
  } | null>(null);

  const handleGrantCurrency = async (userId: string) => {
    if (!activeSession?.id || grantingCurrencyForUserId) return;
    const draft = currencyDraftByUserId[userId] ?? { amount: "", coin: "gp" as CurrencyUnit };
    const amount = Number(draft.amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: { tone: "error", message: t("gm.dashboard.enterValidCurrencyAmount") },
      }));
      return;
    }

    setGrantingCurrencyForUserId(userId);
    setGrantFeedbackByUserId((current) => ({
      ...current,
      [userId]: { tone: "success", message: t("gm.dashboard.sendingCurrency") },
    }));

    try {
      const result = await sessionsRepo.grantCurrency(activeSession.id, {
        playerUserId: userId,
        copperValue: toCopper(amount, draft.coin),
      });
      setWalletByUserId((current) => ({
        ...current,
        [userId]: normalizeWallet(result.currentCurrency),
      }));
      setCurrencyDraftByUserId((current) => ({
        ...current,
        [userId]: { amount: "", coin: draft.coin },
      }));
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: {
          tone: "success",
          message: `Currency delivered. Current funds: ${formatWallet(result.currentCurrency)}.`,
        },
      }));
    } catch (error) {
      setGrantFeedbackByUserId((current) => ({
        ...current,
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
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: { tone: "error", message: t("gm.dashboard.chooseItemBeforeSending") },
      }));
      return;
    }
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: { tone: "error", message: t("gm.dashboard.enterValidItemQuantity") },
      }));
      return;
    }

    const memberId = memberIdByUserId[userId];
    setGrantingItemForUserId(userId);
    setGrantFeedbackByUserId((current) => ({
      ...current,
      [userId]: { tone: "success", message: t("gm.dashboard.sendingItem") },
    }));

    try {
      const result = await sessionsRepo.grantItem(activeSession.id, {
        playerUserId: userId,
        itemId: draft.itemId,
        quantity,
      });
      if (memberId) {
        setInventoryByMemberId((current) => ({
          ...current,
          [memberId]: upsertGrantedInventory(current[memberId] ?? [], result),
        }));
      }
      setItemDraftByUserId((current) => ({
        ...current,
        [userId]: { itemId: draft.itemId, quantity: "1" },
      }));
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: {
          tone: "success",
          message: `${result.itemName} x${result.quantity} delivered successfully.`,
        },
      }));
    } catch (error) {
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: {
          tone: "error",
          message: (error as { message?: string })?.message ?? "Could not deliver the item right now.",
        },
      }));
    } finally {
      setGrantingItemForUserId(null);
    }
  };

  const handleGrantXp = async (userId: string) => {
    if (!activeSession?.id || grantingXpForUserId) return;
    const amount = Number(xpDraftByUserId[userId] ?? "");
    if (!Number.isFinite(amount) || amount <= 0) {
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: { tone: "error", message: t("gm.dashboard.enterValidXpAmount") },
      }));
      return;
    }

    setGrantingXpForUserId(userId);
    setGrantFeedbackByUserId((current) => ({
      ...current,
      [userId]: { tone: "success", message: t("gm.dashboard.grantingXp") },
    }));

    try {
      const result = await sessionsRepo.grantXp(activeSession.id, {
        playerUserId: userId,
        amount,
      });
      await refreshPlayerSheet(userId);
      setXpDraftByUserId((current) => ({ ...current, [userId]: "" }));
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: {
          tone: "success",
          message:
            result.nextLevelThreshold === null
              ? `${result.grantedAmount} XP delivered. Character is already at max level.`
              : `${result.grantedAmount} XP delivered. Current XP: ${result.currentXp}/${result.nextLevelThreshold}.`,
        },
      }));
    } catch (error) {
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: {
          tone: "error",
          message: (error as { message?: string })?.message ?? "Could not deliver XP right now.",
        },
      }));
    } finally {
      setGrantingXpForUserId(null);
    }
  };

  const handleLevelUpDecision = async (userId: string, action: "approve" | "deny") => {
    if (!activeSession?.partyId || levelUpActionState) return;

    setLevelUpActionState({ action, userId });
    setGrantFeedbackByUserId((current) => ({
      ...current,
      [userId]: {
        tone: "success",
        message: action === "approve" ? t("gm.dashboard.approvingLevelUp") : t("gm.dashboard.denyingLevelUp"),
      },
    }));

    try {
      if (action === "approve") {
        await characterSheetsRepo.approveLevelUp(activeSession.partyId, userId);
      } else {
        await characterSheetsRepo.denyLevelUp(activeSession.partyId, userId);
      }
      await refreshPlayerSheet(userId);
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: {
          tone: "success",
          message:
            action === "approve"
              ? t("gm.dashboard.levelUpApprovedUpdated")
              : t("gm.dashboard.levelUpDenied"),
        },
      }));
    } catch (error) {
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: {
          tone: "error",
          message: (error as { message?: string })?.message ?? t("gm.dashboard.failedToUpdateLevelUpRequest"),
        },
      }));
    } finally {
      setLevelUpActionState(null);
    }
  };

  const handleAdjustHp = async (userId: string, action: "damage" | "heal") => {
    if (!activeSession?.id || hpActionState) return;

    const amount = Number(hpDraftByUserId[userId] ?? "");
    if (!Number.isFinite(amount) || amount <= 0) {
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: { tone: "error", message: t("gm.dashboard.enterValidHpAmount") },
      }));
      return;
    }

    const sheet = playerSheetByUserId[userId];
    if (!sheet) {
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: { tone: "error", message: t("gm.dashboard.playerSheetLoading") },
      }));
      return;
    }

    setHpActionState({ action, userId });
    setGrantFeedbackByUserId((current) => ({
      ...current,
      [userId]: {
        tone: "success",
          message:
            action === "damage"
              ? t("gm.dashboard.applyingDamageProgress")
              : t("gm.dashboard.applyingHealingProgress"),
        },
      }));

    try {
      const delta = action === "damage" ? -amount : amount;
      const nextCurrentHp = clampHP(sheet.currentHP + delta, sheet.maxHP);
      await sessionStatesRepo.updateByPlayer(activeSession.id, userId, {
        ...sheet,
        currentHP: nextCurrentHp,
      });
      await refreshPlayerSheet(userId);
      setHpDraftByUserId((current) => ({ ...current, [userId]: "" }));
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: {
          tone: "success",
          message: `HP updated to ${nextCurrentHp}/${sheet.maxHP}.`,
        },
      }));
    } catch (error) {
      setGrantFeedbackByUserId((current) => ({
        ...current,
        [userId]: {
          tone: "error",
          message: (error as { message?: string })?.message ?? "Could not update HP right now.",
        },
      }));
    } finally {
      setHpActionState(null);
    }
  };

  return {
    currencyDraftByUserId,
    grantFeedbackByUserId,
    grantingCurrencyForUserId,
    grantingItemForUserId,
    grantingXpForUserId,
    handleDamagePlayer: (userId: string) => handleAdjustHp(userId, "damage"),
    handleHealPlayer: (userId: string) => handleAdjustHp(userId, "heal"),
    handleApproveLevelUp: (userId: string) => handleLevelUpDecision(userId, "approve"),
    handleDenyLevelUp: (userId: string) => handleLevelUpDecision(userId, "deny"),
    handleGrantCurrency,
    handleGrantItem,
    handleGrantXp,
    hpActionState,
    hpDraftByUserId,
    itemDraftByUserId,
    levelUpActionState,
    setCurrencyDraftByUserId,
    setHpDraftByUserId,
    setItemDraftByUserId,
    setXpDraftByUserId,
    xpDraftByUserId,
  };
};

const upsertGrantedInventory = (
  current: InventoryItem[],
  result: SessionGrantItemResult,
) => {
  const existing = current.find((item) => item.id === result.inventoryItem.id);
  if (existing) {
    return current.map((item) => (item.id === result.inventoryItem.id ? result.inventoryItem : item));
  }
  return [result.inventoryItem, ...current];
};
