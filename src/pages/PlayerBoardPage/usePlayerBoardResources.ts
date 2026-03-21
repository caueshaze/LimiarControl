import { useCallback, useEffect, useState } from "react";
import { partiesRepo } from "../../shared/api/partiesRepo";
import { inventoryRepo } from "../../shared/api/inventoryRepo";
import { itemsRepo } from "../../shared/api/itemsRepo";
import { sessionStatesRepo } from "../../shared/api/sessionStatesRepo";
import type { InventoryItem } from "../../entities/inventory";
import type { Item } from "../../entities/item";
import type { CurrencyWallet } from "../../shared/api/inventoryRepo";
import { EMPTY_WALLET, normalizeWallet } from "../../features/shop/utils/shopCurrency";
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
};

export const usePlayerBoardResources = ({
  partyId,
  selectedCampaignId,
  setSelectedCampaignLocal,
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
  } = useSessionCommands();
  const effectiveCampaignId = campaignId ?? selectedCampaignId ?? activeSession?.campaignId ?? null;
  const { lastEvent } = useCampaignEvents(effectiveCampaignId);
  const { roll, events: rollEvents } = useRollSession();
  const [myInventory, setMyInventory] = useState<InventoryItem[] | null>(null);
  const [catalogItems, setCatalogItems] = useState<Record<string, Item>>({});
  const [playerWallet, setPlayerWallet] = useState<CurrencyWallet | null>(null);

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

  const refreshPlayerWallet = useCallback(async () => {
    if (!activeSession?.id) {
      setPlayerWallet(null);
      return;
    }
    try {
      const record = await sessionStatesRepo.getMine(activeSession.id);
      const nextWallet = normalizeWallet(
        (record.state as { currency?: unknown } | null | undefined)?.currency,
      );
      setPlayerWallet(nextWallet);
    } catch {
      setPlayerWallet(EMPTY_WALLET);
    }
  }, [activeSession?.id]);

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
    playerWallet,
    refresh,
    refreshInventoryData,
    refreshPlayerWallet,
    roll,
    rollEvents,
    sessionEndedAt,
    setMyInventory,
    setPlayerWallet,
    setSelectedSessionId,
    shopAvailable,
  };
};
