import { useCallback, useEffect } from "react";
import type { CharacterSheetMode } from "../model/characterSheet.types";
import { validateSheet } from "../model/characterSheet.schema";
import { syncCreationInventoryLoadoutState } from "../utils/creationEquipment";
import { preloadCreationCatalogs } from "./useCharacterSheet.setters";
import {
  loadPlayCharacterSheet,
  loadCharacterSheetDraft,
  loadCharacterSheetForPlayer,
  loadCharacterSheet,
} from "../services/characterSheet.service";
import { INITIAL_SHEET } from "../model/initialSheet";
import {
  type CharacterSheetHookAction,
  initialCharacterSheetHookState,
} from "./useCharacterSheet.state";

type LoaderParams = {
  partyId?: string | null;
  mode: CharacterSheetMode;
  playPlayerUserId: string | null;
  creationDraftId: string | null;
  creationDraftMode: boolean;
  creationPlayerUserId: string | null;
  canEditPlay: boolean;
  campaignId: string | null;
};

export function useCharacterSheetLoader(
  params: LoaderParams,
  dispatch: React.Dispatch<CharacterSheetHookAction>,
) {
  const loadSheet = useCallback(async () => {
    if (!params.partyId) {
      if (params.mode === "creation") {
        await preloadCreationCatalogs(params.campaignId);
      }
      dispatch({
        type: "load_success",
        sheet: initialCharacterSheetHookState.sheet,
        id: null,
      });
      return;
    }

    dispatch({ type: "load_start" });
    try {
      if (params.mode === "play") {
        if (!params.playPlayerUserId) {
          throw new Error("Missing player for play sheet.");
        }
        const result = await loadPlayCharacterSheet(params.partyId, params.playPlayerUserId, !params.canEditPlay);
        dispatch({
          type: "load_success",
          sheet: result.sheet,
          id: result.id,
          playSessionId: result.sessionId,
          playCampaignId: result.campaignId,
          playPlayerUserId: params.playPlayerUserId,
        });
        return;
      }

      if (params.creationDraftId) {
        const [result] = await Promise.all([
          loadCharacterSheetDraft(params.partyId, params.creationDraftId, params.campaignId),
          preloadCreationCatalogs(params.campaignId),
        ]);
        dispatch({
          type: "load_success",
          sheet: syncCreationInventoryLoadoutState(result.sheet),
          id: result.id,
          draftRecord: result.draft,
        });
        return;
      }

      if (params.creationDraftMode) {
        await preloadCreationCatalogs(params.campaignId);
        dispatch({
          type: "load_success",
          sheet: syncCreationInventoryLoadoutState(INITIAL_SHEET),
          id: null,
          draftRecord: null,
        });
        return;
      }

      if (params.creationPlayerUserId) {
        const [result] = await Promise.all([
          loadCharacterSheetForPlayer(params.partyId, params.creationPlayerUserId, params.campaignId),
          preloadCreationCatalogs(params.campaignId),
        ]);
        dispatch({
          type: "load_success",
          sheet: syncCreationInventoryLoadoutState(result.sheet),
          id: result.id,
          characterRecord: result.record,
        });
        return;
      }

      const result = await loadCharacterSheet(params.partyId, params.mode, params.campaignId);
      dispatch({
        type: "load_success",
        sheet: result.sheet,
        id: result.id,
        characterRecord: result.record,
      });
    } catch (error: unknown) {
      dispatch({
        type: "load_fail",
        error: (error as { message?: string })?.message ?? "Failed to load",
      });
    }
  }, [
    params.partyId,
    params.mode,
    params.playPlayerUserId,
    params.creationDraftId,
    params.creationDraftMode,
    params.creationPlayerUserId,
    params.canEditPlay,
    params.campaignId,
  ]);

  useEffect(() => {
    void loadSheet();
  }, [loadSheet]);

  return loadSheet;
}
