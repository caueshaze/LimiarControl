import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import type {
  AbilityName,
  CharacterSheet,
  CharacterSheetMode,
} from "../model/characterSheet.types";
import { subscribe, getHistory } from "../../../shared/realtime/centrifugoClient";
import { validateSheet } from "../model/characterSheet.schema";
import {
  ABILITY_SCORE_POOL,
  STANDARD_ARRAY,
} from "../constants";
import {
  computeAbilityScoreTotal,
  isStandardArrayDistribution,
  safeParseInt,
} from "../utils/calculations";
import {
  loadCharacterSheet,
  loadPlayCharacterSheet,
  prepareCharacterSheetForSave,
  requestPlaySheetLevelUp,
  saveCharacterSheet,
  savePlayCharacterSheet,
} from "../services/characterSheet.service";
import { createBaseSheetActions } from "./useCharacterSheetActions.base";
import { createCreationSheetActions } from "./useCharacterSheetActions.creation";
import {
  stripRaceBonusesFromAbilities,
} from "./useCharacterSheet.creation";
import {
  buildCreationSetAbility,
  buildCreationSetField,
  preloadCreationCatalogs,
} from "./useCharacterSheet.setters";
import {
  characterSheetHookReducer,
  initialCharacterSheetHookState,
} from "./useCharacterSheet.state";

type UseCharacterSheetOptions = {
  playPlayerUserId?: string | null;
  canEditPlay?: boolean;
  campaignId?: string | null;
};

export const useCharacterSheet = (
  partyId?: string | null,
  mode: CharacterSheetMode = "play",
  options: UseCharacterSheetOptions = {},
) => {
  const [state, dispatch] = useReducer(
    characterSheetHookReducer,
    initialCharacterSheetHookState,
  );
  const importRef = useRef<HTMLInputElement>(null);
  const playEventVersionRef = useRef(0);
  const [requestingLevelUp, setRequestingLevelUp] = useState(false);
  const [requestLevelUpError, setRequestLevelUpError] = useState<string | null>(null);
  const playPlayerUserId = options.playPlayerUserId ?? null;
  const canEditPlay = options.canEditPlay ?? false;
  const campaignId = options.campaignId ?? null;
  const canMutate = mode !== "play" || canEditPlay;

  const update = (updater: (sheet: CharacterSheet) => CharacterSheet) =>
    dispatch({ type: "update_sheet", updater });

  const guardedUpdate = (updater: (sheet: CharacterSheet) => CharacterSheet) =>
    update((sheet) => (canMutate ? updater(sheet) : sheet));

  const loadSheet = useCallback(async () => {
    if (!partyId) {
      if (mode === "creation") {
        await preloadCreationCatalogs(campaignId);
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
      if (mode === "play") {
        if (!playPlayerUserId) {
          throw new Error("Missing player for play sheet.");
        }
        const result = await loadPlayCharacterSheet(partyId, playPlayerUserId, !canEditPlay);
        dispatch({
          type: "load_success",
          sheet: result.sheet,
          id: result.id,
          playSessionId: result.sessionId,
          playCampaignId: result.campaignId,
          playPlayerUserId,
        });
        return;
      }

      const result = await loadCharacterSheet(partyId, mode, campaignId);
      dispatch({ type: "load_success", sheet: result.sheet, id: result.id });
    } catch (error: unknown) {
      dispatch({
        type: "load_fail",
        error: (error as { message?: string })?.message ?? "Failed to load",
      });
    }
  }, [partyId, mode, playPlayerUserId, canEditPlay, campaignId]);

  useEffect(() => {
    void loadSheet();
  }, [loadSheet]);

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
        payload?: { sessionId?: string; playerUserId?: string };
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
        void loadSheet();
      }
    };

    const unsubscribe = subscribe(`campaign:${state.playCampaignId}`, {
      onSubscribed: () => {
        void getHistory(`campaign:${state.playCampaignId}`, 20)
          .then((publications) => {
            [...publications]
              .sort((left, right) => {
                const leftVersion =
                  typeof (left.data as { version?: unknown } | null | undefined)?.version === "number"
                    ? (left.data as { version: number }).version
                    : 0;
                const rightVersion =
                  typeof (right.data as { version?: unknown } | null | undefined)?.version === "number"
                    ? (right.data as { version: number }).version
                    : 0;
                return leftVersion - rightVersion;
              })
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
    loadSheet,
  ]);

  const save = async () => {
    if (!partyId) return;

    if (mode === "play") {
      if (!canEditPlay || !state.playSessionId || !state.playPlayerUserId) return;
      dispatch({ type: "saving_start" });
      try {
        const id = await savePlayCharacterSheet(
          state.playSessionId,
          state.playPlayerUserId,
          state.sheet,
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

    if (mode === "creation") {
      const baseAbilities = stripRaceBonusesFromAbilities(state.sheet.abilities, state.sheet.race);
      if (!isStandardArrayDistribution(baseAbilities)) {
        dispatch({
          type: "saving_fail",
          error: `Ability scores must follow Standard Array (${STANDARD_ARRAY.join(", ")}).`,
        });
        return;
      }
    } else {
      const abilityTotal = computeAbilityScoreTotal(state.sheet.abilities);
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

    const sheetToSave = prepareCharacterSheetForSave(state.sheet, mode);
    dispatch({ type: "saving_start" });
    try {
      const id = await saveCharacterSheet(partyId, sheetToSave, state.remoteId ?? undefined);
      dispatch({ type: "saving_success", id, sheet: sheetToSave });
    } catch (error: unknown) {
      dispatch({
        type: "saving_fail",
        error: (error as { message?: string })?.message ?? "Failed to save",
      });
    }
  };

  const set = <K extends keyof CharacterSheet>(key: K, value: CharacterSheet[K]) =>
    guardedUpdate((sheet) => buildCreationSetField(mode, campaignId)(sheet, key, value));

  const requestLevelUp = async () => {
    if (!partyId || mode !== "play" || canEditPlay || !playPlayerUserId || requestingLevelUp) {
      return;
    }

    setRequestingLevelUp(true);
    setRequestLevelUpError(null);
    try {
      const result = await requestPlaySheetLevelUp(partyId, playPlayerUserId, true);
      dispatch({
        type: "load_success",
        sheet: result.sheet,
        id: result.id,
        playSessionId: result.sessionId,
        playCampaignId: result.campaignId,
        playPlayerUserId,
      });
    } catch (error: unknown) {
      setRequestLevelUpError(
        (error as { message?: string })?.message ?? "Failed to request level-up.",
      );
    } finally {
      setRequestingLevelUp(false);
    }
  };

  const setAbility = (ability: AbilityName, value: number) =>
    guardedUpdate((sheet) => buildCreationSetAbility(mode, campaignId)(sheet, ability, value));

  const baseActions = createBaseSheetActions(guardedUpdate, set, mode);
  const creationActions = createCreationSheetActions({
    mode,
    campaignId,
    guardedUpdate,
    update,
    set,
    dispatch,
    importRef,
    sheet: state.sheet,
  });

  return {
    mode,
    sheet: state.sheet,
    loading: state.loading,
    saving: state.saving,
    isDirty: state.isDirty,
    loadError: state.loadError,
    saveError: state.saveError,
    remoteId: state.remoteId,
    importError: state.importError,
    importRef,
    requestingLevelUp,
    requestLevelUpError,
    requestLevelUp,
    save,
    set,
    setAbility,
    ...baseActions,
    ...creationActions,
    safeParseInt,
    validateSheet,
  };
};

export type SheetActions = ReturnType<typeof useCharacterSheet>;
