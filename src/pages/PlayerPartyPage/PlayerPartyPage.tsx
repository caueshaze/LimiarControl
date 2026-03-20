import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { partiesRepo, type PartyActiveSession, type PartyDetail } from "../../shared/api/partiesRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import { useCampaignEvents } from "../../features/sessions";
import { useAuth } from "../../features/auth";
import { inventoryRepo } from "../../shared/api/inventoryRepo";
import { itemsRepo } from "../../shared/api/itemsRepo";
import { sessionsRepo, type LobbyStatus } from "../../shared/api/sessionsRepo";
import { characterSheetsRepo } from "../../shared/api/characterSheetsRepo";
import type { InventoryItem } from "../../entities/inventory";
import type { Item } from "../../entities/item";
import { PlayerPartyHeader } from "./components/PlayerPartyHeader";
import { PlayerPartyInventoryCard } from "./components/PlayerPartyInventoryCard";
import { PlayerPartyItemModal } from "./components/PlayerPartyItemModal";
import { PlayerPartyMembersCard } from "./components/PlayerPartyMembersCard";
import { PlayerPartySessionCard } from "./components/PlayerPartySessionCard";
import { PlayerPartySessionHistoryCard } from "./components/PlayerPartySessionHistoryCard";
import { PlayerPartySheetCard } from "./components/PlayerPartySheetCard";
import type { PlayerPartySelectedItem } from "./playerParty.types";

