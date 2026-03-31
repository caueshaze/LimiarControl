import type {
  CharacterSheetRecord,
  PartyCharacterSheetDraftRecord,
} from "../../../entities/character";
import type { CharacterSheet } from "../model/characterSheet.types";
import { INITIAL_SHEET } from "../model/initialSheet";

export type CharacterSheetHookState = {
  sheet: CharacterSheet;
  loading: boolean;
  saving: boolean;
  isDirty: boolean;
  loadError: string | null;
  saveError: string | null;
  remoteId: string | null;
  characterRecord: CharacterSheetRecord | null;
  draftRecord: PartyCharacterSheetDraftRecord | null;
  importError: string | null;
  playSessionId: string | null;
  playCampaignId: string | null;
  playPlayerUserId: string | null;
};

export type CharacterSheetHookAction =
  | { type: "load_start" }
  | {
      type: "load_success";
      sheet: CharacterSheet;
      id: string | null;
      characterRecord?: CharacterSheetRecord | null;
      draftRecord?: PartyCharacterSheetDraftRecord | null;
      playSessionId?: string | null;
      playCampaignId?: string | null;
      playPlayerUserId?: string | null;
    }
  | { type: "load_fail"; error: string }
  | { type: "update_sheet"; updater: (sheet: CharacterSheet) => CharacterSheet }
  | { type: "saving_start" }
  | {
      type: "saving_success";
      id: string;
      sheet?: CharacterSheet;
      characterRecord?: CharacterSheetRecord | null;
      draftRecord?: PartyCharacterSheetDraftRecord | null;
    }
  | { type: "saving_fail"; error: string }
  | { type: "import_success"; sheet: CharacterSheet }
  | { type: "import_fail"; error: string }
  | { type: "reset" };

export const initialCharacterSheetHookState: CharacterSheetHookState = {
  sheet: INITIAL_SHEET,
  loading: true,
  saving: false,
  isDirty: false,
  loadError: null,
  saveError: null,
  remoteId: null,
  characterRecord: null,
  draftRecord: null,
  importError: null,
  playSessionId: null,
  playCampaignId: null,
  playPlayerUserId: null,
};

export function characterSheetHookReducer(
  state: CharacterSheetHookState,
  action: CharacterSheetHookAction,
): CharacterSheetHookState {
  switch (action.type) {
    case "load_start":
      return { ...state, loading: true, loadError: null };
    case "load_success":
      return {
        ...state,
        loading: false,
        sheet: action.sheet,
        remoteId: action.id,
        characterRecord: action.characterRecord ?? null,
        draftRecord: action.draftRecord ?? null,
        isDirty: false,
        playSessionId: action.playSessionId ?? null,
        playCampaignId: action.playCampaignId ?? null,
        playPlayerUserId: action.playPlayerUserId ?? null,
      };
    case "load_fail":
      return { ...state, loading: false, loadError: action.error };
    case "update_sheet":
      return { ...state, sheet: action.updater(state.sheet), isDirty: true };
    case "saving_start":
      return { ...state, saving: true, saveError: null };
    case "saving_success":
      return {
        ...state,
        saving: false,
        isDirty: false,
        remoteId: action.id,
        characterRecord: action.characterRecord ?? state.characterRecord,
        draftRecord: action.draftRecord ?? state.draftRecord,
        saveError: null,
        sheet: action.sheet ?? state.sheet,
      };
    case "saving_fail":
      return { ...state, saving: false, saveError: action.error };
    case "import_success":
      return { ...state, sheet: action.sheet, isDirty: true, importError: null };
    case "import_fail":
      return { ...state, importError: action.error };
    case "reset":
      return {
        ...state,
        sheet: INITIAL_SHEET,
        loading: false,
        saving: false,
        isDirty: false,
        loadError: null,
        saveError: null,
        importError: null,
        remoteId: state.remoteId,
        characterRecord: state.characterRecord,
        draftRecord: state.draftRecord,
        playSessionId: state.playSessionId,
        playCampaignId: state.playCampaignId,
        playPlayerUserId: state.playPlayerUserId,
      };
    default:
      return state;
  }
}
