import { useCallback, useEffect, useState } from "react";
import { partiesRepo } from "../../shared/api/partiesRepo";
import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import { inventoryRepo } from "../../shared/api/inventoryRepo";
import { itemsRepo } from "../../shared/api/itemsRepo";
import { sessionStatesRepo } from "../../shared/api/sessionStatesRepo";
import type { InventoryItem } from "../../entities/inventory";
import type { Item } from "../../entities/item";
import type { ActiveConcentration } from "../../entities/character";
import type { ActiveEffect, PendingSpellPreparation } from "../../shared/api/combatRepo";
import type { CurrencyWallet } from "../../shared/api/inventoryRepo";
import { EMPTY_WALLET } from "../../features/shop/utils/shopCurrency";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import {
  useCampaignEvents,
  usePartyActiveSession,
  useSession,
  useSessionCommands,
} from "../../features/sessions";
import { useRollSession } from "../../features/dice-roller";
import { parsePlayerBoardStateSnapshot } from "./playerBoardStateSnapshot";

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
  const [partyPlayers, setPartyPlayers] = useState<PartyMemberSummary[]>([]);
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
  const [activeConcentration, setActiveConcentration] = useState<ActiveConcentration | null>(null);
  const [activeSpellEffects, setActiveSpellEffects] = useState<ActiveEffect[] | null>(null);
  const [pendingSpellPreparation, setPendingSpellPreparation] = useState<PendingSpellPreparation | null>(null);

  const applyPlayerBoardStateSnapshot = useCallback((snapshot: ReturnType<typeof parsePlayerBoardStateSnapshot>) => {
    if (!snapshot) return false;
    setPlayerSheet(snapshot.playerSheet);
    setPlayerWallet(snapshot.playerWallet);
    setActiveConcentration(snapshot.activeConcentration);
    setActiveSpellEffects(snapshot.activeSpellEffects);
    setPendingSpellPreparation(snapshot.pendingSpellPreparation);
    return true;
  }, []);

  useEffect(() => {
    if (!partyId) {
      setCampaignId(null);
      setPartyPlayers([]);
      return;
    }

    let active = true;
    partiesRepo.get(partyId)
      .then((party) => {
        if (active) {
          setCampaignId(party.campaignId);
          setPartyPlayers(
            party.members.filter(
              (m) => m.role === "PLAYER" && m.status === "joined" && m.userId !== userId,
            ),
          );
        }
      })
      .catch(() => {
        if (active) {
          setCampaignId(null);
          setPartyPlayers([]);
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
      setActiveConcentration(null);
      setActiveSpellEffects(null);
      setPendingSpellPreparation(null);
      return;
    }
    try {
      const record = await sessionStatesRepo.getMine(activeSession.id);
      const snapshot = parsePlayerBoardStateSnapshot({
        state: record.state,
        activeConcentration: record.activeConcentration ?? null,
        activeSpellEffects:
          (record.activeSpellEffects as ActiveEffect[] | null | undefined) ?? null,
        pendingSpellPreparation:
          (record.pendingSpellPreparation as PendingSpellPreparation | null | undefined) ?? null,
      });
      if (!applyPlayerBoardStateSnapshot(snapshot)) {
        throw new Error("Invalid player state snapshot");
      }
    } catch {
      setPlayerWallet(EMPTY_WALLET);
      setPlayerSheet(null);
      setActiveConcentration(null);
      setActiveSpellEffects(null);
      setPendingSpellPreparation(null);
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

    const payload = lastEvent.payload as Record<string, unknown>;
    const eventPartyId =
      typeof payload.partyId === "string" ? payload.partyId : null;
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
      if (!applyPlayerBoardStateSnapshot(parsePlayerBoardStateSnapshot({ state: lastEvent.payload.state }))) {
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
    applyPlayerBoardStateSnapshot,
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
    activeConcentration,
    activeSession,
    activeSpellEffects,
    catalogItems,
    clearCommand,
    clearSessionEnded,
    combatActive,
    effectiveCampaignId,
    lastCommand,
    lastEvent,
    myInventory,
    partyPlayers,
    pendingSpellPreparation,
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
    setActiveConcentration,
    setActiveSpellEffects,
    setMyInventory,
    setPendingSpellPreparation,
    setPlayerSheet,
    setPlayerWallet,
    setSelectedSessionId,
    shopAvailable,
  };
};
