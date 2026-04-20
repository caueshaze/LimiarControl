import { useEffect, type RefObject } from "react";
import type { CharacterSheetMode } from "../model/characterSheet.types";
import { subscribe, getHistory } from "../../../shared/realtime/centrifugoClient";
import { validateSheet } from "../model/characterSheet.schema";
import { type CharacterSheetHookAction, type CharacterSheetHookState } from "./useCharacterSheet.state";

type RealtimeParams = {
  mode: CharacterSheetMode;
  canEditPlay: boolean;
  state: Pick<CharacterSheetHookState, "playCampaignId" | "playSessionId" | "playPlayerUserId" | "remoteId" | "characterRecord" | "isDirty">;
  loadSheet: () => Promise<void>;
  playEventVersionRef: RefObject<number>;
  creationEventVersionRef: RefObject<number>;
  creationRealtimeStateRef: RefObject<{
    isDirty: boolean;
    remoteId: string | null;
    characterRecordPlayerId: string | null;
  }>;
  creationDraftMode: boolean;
  creationDraftId: string | null;
  creationPlayerUserId: string | null;
  campaignId: string | null;
  partyId: string | null;
};

function sortPublicationsByVersion(publications: { data: unknown }[]) {
  return [...publications].sort((left, right) => {
    const leftVersion =
      typeof (left.data as { version?: unknown } | null | undefined)?.version === "number"
        ? (left.data as { version: number }).version
        : 0;
    const rightVersion =
      typeof (right.data as { version?: unknown } | null | undefined)?.version === "number"
        ? (right.data as { version: number }).version
        : 0;
    return leftVersion - rightVersion;
  });
}

export function useCharacterSheetRealtime(
  params: RealtimeParams,
  dispatch: React.Dispatch<CharacterSheetHookAction>,
) {
  const {
    mode, canEditPlay, state, loadSheet,
    playEventVersionRef, creationEventVersionRef, creationRealtimeStateRef,
    creationDraftMode, creationDraftId, creationPlayerUserId,
    campaignId, partyId,
  } = params;

  useEffect(() => {
    if (
      mode !== "play" ||
      canEditPlay ||
      !state.playCampaignId ||
      !state.playSessionId ||
      !state.playPlayerUserId
    ) {
      return;
    }

    playEventVersionRef.current = 0;
    const processRealtimeMessage = (message: unknown) => {
      if (!message || typeof message !== "object") return;
      const data = message as {
        type?: string;
        version?: number;
        payload?: { sessionId?: string; playerUserId?: string; state?: unknown };
      };
      if (
        data.type === "session_state_updated" &&
        data.payload?.sessionId === state.playSessionId &&
        data.payload?.playerUserId === state.playPlayerUserId
      ) {
        if (
          typeof data.version === "number" &&
          data.version <= playEventVersionRef.current
        ) {
          return;
        }
        if (typeof data.version === "number") {
          playEventVersionRef.current = data.version;
        }
        const snapshot = validateSheet(data.payload?.state);
        if (snapshot?.ok) {
          dispatch({
            type: "load_success",
            sheet: snapshot.sheet,
            id: state.remoteId,
            playSessionId: state.playSessionId,
            playCampaignId: state.playCampaignId,
            playPlayerUserId: state.playPlayerUserId,
          });
          return;
        }
        void loadSheet();
      }
    };

    const unsubscribe = subscribe(`campaign:${state.playCampaignId}`, {
      onSubscribed: () => {
        void getHistory(`campaign:${state.playCampaignId}`, 20)
          .then((publications) => {
            sortPublicationsByVersion(publications)
              .forEach((publication) => processRealtimeMessage(publication.data));
          })
          .catch(() => {});
      },
      onPublication: processRealtimeMessage,
    });

    return () => {
      unsubscribe();
    };
  }, [
    mode,
    canEditPlay,
    state.playCampaignId,
    state.playPlayerUserId,
    state.playSessionId,
    state.remoteId,
    loadSheet,
    playEventVersionRef,
  ]);

  useEffect(() => {
    if (
      mode !== "creation" ||
      creationDraftMode ||
      !!creationDraftId ||
      !campaignId ||
      !partyId
    ) {
      return;
    }

    creationEventVersionRef.current = 0;
    const processRealtimeMessage = (message: unknown) => {
      if (!message || typeof message !== "object") return;
      const data = message as {
        type?: string;
        version?: number;
        payload?: {
          partyId?: string | null;
          playerUserId?: string | null;
          updateKind?: string | null;
        };
      };
      if (data.type !== "character_sheet_updated") {
        return;
      }
      if (data.payload?.partyId !== partyId) {
        return;
      }
      if (
        typeof data.version === "number" &&
        data.version <= creationEventVersionRef.current
      ) {
        return;
      }
      if (typeof data.version === "number") {
        creationEventVersionRef.current = data.version;
      }

      const eventPlayerUserId = data.payload?.playerUserId ?? null;
      const currentRecordPlayerUserId = creationRealtimeStateRef.current.characterRecordPlayerId;
      const matchesTarget =
        creationPlayerUserId
          ? eventPlayerUserId === creationPlayerUserId
          : currentRecordPlayerUserId
            ? eventPlayerUserId === currentRecordPlayerUserId
            : true;

      if (!matchesTarget) {
        return;
      }

      const shouldReload =
        !creationRealtimeStateRef.current.isDirty ||
        !creationRealtimeStateRef.current.remoteId ||
        data.payload?.updateKind === "delivered" ||
        data.payload?.updateKind === "accepted";

      if (shouldReload) {
        void loadSheet();
      }
    };

    const unsubscribe = subscribe(`campaign:${campaignId}`, {
      onSubscribed: () => {
        void getHistory(`campaign:${campaignId}`, 20)
          .then((publications) => {
            sortPublicationsByVersion(publications)
              .forEach((publication) => processRealtimeMessage(publication.data));
          })
          .catch(() => {});
      },
      onPublication: processRealtimeMessage,
    });

    return () => {
      unsubscribe();
    };
  }, [
    campaignId,
    creationDraftId,
    creationDraftMode,
    creationPlayerUserId,
    loadSheet,
    mode,
    partyId,
    creationEventVersionRef,
    creationRealtimeStateRef,
  ]);
}
