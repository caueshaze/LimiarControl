import { useCallback, useEffect, useRef, useState } from "react";
import { partiesRepo, type PartyActiveSession, type PartyDetail } from "../../shared/api/partiesRepo";
import { inventoryRepo } from "../../shared/api/inventoryRepo";
import { itemsRepo } from "../../shared/api/itemsRepo";
import { sessionsRepo, type LobbyStatus } from "../../shared/api/sessionsRepo";
import { characterSheetsRepo } from "../../shared/api/characterSheetsRepo";
import type { CharacterSheetRecord } from "../../entities/character";
import type { InventoryItem } from "../../entities/inventory";
import type { Item } from "../../entities/item";
import type { PlayerPartySelectedItem } from "./playerParty.types";

type Props = {
  partyId: string | undefined;
  userId?: string | null;
};

export const usePlayerPartyPageData = ({ partyId, userId }: Props) => {
  const [party, setParty] = useState<PartyDetail | null>(null);
  const [sessions, setSessions] = useState<PartyActiveSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [myInventory, setMyInventory] = useState<InventoryItem[] | null>(null);
  const [catalogItems, setCatalogItems] = useState<Record<string, Item>>({});
  const [selectedItem, setSelectedItem] = useState<PlayerPartySelectedItem | null>(null);
  const [expandedSessionId, setExpandedSessionId] = useState<string | null>(null);
  const [lobbyStatus, setLobbyStatus] = useState<LobbyStatus | null>(null);
  const [joiningLobby, setJoiningLobby] = useState(false);
  const [hasJoinedLobby, setHasJoinedLobby] = useState(false);
  const [hasCharacterSheet, setHasCharacterSheet] = useState<boolean | null>(null);
  const [characterSheetRecord, setCharacterSheetRecord] = useState<CharacterSheetRecord | null>(null);
  const [characterSheetStatus, setCharacterSheetStatus] = useState<
    "missing" | "pending_acceptance" | "accepted" | null
  >(null);
  const wasLobbyRef = useRef(false);
  const prevActiveSessionIdRef = useRef<string | null>(null);
  const notifiedLobbySessionIdRef = useRef<string | null>(null);

  const refreshCharacterSheetStatus = useCallback(async () => {
    if (!partyId) {
      setHasCharacterSheet(null);
      setCharacterSheetRecord(null);
      setCharacterSheetStatus(null);
      return;
    }

    try {
      const record = await characterSheetsRepo.getByParty(partyId);
      setHasCharacterSheet(true);
      setCharacterSheetRecord(record);
      setCharacterSheetStatus(record.acceptedAt ? "accepted" : "pending_acceptance");
    } catch (error) {
      if ((error as { status?: number })?.status === 404) {
        setHasCharacterSheet(false);
        setCharacterSheetRecord(null);
        setCharacterSheetStatus("missing");
        return;
      }
      setHasCharacterSheet(null);
      setCharacterSheetRecord(null);
      setCharacterSheetStatus(null);
    }
  }, [partyId]);

  const loadData = useCallback(async () => {
    if (!partyId) return;
    setLoading(true);
    try {
      const [partyData, sessionsData] = await Promise.all([
        partiesRepo.get(partyId),
        partiesRepo.listPartySessions(partyId),
      ]);
      setParty(partyData);
      setSessions(sessionsData);
      await refreshCharacterSheetStatus();
    } catch {
      setParty(null);
    } finally {
      setLoading(false);
    }
  }, [partyId, refreshCharacterSheetStatus]);

  const refreshSessions = useCallback(async () => {
    if (!partyId) return [];
    try {
      const sessionsData = await partiesRepo.listPartySessions(partyId);
      setSessions(sessionsData);
      return sessionsData;
    } catch {
      return [];
    }
  }, [partyId]);

  const refreshActiveSession = useCallback(async () => {
    if (!partyId) return null;
    try {
      const session = await partiesRepo.getPartyActiveSession(partyId);
      setSessions((current) => {
        const next = current.filter((entry) => entry.id !== session.id);
        return [session, ...next];
      });
      return session;
    } catch {
      return null;
    }
  }, [partyId]);

  const syncActiveSessionFromRealtime = useCallback(
    async (expectedSessionId?: string | null) => {
      if (!partyId) return null;

      for (let attempt = 0; attempt < 4; attempt += 1) {
        try {
          const session = await partiesRepo.getPartyActiveSession(partyId);
          setSessions((current) => {
            const next = current.filter((entry) => entry.id !== session.id);
            return [session, ...next];
          });
          if (!expectedSessionId || session.id === expectedSessionId) {
            return session;
          }
        } catch {
          // ignore and retry
        }

        if (attempt < 3) {
          await new Promise((resolve) => window.setTimeout(resolve, 350 * (attempt + 1)));
        }
      }

      const sessionsData = await refreshSessions();
      return expectedSessionId
        ? sessionsData.find((session) => session.id === expectedSessionId) ?? null
        : sessionsData.find((session) => session.isActive) ?? null;
    },
    [partyId, refreshSessions],
  );

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (!partyId) return;
    const interval = setInterval(() => {
      void refreshSessions();
    }, 30_000);

    return () => {
      clearInterval(interval);
    };
  }, [partyId, refreshSessions]);

  useEffect(() => {
    void refreshCharacterSheetStatus();
  }, [refreshCharacterSheetStatus]);

  useEffect(() => {
    if (!party?.campaignId) return;

    Promise.all([inventoryRepo.list(party.campaignId), itemsRepo.list(party.campaignId)])
      .then(([inventory, items]) => {
        const itemMap: Record<string, Item> = {};
        for (const item of items) {
          itemMap[item.id] = item;
        }
        setCatalogItems(itemMap);
        setMyInventory(inventory);
      })
      .catch(() => {
        setMyInventory([]);
      });
  }, [party?.campaignId]);

  const activeSession = sessions.find((session) => session.isActive) ?? null;

  useEffect(() => {
    if (activeSession?.status === "LOBBY") {
      wasLobbyRef.current = true;
    }
  }, [activeSession?.status]);

  useEffect(() => {
    if (!activeSession?.id || activeSession.status !== "LOBBY") {
      setLobbyStatus(null);
      return;
    }

    let cancelled = false;

    const syncLobbyState = async () => {
      const [status, sessionsData] = await Promise.all([
        sessionsRepo.getLobbyStatus(activeSession.id).catch(() => null),
        refreshSessions(),
      ]);

      if (cancelled) {
        return;
      }

      if (status) {
        setLobbyStatus(status);
      }

      const refreshedActive = sessionsData.find((session) => session.isActive) ?? null;
      if (refreshedActive?.status === "ACTIVE") {
        setHasJoinedLobby(false);
      }
    };

    void syncLobbyState();
    const interval = setInterval(() => {
      void syncLobbyState();
    }, 5_000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [activeSession?.id, activeSession?.status, refreshSessions]);

  const handleJoinLobby = useCallback(async () => {
    if (!activeSession?.id || joiningLobby) return;
    setJoiningLobby(true);
    try {
      await sessionsRepo.joinLobby(activeSession.id);
      setHasJoinedLobby(true);
      if (userId) {
        setLobbyStatus((current) => {
          if (!current || current.ready.includes(userId)) {
            return current;
          }
          return { ...current, ready: [...current.ready, userId] };
        });
      }
    } catch {
      // ignore
    } finally {
      setJoiningLobby(false);
    }
  }, [activeSession?.id, joiningLobby, userId]);

  return {
    party,
    sessions,
    activeSession,
    loading,
    myInventory,
    catalogItems,
    selectedItem,
    expandedSessionId,
    lobbyStatus,
    joiningLobby,
    hasJoinedLobby,
    hasCharacterSheet,
    characterSheetRecord,
    characterSheetStatus,
    wasLobbyRef,
    prevActiveSessionIdRef,
    notifiedLobbySessionIdRef,
    loadData,
    refreshSessions,
    refreshActiveSession,
    syncActiveSessionFromRealtime,
    handleJoinLobby,
    setSelectedItem,
    setExpandedSessionId,
    setLobbyStatus,
    setHasJoinedLobby,
  };
};
