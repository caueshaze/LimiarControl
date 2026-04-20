import { useRef, useState, useReducer, useEffect } from "react";
import type {
  AbilityName,
  CharacterSheet,
  CharacterSheetMode,
} from "../model/characterSheet.types";
import { validateSheet } from "../model/characterSheet.schema";
import { safeParseInt } from "../utils/calculations";
import { createBaseSheetActions } from "./useCharacterSheetActions.base";
import { createCreationSheetActions } from "./useCharacterSheetActions.creation";
import {
  buildCreationSetAbility,
  buildCreationSetField,
} from "./useCharacterSheet.setters";
import {
  characterSheetHookReducer,
  initialCharacterSheetHookState,
} from "./useCharacterSheet.state";
import { useCharacterSheetLoader } from "./useCharacterSheetLoader";
import { useCharacterSheetRealtime } from "./useCharacterSheetRealtime";
import {
  useCharacterSheetAccept,
  useCharacterSheetLevelUp,
  useCharacterSheetSave,
} from "./useCharacterSheetSave";

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

  const loadSheet = useCharacterSheetLoader(
    {
      partyId,
      mode,
      playPlayerUserId,
      creationDraftId,
      creationDraftMode,
      creationPlayerUserId,
      canEditPlay,
      campaignId,
    },
    dispatch,
  );

  useEffect(() => {
    creationRealtimeStateRef.current = {
      isDirty: state.isDirty,
      remoteId: state.remoteId,
      characterRecordPlayerId: state.characterRecord?.playerId ?? null,
    };
  }, [state.characterRecord?.playerId, state.isDirty, state.remoteId]);

  useCharacterSheetRealtime(
    {
      mode,
      canEditPlay,
      state,
      loadSheet,
      playEventVersionRef,
      creationEventVersionRef,
      creationRealtimeStateRef,
      creationDraftMode,
      creationDraftId,
      creationPlayerUserId,
      campaignId,
      partyId: partyId ?? null,
    },
    dispatch,
  );

  const save = useCharacterSheetSave(
    {
      mode,
      partyId,
      state,
      canEditPlay,
      creationDraftMode,
      creationDraftId,
      campaignId,
    },
    dispatch,
  );

  const requestLevelUpAction = useCharacterSheetLevelUp(
    { partyId, mode, canEditPlay, playPlayerUserId, requestingLevelUp },
    dispatch,
  );
  const requestLevelUp = async () => {
    setRequestingLevelUp(true);
    setRequestLevelUpError(null);
    try {
      await requestLevelUpAction();
    } catch (error: unknown) {
      setRequestLevelUpError((error as { message?: string })?.message ?? "Failed to request level-up.");
    } finally {
      setRequestingLevelUp(false);
    }
  };

  const acceptPendingSheetAction = useCharacterSheetAccept(
    { partyId, mode, creationDraftId, creationPlayerUserId, characterRecord: state.characterRecord, state },
    dispatch,
  );
  const acceptPendingSheet = async () => {
    if (acceptingSheet) return;
    setAcceptingSheet(true);
    setAcceptSheetError(null);
    try {
      await acceptPendingSheetAction();
    } catch (error: unknown) {
      setAcceptSheetError(
        (error as { message?: string })?.message ?? "Failed to accept character sheet.",
      );
    } finally {
      setAcceptingSheet(false);
    }
  };

  const set = <K extends keyof CharacterSheet>(key: K, value: CharacterSheet[K]) =>
    guardedUpdate((sheet) => buildCreationSetField(mode, campaignId)(sheet, key, value));

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
