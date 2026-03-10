import { http } from "./http";
import type { CharacterSheetRecord } from "../../entities/character";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";

export const characterSheetsRepo = {
  /** GET /parties/:partyId/character-sheet/me — carrega a ficha do player autenticado */
  getByParty: (partyId: string) =>
    http.get<CharacterSheetRecord>(`/parties/${partyId}/character-sheet/me`),

  /** POST /parties/:partyId/character-sheet — cria nova ficha */
  create: (partyId: string, data: CharacterSheet) =>
    http.post<CharacterSheetRecord>(`/parties/${partyId}/character-sheet`, { data }),

  /** PUT /parties/:partyId/character-sheet/me — atualiza ficha existente */
  update: (partyId: string, data: CharacterSheet) =>
    http.put<CharacterSheetRecord>(`/parties/${partyId}/character-sheet/me`, { data }),

  /** DELETE /parties/:partyId/character-sheet/me */
  delete: (partyId: string) =>
    http.del<void>(`/parties/${partyId}/character-sheet/me`),
};
