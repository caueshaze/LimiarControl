import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useLocale } from "../../shared/hooks/useLocale";
import { useCampaignEvents } from "../../features/sessions";
import { useAuth } from "../../features/auth";
import { sessionsRepo } from "../../shared/api/sessionsRepo";
import { PlayerPartyHeader } from "./components/PlayerPartyHeader";
import { PlayerPartyInventoryCard } from "./components/PlayerPartyInventoryCard";
import { PlayerPartyItemModal } from "./components/PlayerPartyItemModal";
import { PlayerPartyMembersCard } from "./components/PlayerPartyMembersCard";
import { PlayerPartySessionCard } from "./components/PlayerPartySessionCard";
import { PlayerPartySessionHistoryCard } from "./components/PlayerPartySessionHistoryCard";
import { PlayerPartySheetCard } from "./components/PlayerPartySheetCard";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui";
import { usePlayerPartyPageData } from "./usePlayerPartyPageData";

export const PlayerPartyPage = () => {
  const { partyId } = useParams<{ partyId: string }>();
  const navigate = useNavigate();
  const { locale, t } = useLocale();
  const { user } = useAuth();
  const { toast, showToast, clearToast } = useToast();
  const {
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
  } = usePlayerPartyPageData({ partyId, userId: user?.userId });

  const { lastEvent } = useCampaignEvents(party?.campaignId ?? null);

  useEffect(() => {
    if (activeSession?.id) {
      prevActiveSessionIdRef.current = activeSession.id;
    } else if (prevActiveSessionIdRef.current) {
      prevActiveSessionIdRef.current = null;
      navigate(routes.home, { replace: true });
    }
  }, [activeSession?.id, navigate, prevActiveSessionIdRef]);

  useEffect(() => {
    if (!lastEvent) return;

    if (lastEvent.type === "session_started") {
      if (lastEvent.payload.partyId && partyId && lastEvent.payload.partyId !== partyId) {
        return;
      }
      setLobbyStatus(null);
      setHasJoinedLobby(false);
      notifiedLobbySessionIdRef.current = lastEvent.payload.sessionId;
      void syncActiveSessionFromRealtime(lastEvent.payload.sessionId);
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
      if (notifiedLobbySessionIdRef.current !== lastEvent.payload.sessionId) {
        notifiedLobbySessionIdRef.current = lastEvent.payload.sessionId;
        showToast({
          variant: "info",
          title:
            locale === "pt"
              ? "Sessao aberta pelo GM"
              : "GM opened the session",
          description:
            locale === "pt"
              ? `${lastEvent.payload.title} ja esta pronta na sala de espera.`
              : `${lastEvent.payload.title} is ready in the lobby.`,
          duration: 4500,
        });
      }
      void syncActiveSessionFromRealtime(lastEvent.payload.sessionId);
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
  }, [lastEvent, loadData, locale, navigate, partyId, refreshSessions, showToast, syncActiveSessionFromRealtime]);

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
      <Toast toast={toast} onClose={clearToast} />
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
