import type { CharacterSheetMode } from "../model/characterSheet.types";
import {
  ABILITY_SCORE_POOL,
  STANDARD_ARRAY,
} from "../constants";
import {
  computeAbilityScoreTotal,
  isStandardArrayDistribution,
} from "../utils/calculations";
import {
  acceptCharacterSheet,
  createCharacterSheetDraft,
  prepareCharacterSheetForSave,
  requestPlaySheetLevelUp,
  saveCharacterSheet,
  saveCharacterSheetDraft,
  savePlayCharacterSheet,
} from "../services/characterSheet.service";
import { stripClassLevelAbilityBonuses } from "../data/classFeatures";
import { stripRaceBonusesFromAbilities } from "./useCharacterSheet.creation";
import { hasUnresolvedCreationInventoryItems } from "../utils/creationEquipment";
import { hasUnresolvedCreationSpellSelections } from "../utils/creationSpells";
import { type CharacterSheetHookAction, type CharacterSheetHookState } from "./useCharacterSheet.state";

type SaveParams = {
  mode: CharacterSheetMode;
  partyId: string | null | undefined;
  state: Pick<CharacterSheetHookState, "sheet" | "remoteId" | "draftRecord" | "playSessionId" | "playPlayerUserId">;
  canEditPlay: boolean;
  creationDraftMode: boolean;
  creationDraftId: string | null;
  campaignId: string | null;
};

export function useCharacterSheetSave(
  params: SaveParams,
  dispatch: React.Dispatch<CharacterSheetHookAction>,
) {
  const save = async (draftName?: string) => {
    if (!params.partyId) return;

    if (params.mode === "creation" && hasUnresolvedCreationInventoryItems(params.state.sheet.inventory)) {
      dispatch({
        type: "saving_fail",
        error: "Every creation inventory item must come from the campaign catalog.",
      });
      return;
    }

    if (
      params.mode === "creation" &&
      hasUnresolvedCreationSpellSelections(
        params.state.sheet.spellcasting,
        params.state.sheet.class,
        params.campaignId,
      )
    ) {
      dispatch({
        type: "saving_fail",
        error: "Every creation spell must come from the spell catalog.",
      });
      return;
    }

    if (params.mode === "play") {
      if (!params.canEditPlay || !params.state.playSessionId || !params.state.playPlayerUserId) return;
      dispatch({ type: "saving_start" });
      try {
        const id = await savePlayCharacterSheet(
          params.state.playSessionId,
          params.state.playPlayerUserId,
          params.state.sheet,
        );
        dispatch({ type: "saving_success", id });
      } catch (error: unknown) {
        dispatch({
          type: "saving_fail",
          error: (error as { message?: string })?.message ?? "Failed to save",
        });
      }
      return;
    }

    if (params.mode === "creation") {
      if (!params.creationDraftId && !params.creationDraftMode) {
        const normalizedBaseAbilities = stripClassLevelAbilityBonuses(
          stripRaceBonusesFromAbilities(
            params.state.sheet.abilities,
            params.state.sheet.race,
            params.state.sheet.raceConfig,
          ),
          params.state.sheet.class,
          params.state.sheet.level,
        );
        if (!isStandardArrayDistribution(normalizedBaseAbilities)) {
          dispatch({
            type: "saving_fail",
            error: `Ability scores must follow Standard Array (${STANDARD_ARRAY.join(", ")}).`,
          });
          return;
        }
      }
    } else {
      const abilityTotal = computeAbilityScoreTotal(params.state.sheet.abilities);
      if (abilityTotal !== ABILITY_SCORE_POOL) {
        const diff = ABILITY_SCORE_POOL - abilityTotal;
        dispatch({
          type: "saving_fail",
          error:
            diff > 0
              ? `Ability scores must total ${ABILITY_SCORE_POOL} (remaining: ${diff}).`
              : `Ability scores must total ${ABILITY_SCORE_POOL} (over by ${Math.abs(diff)}).`,
        });
        return;
      }
    }

    const sheetToSave = prepareCharacterSheetForSave(params.state.sheet, params.mode);
    dispatch({ type: "saving_start" });
    try {
      if (params.creationDraftMode) {
        const normalizedDraftName = draftName?.trim() || params.state.draftRecord?.name || "Untitled Draft";
        const draft = params.creationDraftId
          ? await saveCharacterSheetDraft(
              params.partyId,
              params.creationDraftId,
              normalizedDraftName,
              sheetToSave,
            )
          : await createCharacterSheetDraft(
              params.partyId,
              normalizedDraftName,
              sheetToSave,
            );
        dispatch({
          type: "saving_success",
          id: draft.id,
          sheet: sheetToSave,
          draftRecord: draft,
        });
        return;
      }

      const record = await saveCharacterSheet(params.partyId, sheetToSave, params.state.remoteId ?? undefined);
      dispatch({
        type: "saving_success",
        id: record.id,
        sheet: sheetToSave,
        characterRecord: record,
      });
    } catch (error: unknown) {
      dispatch({
        type: "saving_fail",
        error: (error as { message?: string })?.message ?? "Failed to save",
      });
    }
  };

  return save;
}

export function useCharacterSheetLevelUp(
  params: {
    partyId: string | null | undefined;
    mode: CharacterSheetMode;
    canEditPlay: boolean;
    playPlayerUserId: string | null;
    requestingLevelUp: boolean;
  },
  dispatch: React.Dispatch<CharacterSheetHookAction>,
) {
  const requestLevelUp = async () => {
    if (!params.partyId || params.mode !== "play" || params.canEditPlay || !params.playPlayerUserId || params.requestingLevelUp) {
      return;
    }
    try {
      const result = await requestPlaySheetLevelUp(params.partyId, params.playPlayerUserId, true);
      dispatch({
        type: "load_success",
        sheet: result.sheet,
        id: result.id,
        playSessionId: result.sessionId,
        playCampaignId: result.campaignId,
        playPlayerUserId: params.playPlayerUserId,
      });
    } catch (error: unknown) {
      throw (error as { message?: string })?.message ?? "Failed to request level-up.";
    }
  };

  return requestLevelUp;
}

export function useCharacterSheetAccept(
  params: {
    partyId: string | null | undefined;
    mode: CharacterSheetMode;
    creationDraftId: string | null;
    creationPlayerUserId: string | null;
    characterRecord: { acceptedAt?: string | null; playerId?: string } | null;
    state: Pick<CharacterSheetHookState, "sheet" | "remoteId">;
  },
  dispatch: React.Dispatch<CharacterSheetHookAction>,
) {
  const acceptPendingSheet = async () => {
    if (
      !params.partyId ||
      params.mode !== "creation" ||
      params.creationDraftId ||
      params.creationPlayerUserId ||
      !params.characterRecord ||
      params.characterRecord.acceptedAt
    ) {
      return;
    }

    const record = await acceptCharacterSheet(params.partyId);
    dispatch({
      type: "load_success",
      sheet: params.state.sheet,
      id: record.id,
      characterRecord: record,
    });
  };

  return acceptPendingSheet;
}
