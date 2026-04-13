import type {
  CharacterSheetRecord,
  PartyCharacterSheetDraftRecord,
} from "../../../entities/character";
import { characterSheetsRepo } from "../../../shared/api/characterSheetsRepo";
import { characterSheetDraftsRepo } from "../../../shared/api/characterSheetDraftsRepo";
import { sessionStatesRepo } from "../../../shared/api/sessionStatesRepo";
import { partiesRepo } from "../../../shared/api/partiesRepo";
import { parseCharacterSheet } from "../model/characterSheet.schema";
import { INITIAL_SHEET } from "../model/initialSheet";
import type { CharacterSheet } from "../model/characterSheet.types";
import { applyCanonicalClassState } from "../data/classFeatures";
import { normalizeRaceState } from "../data/races";
import {
  applyCreationLoadoutToSheet,
  syncCreationInventoryLoadoutState,
} from "../utils/creationEquipment";
import { loadCreationItemCatalog } from "../utils/creationItemCatalog";
import { loadSpellCatalog } from "../../../entities/dnd-base";

/**
 * Carrega a ficha do player autenticado para um party.
 * 404 → ficha ainda não existe: retorna INITIAL_SHEET com id=null (save fará POST).
 * Outros erros → lança para o hook tratar.
 * O fluxo: API → unknown → parseCharacterSheet → CharacterSheet
 */
export async function loadCharacterSheet(
  partyId: string,
  mode: "creation" | "play" = "creation",
  campaignId?: string | null,
): Promise<{ id: string | null; sheet: CharacterSheet; record: CharacterSheetRecord | null }> {
  if (mode === "creation") {
    await Promise.all([
      loadCreationItemCatalog(campaignId),
      loadSpellCatalog(campaignId),
    ]);
  }

  try {
    const record = await characterSheetsRepo.getByParty(partyId);
    const sheet = parseCharacterSheet(record.data); // unknown → CharacterSheet (valida ou lança)
    return {
      id: record.id,
      sheet: mode === "creation" ? syncCreationInventoryLoadoutState(sheet) : sheet,
      record,
    };
  } catch (err: unknown) {
    if ((err as { status?: number })?.status === 404) {
      const sheet = mode === "creation" ? applyCreationLoadoutToSheet(INITIAL_SHEET) : INITIAL_SHEET;
      return { id: null, sheet, record: null };
    }
    throw err;
  }
}

export async function loadCharacterSheetForPlayer(
  partyId: string,
  playerUserId: string,
  campaignId?: string | null,
): Promise<{ id: string | null; sheet: CharacterSheet; record: CharacterSheetRecord }> {
  await Promise.all([
    loadCreationItemCatalog(campaignId),
    loadSpellCatalog(campaignId),
  ]);

  const record = await characterSheetsRepo.getForPlayer(partyId, playerUserId);
  return {
    id: record.id,
    sheet: syncCreationInventoryLoadoutState(parseCharacterSheet(record.data)),
    record,
  };
}

export async function loadCharacterSheetDraft(
  partyId: string,
  draftId: string,
  campaignId?: string | null,
): Promise<{ id: string; sheet: CharacterSheet; draft: PartyCharacterSheetDraftRecord }> {
  await Promise.all([
    loadCreationItemCatalog(campaignId),
    loadSpellCatalog(campaignId),
  ]);

  const draft = await characterSheetDraftsRepo.get(partyId, draftId);
  return {
    id: draft.id,
    sheet: syncCreationInventoryLoadoutState(parseCharacterSheet(draft.data)),
    draft,
  };
}

const normalizeCharacterSheetForPersistence = (sheet: CharacterSheet): CharacterSheet => {
  const normalizedRace = normalizeRaceState(sheet.race, sheet.raceConfig);
  return applyCanonicalClassState({
    ...sheet,
    race: normalizedRace.raceId,
    raceConfig: normalizedRace.raceConfig,
  });
};

export const prepareCharacterSheetForSave = (
  sheet: CharacterSheet,
  mode: "creation" | "play",
): CharacterSheet =>
  mode === "creation"
    ? syncCreationInventoryLoadoutState(normalizeCharacterSheetForPersistence(sheet))
    : normalizeCharacterSheetForPersistence(sheet);

/**
 * Salva a ficha: cria (POST) se não existir, atualiza (PUT) se já existir.
 * Retorna o ID remoto da ficha.
 */
export async function saveCharacterSheet(
  partyId: string,
  sheet: CharacterSheet,
  remoteId?: string,
): Promise<CharacterSheetRecord> {
  if (remoteId) {
    return characterSheetsRepo.update(partyId, sheet);
  }
  return characterSheetsRepo.create(partyId, sheet);
}

export async function saveCharacterSheetDraft(
  partyId: string,
  draftId: string,
  draftName: string,
  sheet: CharacterSheet,
): Promise<PartyCharacterSheetDraftRecord> {
  return characterSheetDraftsRepo.update(partyId, draftId, {
    name: draftName,
    data: sheet,
  });
}

export async function createCharacterSheetDraft(
  partyId: string,
  draftName: string,
  sheet: CharacterSheet,
): Promise<PartyCharacterSheetDraftRecord> {
  return characterSheetDraftsRepo.create(partyId, {
    name: draftName,
    data: sheet,
  });
}

export async function acceptCharacterSheet(
  partyId: string,
): Promise<CharacterSheetRecord> {
  return characterSheetsRepo.accept(partyId);
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
  const record = await sessionStatesRepo.updateByPlayer(
    sessionId,
    playerUserId,
    normalizeCharacterSheetForPersistence(sheet),
  );
  return record.id;
}

export async function requestPlaySheetLevelUp(
  partyId: string,
  playerUserId: string,
  useOwnState: boolean,
): Promise<{ id: string | null; sheet: CharacterSheet; sessionId: string; campaignId: string }> {
  await characterSheetsRepo.requestLevelUp(partyId);
  return loadPlayCharacterSheet(partyId, playerUserId, useOwnState);
}
