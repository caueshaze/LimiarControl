import { characterSheetsRepo } from "../../../shared/api/characterSheetsRepo";
import { sessionStatesRepo } from "../../../shared/api/sessionStatesRepo";
import { partiesRepo } from "../../../shared/api/partiesRepo";
import { parseCharacterSheet } from "../model/characterSheet.schema";
import { INITIAL_SHEET } from "../model/initialSheet";
import type { CharacterSheet } from "../model/characterSheet.types";

/**
 * Carrega a ficha do player autenticado para um party.
 * 404 → ficha ainda não existe: retorna INITIAL_SHEET com id=null (save fará POST).
 * Outros erros → lança para o hook tratar.
 * O fluxo: API → unknown → parseCharacterSheet → CharacterSheet
 */
export async function loadCharacterSheet(
  partyId: string,
): Promise<{ id: string | null; sheet: CharacterSheet }> {
  try {
    const record = await characterSheetsRepo.getByParty(partyId);
    const sheet = parseCharacterSheet(record.data); // unknown → CharacterSheet (valida ou lança)
    return { id: record.id, sheet };
  } catch (err: unknown) {
    if ((err as { status?: number })?.status === 404) {
      return { id: null, sheet: INITIAL_SHEET };
    }
    throw err;
  }
}

/**
 * Salva a ficha: cria (POST) se não existir, atualiza (PUT) se já existir.
 * Retorna o ID remoto da ficha.
 */
export async function saveCharacterSheet(
  partyId: string,
  sheet: CharacterSheet,
  remoteId?: string,
): Promise<string> {
  if (remoteId) {
    await characterSheetsRepo.update(partyId, sheet);
    return remoteId;
  }
  const record = await characterSheetsRepo.create(partyId, sheet);
  return record.id;
}

export async function loadPlayCharacterSheet(
  partyId: string,
  playerUserId: string,
  useOwnState: boolean,
): Promise<{ id: string | null; sheet: CharacterSheet; sessionId: string; campaignId: string }> {
  const activeSession = await partiesRepo.getPartyActiveSession(partyId);
  const record = useOwnState
    ? await sessionStatesRepo.getMine(activeSession.id)
    : await sessionStatesRepo.getByPlayer(activeSession.id, playerUserId);
  const sheet = parseCharacterSheet(record.state);
  return {
    id: record.id,
    sheet,
    sessionId: activeSession.id,
    campaignId: activeSession.campaignId,
  };
}

export async function savePlayCharacterSheet(
  sessionId: string,
  playerUserId: string,
  sheet: CharacterSheet,
): Promise<string> {
  const record = await sessionStatesRepo.updateByPlayer(sessionId, playerUserId, sheet);
  return record.id;
}
