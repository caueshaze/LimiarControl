import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  useActiveSession,
  useCampaignEvents,
  useSession,
  useSessionCommands,
} from "../../features/sessions";
import { useRollSession } from "../../features/dice-roller";
import { campaignsRepo } from "../../shared/api/campaignsRepo";
import { sessionsRepo, type ActivityEvent, type LobbyStatus } from "../../shared/api/sessionsRepo";
import { partiesRepo, type PartyMemberSummary } from "../../shared/api/partiesRepo";
import { membersRepo } from "../../shared/api/membersRepo";
import { inventoryRepo, type CurrencyWallet } from "../../shared/api/inventoryRepo";
import { itemsRepo } from "../../shared/api/itemsRepo";
import { sessionStatesRepo } from "../../shared/api/sessionStatesRepo";
import type { CampaignSystemType } from "../../entities/campaign";
import type { InventoryItem } from "../../entities/inventory";
import type { Item } from "../../entities/item";
import { EMPTY_WALLET, normalizeWallet } from "../../features/shop/utils/shopCurrency";
import { useGmDashboardPlayerProgress } from "./useGmDashboardPlayerProgress";

type Props = {
  effectiveCampaignId: string | null;
  selectCampaign: (campaignId: string) => void;
  selectedCampaignId: string | null;
};

