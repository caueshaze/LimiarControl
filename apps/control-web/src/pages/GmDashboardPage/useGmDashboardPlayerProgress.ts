import { useCallback, useEffect, useState } from "react";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import { parseCharacterSheet } from "../../features/character-sheet/model/characterSheet.schema";
import type { CampaignEvent } from "../../features/sessions/hooks/useCampaignEvents";
import { sessionStatesRepo } from "../../shared/api/sessionStatesRepo";
import type { ActiveSession } from "../../shared/api/sessionsRepo";
import type { PartyMemberSummary } from "../../shared/api/partiesRepo";

type Props = {
  activeSession: ActiveSession | null;
  lastEvent: CampaignEvent | null;
  partyPlayers: PartyMemberSummary[];
};

export const useGmDashboardPlayerProgress = ({
  activeSession,
  lastEvent,
  partyPlayers,
}: Props) => {
  const [playerSheetByUserId, setPlayerSheetByUserId] = useState<Record<string, CharacterSheet>>({});

  const refreshPlayerSheet = useCallback(async (userId: string) => {
    if (!activeSession?.id) return;
    try {
      const state = await sessionStatesRepo.getByPlayer(activeSession.id, userId);
      const sheet = parseCharacterSheet(state.state);
      setPlayerSheetByUserId((current) => ({ ...current, [userId]: sheet }));
    } catch {
      setPlayerSheetByUserId((current) => {
        const next = { ...current };
        delete next[userId];
        return next;
      });
    }
  }, [activeSession?.id]);

  useEffect(() => {
    if (!activeSession?.id || partyPlayers.length === 0) {
      setPlayerSheetByUserId({});
      return;
    }

    void Promise.all(partyPlayers.map((player) => refreshPlayerSheet(player.userId)));
  }, [activeSession?.id, partyPlayers, refreshPlayerSheet]);

  useEffect(() => {
    if (!lastEvent) return;
    const eventUserId =
      typeof (lastEvent.payload as { playerUserId?: unknown } | null | undefined)?.playerUserId === "string"
        ? (lastEvent.payload as { playerUserId: string }).playerUserId
        : null;
    if (!eventUserId) return;
    if (!partyPlayers.some((player) => player.userId === eventUserId)) return;

    if (
      lastEvent.type === "gm_granted_xp" ||
      lastEvent.type === "level_up_requested" ||
      lastEvent.type === "level_up_approved" ||
      lastEvent.type === "level_up_denied" ||
      lastEvent.type === "session_state_updated"
    ) {
      void refreshPlayerSheet(eventUserId);
    }
  }, [lastEvent, partyPlayers, refreshPlayerSheet]);

  return {
    playerSheetByUserId,
    refreshPlayerSheet,
  };
};
