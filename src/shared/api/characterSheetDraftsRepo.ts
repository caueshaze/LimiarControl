import { http } from "./http";
import type {
  CharacterSheetRecord,
  PartyCharacterSheetDraftRecord,
} from "../../entities/character";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";

export const characterSheetDraftsRepo = {
  list: (partyId: string) =>
    http.get<PartyCharacterSheetDraftRecord[]>(`/parties/${partyId}/character-sheet-drafts`),

  create: (partyId: string, payload: { name: string; data: CharacterSheet }) =>
    http.post<PartyCharacterSheetDraftRecord>(`/parties/${partyId}/character-sheet-drafts`, payload),

  get: (partyId: string, draftId: string) =>
    http.get<PartyCharacterSheetDraftRecord>(
      `/parties/${partyId}/character-sheet-drafts/${draftId}`,
    ),

  update: (
    partyId: string,
    draftId: string,
    payload: { name: string; data: CharacterSheet },
  ) =>
    http.put<PartyCharacterSheetDraftRecord>(
      `/parties/${partyId}/character-sheet-drafts/${draftId}`,
      payload,
    ),

  archive: (partyId: string, draftId: string) =>
    http.post<PartyCharacterSheetDraftRecord>(
      `/parties/${partyId}/character-sheet-drafts/${draftId}/archive`,
      {},
    ),

  restore: (partyId: string, draftId: string) =>
    http.post<PartyCharacterSheetDraftRecord>(
      `/parties/${partyId}/character-sheet-drafts/${draftId}/restore`,
      {},
    ),

  remove: (partyId: string, draftId: string) =>
    http.del<void>(`/parties/${partyId}/character-sheet-drafts/${draftId}`),

  derive: (partyId: string, draftId: string, playerUserId: string) =>
    http.post<CharacterSheetRecord>(
      `/parties/${partyId}/character-sheet-drafts/${draftId}/derive`,
      { playerUserId },
    ),
};