export const PlayerPartyPage = () => {
  const { partyId } = useParams<{ partyId: string }>();
  const navigate = useNavigate();
  const { t } = useLocale();
  const { user } = useAuth();

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
  const wasLobbyRef = useRef(false);
  const prevActiveSessionIdRef = useRef<string | null>(null);

  const [hasCharacterSheet, setHasCharacterSheet] = useState<boolean | null>(null);

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
    } catch {
      setParty(null);
    } finally {
      setLoading(false);
    }
  }, [partyId]);

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
    if (!partyId) return;
    characterSheetsRepo
      .getByParty(partyId)
      .then(() => setHasCharacterSheet(true))
      .catch((error: { status?: number }) =>
        setHasCharacterSheet(error?.status === 404 ? false : null),
      );
  }, [partyId]);

  const { lastEvent } = useCampaignEvents(party?.campaignId ?? null);
  const activeSession = sessions.find((session) => session.isActive) ?? null;

  useEffect(() => {
    if (activeSession?.id) {
      prevActiveSessionIdRef.current = activeSession.id;
    } else if (prevActiveSessionIdRef.current) {
      prevActiveSessionIdRef.current = null;
      navigate(routes.home, { replace: true });
    }
  }, [activeSession?.id, navigate]);

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

  useEffect(() => {
    if (!lastEvent) return;

    if (lastEvent.type === "session_started") {
      if (lastEvent.payload.partyId && partyId && lastEvent.payload.partyId !== partyId) {
        return;
      }
      setLobbyStatus(null);
      setHasJoinedLobby(false);
      void refreshSessions();
      if (partyId) {
        navigate(routes.board.replace(":partyId", partyId));
      }
      return;
    }

    if (lastEvent.type === "session_closed") {
      const eventPartyId =
        typeof lastEvent.payload.partyId === "string" ? lastEvent.payload.partyId : null;
      if (eventPartyId && partyId && eventPartyId !== partyId) {
        void refreshSessions();
        return;
      }
      setLobbyStatus(null);
      setHasJoinedLobby(false);
      navigate(routes.home, { replace: true });
      return;
    }

    if (lastEvent.type === "session_lobby") {
      if (lastEvent.payload.partyId && partyId && lastEvent.payload.partyId !== partyId) {
        return;
      }
      setLobbyStatus({
        sessionId: lastEvent.payload.sessionId,
        campaignId: lastEvent.payload.campaignId,
        partyId: lastEvent.payload.partyId,
        expected: lastEvent.payload.expectedPlayers,
        ready: lastEvent.payload.readyUserIds ?? [],
        readyCount: lastEvent.payload.readyCount ?? 0,
        totalCount:
          lastEvent.payload.totalCount ?? lastEvent.payload.expectedPlayers.length,
      });
      setHasJoinedLobby(false);
      void refreshActiveSession().then((session) => {
        if (!session) {
          void refreshSessions();
        }
      });
      return;
    }

    if (lastEvent.type === "party_member_updated") {
      void loadData();
      return;
    }

    if (lastEvent.type === "player_joined_lobby") {
      if (lastEvent.payload.partyId && partyId && lastEvent.payload.partyId !== partyId) {
        return;
      }
      setLobbyStatus((current) => {
        if (!current || current.sessionId !== lastEvent.payload.sessionId) {
          return current;
        }
        if (current.ready.includes(lastEvent.payload.userId)) {
          return current;
        }
        return {
          ...current,
          ready: [...current.ready, lastEvent.payload.userId],
          readyCount: lastEvent.payload.readyCount ?? current.readyCount + 1,
        };
      });
    }
  }, [lastEvent, loadData, navigate, partyId, refreshActiveSession, refreshSessions]);

  useEffect(() => {
    if (activeSession?.status === "LOBBY") {
      wasLobbyRef.current = true;
      return;
    }

    if (activeSession?.status === "ACTIVE" && wasLobbyRef.current && partyId) {
      navigate(routes.board.replace(":partyId", partyId), { replace: true });
      wasLobbyRef.current = false;
    }
  }, [activeSession?.status, navigate, partyId]);

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
      if (refreshedActive?.status === "ACTIVE" && partyId) {
        setHasJoinedLobby(false);
        navigate(routes.board.replace(":partyId", partyId), { replace: true });
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
  }, [activeSession?.id, activeSession?.status, navigate, partyId, refreshSessions]);

  const handleJoinLobby = async () => {
    if (!activeSession?.id || joiningLobby) return;
    setJoiningLobby(true);
    try {
      await sessionsRepo.joinLobby(activeSession.id);
      setHasJoinedLobby(true);
      if (user?.userId) {
        setLobbyStatus((current) => {
          if (!current || current.ready.includes(user.userId)) {
            return current;
          }
          return { ...current, ready: [...current.ready, user.userId] };
        });
      }
    } catch {
      // ignore
    } finally {
      setJoiningLobby(false);
    }
  };

  if (loading) {
    return (
      <section className="space-y-6 px-1">
        <p className="text-sm text-slate-500">{t("playerParty.loading")}</p>
      </section>
    );
  }

  if (!party) {
    return (
      <section className="space-y-4 px-1">
        <p className="text-sm text-slate-400">{t("playerParty.notFound")}</p>
        <Link
          to={routes.home}
          className="text-xs font-semibold uppercase tracking-[0.22em] text-limiar-200 transition hover:text-white"
        >
          ← {t("playerParty.backHome")}
        </Link>
      </section>
    );
  }

  const myMember = party.members.find((member) => member.userId === user?.userId);
  const isPlayer = myMember?.role === "PLAYER";
  const alreadyInLobby =
    hasJoinedLobby || !!(user?.userId && lobbyStatus?.ready.includes(user.userId));

  return (
    <>
      <section className="space-y-6">
        <PlayerPartyHeader
          partyName={party.name}
          memberCount={party.members.length}
          sessionsCount={sessions.length}
          createdAt={party.createdAt}
          hasCharacterSheet={hasCharacterSheet}
          sessionStatus={activeSession?.status ?? null}
        />

        <PlayerPartySessionCard
          activeSession={activeSession}
          lobbyStatus={lobbyStatus}
          alreadyInLobby={alreadyInLobby}
          joiningLobby={joiningLobby}
          onJoinLobby={handleJoinLobby}
          onEnterBoard={() =>
            navigate(routes.board.replace(":partyId", party.id))
          }
        />

        <PlayerPartySheetCard
          partyId={partyId ?? ""}
          isPlayer={isPlayer}
          hasCharacterSheet={hasCharacterSheet}
          isSessionActive={activeSession?.status === "ACTIVE"}
        />

        <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <PlayerPartyMembersCard
            members={party.members}
            currentUserId={user?.userId}
            readyUserIds={lobbyStatus?.ready ?? []}
          />

          <div className="space-y-6">
            <PlayerPartyInventoryCard
              inventory={myInventory}
              catalogItems={catalogItems}
              onSelectItem={setSelectedItem}
            />
            <PlayerPartySessionHistoryCard
              sessions={sessions}
              expandedSessionId={expandedSessionId}
              onToggleSession={setExpandedSessionId}
            />
          </div>
        </div>
      </section>

      <PlayerPartyItemModal
        selectedItem={selectedItem}
        onClose={() => setSelectedItem(null)}
      />
    </>
  );
};
