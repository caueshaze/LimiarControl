import { useCallback, useEffect, useState } from "react";
import { partiesRepo } from "../../shared/api/partiesRepo";
import { inventoryRepo } from "../../shared/api/inventoryRepo";
import { itemsRepo } from "../../shared/api/itemsRepo";
import { sessionStatesRepo } from "../../shared/api/sessionStatesRepo";
import type { InventoryItem } from "../../entities/inventory";
import type { Item } from "../../entities/item";
import type { CurrencyWallet } from "../../shared/api/inventoryRepo";
import { EMPTY_WALLET, normalizeWallet } from "../../features/shop/utils/shopCurrency";
import { parseCharacterSheet } from "../../features/character-sheet/model/characterSheet.schema";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import {
  useCampaignEvents,
  usePartyActiveSession,
  useSession,
  useSessionCommands,
} from "../../features/sessions";
import { useRollSession } from "../../features/dice-roller";

type Props = {
  partyId: string | undefined;
  selectedCampaignId: string | null;
  setSelectedCampaignLocal: (campaignId: string) => void;
  userId?: string | null;
};

export const usePlayerBoardResources = ({
  partyId,
  selectedCampaignId,
  setSelectedCampaignLocal,
  userId = null,
}: Props) => {
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const { activeSession, refresh } = usePartyActiveSession(partyId);
  const { selectedSessionId, setSelectedSessionId } = useSession();
  const {
    lastCommand,
    clearCommand,
    sessionEndedAt,
    clearSessionEnded,
    shopOpen: shopAvailable,
    combatActive,
    restState,
  } = useSessionCommands();
  const effectiveCampaignId = campaignId ?? selectedCampaignId ?? activeSession?.campaignId ?? null;
  const { lastEvent } = useCampaignEvents(effectiveCampaignId);
  const { roll, events: rollEvents } = useRollSession();
  const [myInventory, setMyInventory] = useState<InventoryItem[] | null>(null);
  const [catalogItems, setCatalogItems] = useState<Record<string, Item>>({});
  const [playerWallet, setPlayerWallet] = useState<CurrencyWallet | null>(null);
  const [playerSheet, setPlayerSheet] = useState<CharacterSheet | null>(null);

  const applyRealtimeStateSnapshot = useCallback((rawState: unknown): boolean => {
    try {
      const nextSheet = parseCharacterSheet(rawState);
      setPlayerSheet(nextSheet);
      setPlayerWallet(normalizeWallet(nextSheet.currency));
      return true;
    } catch {
      return false;
    }
  }, []);

  useEffect(() => {
    if (!partyId) {
      setCampaignId(null);
      return;
    }

    let active = true;
    partiesRepo.get(partyId)
      .then((party) => {
        if (active) {
          setCampaignId(party.campaignId);
        }
      })
      .catch(() => {
        if (active) {
          setCampaignId(null);
        }
      });

    return () => {
      active = false;
    };
  }, [partyId]);

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

  const refreshPlayerState = useCallback(async () => {
    if (!activeSession?.id) {
      setPlayerWallet(null);
      setPlayerSheet(null);
      return;
    }
    try {
      const record = await sessionStatesRepo.getMine(activeSession.id);
      setPlayerSheet(parseCharacterSheet(record.state));
      const nextWallet = normalizeWallet(
        (record.state as { currency?: unknown } | null | undefined)?.currency,
      );
      setPlayerWallet(nextWallet);
    } catch {
      setPlayerWallet(EMPTY_WALLET);
      setPlayerSheet(null);
    }
  }, [activeSession?.id]);

  const refreshPlayerWallet = useCallback(async () => {
    await refreshPlayerState();
  }, [refreshPlayerState]);

  useEffect(() => {
    if (!effectiveCampaignId) {
      setCatalogItems({});
      setMyInventory([]);
      return;
    }

    let active = true;
    Promise.all([
      inventoryRepo.list(effectiveCampaignId, null, partyId),
      itemsRepo.list(effectiveCampaignId),
    ]).then(([inventory, items]) => {
      if (!active) {
        return;
      }
      const itemMap: Record<string, Item> = {};
      for (const item of items) {
        itemMap[item.id] = item;
      }
      setCatalogItems(itemMap);
      setMyInventory(inventory);
    }).catch(() => {
      if (!active) {
        return;
      }
      setCatalogItems({});
      setMyInventory([]);
    });

    return () => {
      active = false;
    };
  }, [effectiveCampaignId, partyId]);

  useEffect(() => {
    void refreshPlayerState();
  }, [refreshPlayerState]);

  useEffect(() => {
    if (!activeSession?.id || !userId || !lastEvent) {
      return;
    }

    const eventPartyId =
      typeof lastEvent.payload.partyId === "string" ? lastEvent.payload.partyId : null;
    if (eventPartyId && partyId && eventPartyId !== partyId) {
      return;
    }

    const eventPlayerUserId =
      typeof (lastEvent.payload as { playerUserId?: unknown } | null | undefined)?.playerUserId === "string"
        ? (lastEvent.payload as { playerUserId: string }).playerUserId
        : null;
    const eventUserId =
      typeof (lastEvent.payload as { userId?: unknown } | null | undefined)?.userId === "string"
        ? (lastEvent.payload as { userId: string }).userId
        : null;

    const isOwnPlayerEvent = eventPlayerUserId === userId;
    const isOwnUserEvent = eventUserId === userId;

    if (
      lastEvent.type === "session_state_updated" &&
      isOwnPlayerEvent
    ) {
      if (!applyRealtimeStateSnapshot(lastEvent.payload.state)) {
        void refreshPlayerState();
      }
      return;
    }

    if (
      (lastEvent.type === "gm_granted_xp" ||
        lastEvent.type === "rest_started" ||
        lastEvent.type === "rest_ended" ||
        lastEvent.type === "hit_dice_used" ||
        lastEvent.type === "level_up_requested" ||
        lastEvent.type === "level_up_approved" ||
        lastEvent.type === "level_up_denied" ||
        lastEvent.type === "gm_granted_currency") &&
      (lastEvent.type === "rest_started" ||
        lastEvent.type === "rest_ended" ||
        isOwnPlayerEvent)
    ) {
      if (
        lastEvent.type === "rest_ended"
        && lastEvent.payload.restType === "long_rest"
      ) {
        void refreshInventoryData();
      }
      void refreshPlayerState();
      return;
    }

    if (lastEvent.type === "gm_granted_item" && isOwnPlayerEvent) {
      void refreshInventoryData();
      void refreshPlayerState();
      return;
    }

    if (
      (lastEvent.type === "shop_purchase_created" || lastEvent.type === "shop_sale_created") &&
      isOwnUserEvent
    ) {
      void refreshInventoryData();
      void refreshPlayerState();
      return;
    }

    if (lastEvent.type === "consumable_used") {
      const actorUserId =
        typeof lastEvent.payload.actorUserId === "string"
          ? lastEvent.payload.actorUserId
          : null;
      if (actorUserId && actorUserId === userId) {
        void refreshInventoryData();
      }
    }
  }, [
    activeSession?.id,
    applyRealtimeStateSnapshot,
    lastEvent,
    partyId,
    refreshInventoryData,
    refreshPlayerState,
    userId,
  ]);

  useEffect(() => {
    if (!activeSession?.id) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void refreshPlayerState();
    }, 5000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [activeSession?.id, refreshPlayerState]);

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
  }, [
    activeSession?.campaignId,
    activeSession?.id,
    campaignId,
    selectedCampaignId,
    selectedSessionId,
    setSelectedCampaignLocal,
    setSelectedSessionId,
  ]);

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
      refresh().catch(() => {});
    }, activeSession ? 30_000 : 15_000);
    return () => window.clearInterval(handle);
  }, [effectiveCampaignId, activeSession, refresh]);

  return {
    activeSession,
    catalogItems,
    clearCommand,
    clearSessionEnded,
    combatActive,
    effectiveCampaignId,
    lastCommand,
    lastEvent,
    myInventory,
    playerSheet,
    playerWallet,
    refresh,
    refreshInventoryData,
    refreshPlayerState,
    refreshPlayerWallet,
    restState,
    roll,
    rollEvents,
    sessionEndedAt,
    setMyInventory,
    setPlayerSheet,
    setPlayerWallet,
    setSelectedSessionId,
    shopAvailable,
  };
};