export const useGmDashboardData = ({
  effectiveCampaignId,
  selectCampaign,
  selectedCampaignId,
}: Props) => {
  const { activeSession, loading, activate, endSession, refresh: refreshSession } = useActiveSession(effectiveCampaignId);
  const { selectedSessionId, setSelectedSessionId } = useSession();
  const { shopOpen: shopActive, combatActive } = useSessionCommands();
  const { events: rollEvents } = useRollSession();
  const { lastEvent, onlineUsers } = useCampaignEvents(effectiveCampaignId);
  const [overviewName, setOverviewName] = useState<string | null>(null);
  const [overviewSystem, setOverviewSystem] = useState<CampaignSystemType | null>(null);
  const [activityFeed, setActivityFeed] = useState<ActivityEvent[]>([]);
  const activityIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [partyPlayers, setPartyPlayers] = useState<PartyMemberSummary[]>([]);
  const [memberIdByUserId, setMemberIdByUserId] = useState<Record<string, string>>({});
  const [inventoryByMemberId, setInventoryByMemberId] = useState<Record<string, InventoryItem[]>>({});
  const [walletByUserId, setWalletByUserId] = useState<Record<string, CurrencyWallet>>({});
  const [catalogItems, setCatalogItems] = useState<Record<string, Item>>({});
  const [shopUiOpen, setShopUiOpen] = useState(false);
  const [combatUiActive, setCombatUiActive] = useState(false);
  const [lobbyStatus, setLobbyStatus] = useState<LobbyStatus | null>(null);
  const { playerSheetByUserId, refreshPlayerSheet } = useGmDashboardPlayerProgress({
    activeSession,
    lastEvent,
    partyPlayers,
  });

  const sortedCatalogItems = useMemo(
    () => Object.values(catalogItems).sort((left, right) => left.name.localeCompare(right.name)),
    [catalogItems],
  );

  const refreshPlayerInventory = useCallback(async (userId: string) => {
    const memberId = memberIdByUserId[userId];
    if (!memberId || !effectiveCampaignId) return;
    try {
      const items = await inventoryRepo.list(effectiveCampaignId, memberId, activeSession?.partyId);
      setInventoryByMemberId((current) => ({ ...current, [memberId]: items }));
    } catch {
      // ignore
    }
  }, [activeSession?.partyId, effectiveCampaignId, memberIdByUserId]);

  const refreshPlayerWallet = useCallback(async (userId: string) => {
    if (!activeSession?.id) return;
    try {
      const state = await sessionStatesRepo.getByPlayer(activeSession.id, userId);
      const nextWallet = normalizeWallet(
        (state.state as { currency?: unknown } | null | undefined)?.currency,
      );
      setWalletByUserId((current) => ({ ...current, [userId]: nextWallet }));
    } catch {
      setWalletByUserId((current) => ({ ...current, [userId]: EMPTY_WALLET }));
    }
  }, [activeSession?.id]);

  const refreshActivity = useCallback(async () => {
    if (!activeSession?.id) return;
    try {
      const events = await sessionsRepo.getActivity(activeSession.id);
      setActivityFeed(events);
    } catch {
      // ignore
    }
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
    void refreshActivity();
    activityIntervalRef.current = setInterval(refreshActivity, 10_000);
    return () => {
      if (activityIntervalRef.current) {
        clearInterval(activityIntervalRef.current);
        activityIntervalRef.current = null;
      }
    };
  }, [activeSession?.id, refreshActivity]);

  useEffect(() => {
    setShopUiOpen(shopActive);
  }, [shopActive]);

  useEffect(() => {
    setCombatUiActive(combatActive);
  }, [combatActive]);

  useEffect(() => {
    if (!lastEvent) return;
    void refreshActivity();

    if (
      lastEvent.type === "session_started" ||
      lastEvent.type === "session_lobby" ||
      lastEvent.type === "session_closed"
    ) {
      refreshSession();
    }

    const eventPartyId =
      typeof lastEvent.payload.partyId === "string" ? lastEvent.payload.partyId : null;
    const isOtherPartyEvent =
      eventPartyId && activeSession?.partyId && eventPartyId !== activeSession.partyId;
    if (lastEvent.type === "shop_opened" && !isOtherPartyEvent) setShopUiOpen(true);
    if (lastEvent.type === "shop_closed" && !isOtherPartyEvent) setShopUiOpen(false);
    if (lastEvent.type === "combat_started" && !isOtherPartyEvent) setCombatUiActive(true);
    if (lastEvent.type === "combat_ended" && !isOtherPartyEvent) setCombatUiActive(false);

    if (lastEvent.type === "session_lobby") {
      setLobbyStatus({
        sessionId: String(lastEvent.payload.sessionId),
        campaignId: typeof lastEvent.payload.campaignId === "string" ? lastEvent.payload.campaignId : null,
        partyId: typeof lastEvent.payload.partyId === "string" ? lastEvent.payload.partyId : null,
        expected: (lastEvent.payload.expectedPlayers as LobbyStatus["expected"]) ?? [],
        ready: (lastEvent.payload.readyUserIds as string[]) ?? [],
        readyCount: Number(lastEvent.payload.readyCount ?? 0),
        totalCount: Number(lastEvent.payload.totalCount ?? (lastEvent.payload.expectedPlayers as unknown[] | undefined)?.length ?? 0),
      });
    }

    if (lastEvent.type === "player_joined_lobby") {
      setLobbyStatus((current) => {
        if (!current || current.sessionId !== lastEvent.payload.sessionId) return current;
        if (current.ready.includes(String(lastEvent.payload.userId))) return current;
        return {
          ...current,
          ready: [...current.ready, String(lastEvent.payload.userId)],
          readyCount: Number(lastEvent.payload.readyCount ?? current.readyCount + 1),
        };
      });
    }

    if (lastEvent.type === "party_member_updated" && activeSession?.partyId) {
      partiesRepo.get(activeSession.partyId)
        .then((party) => {
          const players = party.members.filter((member) => member.role === "PLAYER" && member.status === "joined");
          setPartyPlayers(players);
        })
        .catch(() => {});
    }

    if (lastEvent.type === "shop_purchase_created" || lastEvent.type === "shop_sale_created") {
      const eventUserId =
        typeof lastEvent.payload.userId === "string" ? lastEvent.payload.userId : null;
      if (eventUserId) {
        void refreshPlayerInventory(eventUserId);
        void refreshPlayerWallet(eventUserId);
      }
    }

    if (lastEvent.type === "gm_granted_item") {
      const eventUserId =
        typeof lastEvent.payload.playerUserId === "string" ? lastEvent.payload.playerUserId : null;
      if (eventUserId) {
        void refreshPlayerInventory(eventUserId);
      }
    }

    if (lastEvent.type === "gm_granted_currency") {
      const eventUserId =
        typeof lastEvent.payload.playerUserId === "string" ? lastEvent.payload.playerUserId : null;
      if (eventUserId) {
        setWalletByUserId((current) => ({
          ...current,
          [eventUserId]: normalizeWallet(
            (lastEvent.payload as { currentCurrency?: unknown } | null | undefined)?.currentCurrency,
          ),
        }));
      }
    }

    if (lastEvent.type === "session_state_updated") {
      const eventUserId =
        typeof lastEvent.payload.playerUserId === "string" ? lastEvent.payload.playerUserId : null;
      if (eventUserId && partyPlayers.some((player) => player.userId === eventUserId)) {
        void refreshPlayerWallet(eventUserId);
      }
    }
  }, [
    activeSession?.partyId,
    lastEvent,
    partyPlayers,
    refreshActivity,
    refreshPlayerInventory,
    refreshPlayerWallet,
    refreshSession,
  ]);

  useEffect(() => {
    if (!effectiveCampaignId) {
      setCatalogItems({});
      return;
    }
    itemsRepo.list(effectiveCampaignId)
      .then((items) => {
        const next: Record<string, Item> = {};
        for (const item of items) next[item.id] = item;
        setCatalogItems(next);
      })
      .catch(() => {});
  }, [effectiveCampaignId]);

  useEffect(() => {
    if (!activeSession?.partyId || !effectiveCampaignId) {
      setPartyPlayers([]);
      setMemberIdByUserId({});
      setInventoryByMemberId({});
      setWalletByUserId({});
      return;
    }

    Promise.all([partiesRepo.get(activeSession.partyId), membersRepo.list(effectiveCampaignId)])
      .then(([party, campaignMembers]) => {
        const players = party.members.filter((member) => member.role === "PLAYER" && member.status === "joined");
        const memberMap: Record<string, string> = {};
        for (const member of campaignMembers) {
          memberMap[member.userId] = member.id;
        }
        setPartyPlayers(players);
        setMemberIdByUserId(memberMap);
      })
      .catch(() => {});
  }, [activeSession?.partyId, effectiveCampaignId]);

  useEffect(() => {
    if (!effectiveCampaignId) return;
    if (selectedCampaignId !== effectiveCampaignId) {
      selectCampaign(effectiveCampaignId);
    }
  }, [effectiveCampaignId, selectCampaign, selectedCampaignId]);

  useEffect(() => {
    if (!effectiveCampaignId) {
      setOverviewName(null);
      setOverviewSystem(null);
      return;
    }
    campaignsRepo.overview(effectiveCampaignId)
      .then((data) => {
        setOverviewName(data.name);
        setOverviewSystem(data.systemType);
      })
      .catch(() => {
        setOverviewName(null);
        setOverviewSystem(null);
      });
  }, [effectiveCampaignId]);

  useEffect(() => {
    if (!activeSession?.id) return;
    if (selectedSessionId !== activeSession.id) {
      setSelectedSessionId(activeSession.id);
    }
  }, [activeSession?.id, selectedSessionId, setSelectedSessionId]);

  useEffect(() => {
    if (!activeSession?.id || activeSession.status !== "LOBBY") {
      setLobbyStatus(null);
      return;
    }

    let cancelled = false;
    sessionsRepo.getLobbyStatus(activeSession.id)
      .then((status) => {
        if (!cancelled) setLobbyStatus(status);
      })
      .catch(() => {});

    const intervalId = setInterval(() => {
      sessionsRepo.getLobbyStatus(activeSession.id)
        .then((status) => {
          if (!cancelled) setLobbyStatus(status);
        })
        .catch(() => {});
    }, 2000);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, [activeSession?.id, activeSession?.status]);

  return {
    activate,
    activeSession,
    activityFeed,
    catalogItems,
    combatUiActive,
    endSession,
    lastEvent,
    loading,
    lobbyStatus,
    memberIdByUserId,
    onlineUsers,
    overviewName,
    overviewSystem,
    partyPlayers,
    playerSheetByUserId,
    refreshPlayerInventory,
    refreshPlayerSheet,
    refreshPlayerWallet,
    rollEvents,
    setCombatUiActive,
    setInventoryByMemberId,
    setLobbyStatus,
    setSelectedSessionId,
    setShopUiOpen,
    setWalletByUserId,
    shopUiOpen,
    sortedCatalogItems,
    walletByUserId,
    inventoryByMemberId,
  };
};
