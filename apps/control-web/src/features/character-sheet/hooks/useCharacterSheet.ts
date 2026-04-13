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
  acceptCharacterSheet,
  createCharacterSheetDraft,
  loadCharacterSheet,
  loadCharacterSheetDraft,
  loadCharacterSheetForPlayer,
  loadPlayCharacterSheet,
  prepareCharacterSheetForSave,
  requestPlaySheetLevelUp,
  saveCharacterSheet,
  saveCharacterSheetDraft,
  savePlayCharacterSheet,
} from "../services/characterSheet.service";
import { stripClassLevelAbilityBonuses } from "../data/classFeatures";
import { INITIAL_SHEET } from "../model/initialSheet";
import { createBaseSheetActions } from "./useCharacterSheetActions.base";
import { createCreationSheetActions } from "./useCharacterSheetActions.creation";
import {
  stripRaceBonusesFromAbilities,
} from "./useCharacterSheet.creation";
import { hasUnresolvedCreationInventoryItems, syncCreationInventoryLoadoutState } from "../utils/creationEquipment";
import { hasUnresolvedCreationSpellSelections } from "../utils/creationSpells";
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
  creationPlayerUserId?: string | null;
  creationDraftId?: string | null;
  creationDraftMode?: boolean;
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
  const creationEventVersionRef = useRef(0);
  const creationRealtimeStateRef = useRef({
    isDirty: false,
    remoteId: null as string | null,
    characterRecordPlayerId: null as string | null,
  });
  const [requestingLevelUp, setRequestingLevelUp] = useState(false);
  const [requestLevelUpError, setRequestLevelUpError] = useState<string | null>(null);
  const [acceptingSheet, setAcceptingSheet] = useState(false);
  const [acceptSheetError, setAcceptSheetError] = useState<string | null>(null);
  const playPlayerUserId = options.playPlayerUserId ?? null;
  const creationPlayerUserId = options.creationPlayerUserId ?? null;
  const creationDraftId = options.creationDraftId ?? null;
  const creationDraftMode = options.creationDraftMode ?? false;
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

      if (creationDraftId) {
        const [result] = await Promise.all([
          loadCharacterSheetDraft(partyId, creationDraftId, campaignId),
          preloadCreationCatalogs(campaignId),
        ]);
        dispatch({
          type: "load_success",
          sheet: syncCreationInventoryLoadoutState(result.sheet),
          id: result.id,
          draftRecord: result.draft,
        });
        return;
      }

      if (creationDraftMode) {
        await preloadCreationCatalogs(campaignId);
        dispatch({
          type: "load_success",
          sheet: syncCreationInventoryLoadoutState(INITIAL_SHEET),
          id: null,
          draftRecord: null,
        });
        return;
      }

      if (creationPlayerUserId) {
        const [result] = await Promise.all([
          loadCharacterSheetForPlayer(partyId, creationPlayerUserId, campaignId),
          preloadCreationCatalogs(campaignId),
        ]);
        dispatch({
          type: "load_success",
          sheet: syncCreationInventoryLoadoutState(result.sheet),
          id: result.id,
          characterRecord: result.record,
        });
        return;
      }

      const result = await loadCharacterSheet(partyId, mode, campaignId);
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
    partyId,
    mode,
    playPlayerUserId,
    creationDraftId,
    creationDraftMode,
    creationPlayerUserId,
    canEditPlay,
    campaignId,
  ]);

  useEffect(() => {
    void loadSheet();
  }, [loadSheet]);

  useEffect(() => {
    creationRealtimeStateRef.current = {
      isDirty: state.isDirty,
      remoteId: state.remoteId,
      characterRecordPlayerId: state.characterRecord?.playerId ?? null,
    };
  }, [state.characterRecord?.playerId, state.isDirty, state.remoteId]);

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
    state.remoteId,
    loadSheet,
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
    campaignId,
    creationDraftId,
    creationDraftMode,
    creationPlayerUserId,
    loadSheet,
    mode,
    partyId,
  ]);

  const save = async (draftName?: string) => {
    if (!partyId) return;

    if (mode === "creation" && hasUnresolvedCreationInventoryItems(state.sheet.inventory)) {
      dispatch({
        type: "saving_fail",
        error: "Every creation inventory item must come from the campaign catalog.",
      });
      return;
    }

    if (
      mode === "creation" &&
      hasUnresolvedCreationSpellSelections(
        state.sheet.spellcasting,
        state.sheet.class,
        campaignId,
      )
    ) {
      dispatch({
        type: "saving_fail",
        error: "Every creation spell must come from the spell catalog.",
      });
      return;
    }

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
      if (!creationDraftId && !creationDraftMode) {
        const normalizedBaseAbilities = stripClassLevelAbilityBonuses(
          stripRaceBonusesFromAbilities(
            state.sheet.abilities,
            state.sheet.race,
            state.sheet.raceConfig,
          ),
          state.sheet.class,
          state.sheet.level,
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
      if (creationDraftMode) {
        const normalizedDraftName = draftName?.trim() || state.draftRecord?.name || "Untitled Draft";
        const draft = creationDraftId
          ? await saveCharacterSheetDraft(
              partyId,
              creationDraftId,
              normalizedDraftName,
              sheetToSave,
            )
          : await createCharacterSheetDraft(
              partyId,
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

      const record = await saveCharacterSheet(partyId, sheetToSave, state.remoteId ?? undefined);
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

  const acceptPendingSheet = async () => {
    if (
      !partyId ||
      mode !== "creation" ||
      creationDraftId ||
      creationPlayerUserId ||
      !state.characterRecord ||
      state.characterRecord.acceptedAt ||
      acceptingSheet
    ) {
      return;
    }

    setAcceptingSheet(true);
    setAcceptSheetError(null);
    try {
      const record = await acceptCharacterSheet(partyId);
      dispatch({
        type: "load_success",
        sheet: state.sheet,
        id: record.id,
        characterRecord: record,
      });
    } catch (error: unknown) {
      setAcceptSheetError(
        (error as { message?: string })?.message ?? "Failed to accept character sheet.",
      );
    } finally {
      setAcceptingSheet(false);
    }
  };

  const setAbility = (ability: AbilityName, value: number) =>
    guardedUpdate((sheet) =>
      buildCreationSetAbility(mode, campaignId, {
        allowCreationEditing: creationDraftMode,
      })(sheet, ability, value),
    );

  const baseActions = createBaseSheetActions(guardedUpdate, set, mode, {
    allowCreationEditing: creationDraftMode,
    campaignId,
  });
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
    characterRecord: state.characterRecord,
    draftRecord: state.draftRecord,
    importError: state.importError,
    importRef,
    requestingLevelUp,
    requestLevelUpError,
    acceptingSheet,
    acceptSheetError,
    requestLevelUp,
    acceptPendingSheet,
    save,
    creationDraftMode,
    set,
    setAbility,
    ...baseActions,
    ...creationActions,
    safeParseInt,
    validateSheet,
  };
};

export type SheetActions = ReturnType<typeof useCharacterSheet>;
