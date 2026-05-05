import type { OutOfCombatCastableSpell, OutOfCombatCastRequest, SessionStateRecord } from "../../entities/character";
import { http } from "./http";

export const sessionStatesRepo = {
  getMine: (sessionId: string) =>
    http.get<SessionStateRecord>(`/sessions/${sessionId}/state/me`),
  updateMineLoadout: (
    sessionId: string,
    payload: { currentWeaponId: string | null; equippedArmorItemId: string | null },
  ) =>
    http.put<SessionStateRecord>(`/sessions/${sessionId}/state/me/loadout`, payload),
  getByPlayer: (sessionId: string, playerUserId: string) =>
    http.get<SessionStateRecord>(`/sessions/${sessionId}/state/${playerUserId}`),
  updateByPlayer: (sessionId: string, playerUserId: string, state: unknown) =>
    http.put<SessionStateRecord>(`/sessions/${sessionId}/state/${playerUserId}`, { state }),
  clearConcentration: (sessionId: string, concentrationGroup?: string | null) =>
    http.post<SessionStateRecord>(`/sessions/${sessionId}/state/me/concentration/clear`, {
      concentrationGroup: concentrationGroup ?? null,
    }),

  removePersistedEffect: (sessionId: string, effectId: string) =>
    http.del<SessionStateRecord>(`/sessions/${sessionId}/state/me/effects/${effectId}`),
  prepareSpells: (sessionId: string, preparedSpellIds: string[]) =>
    http.post<SessionStateRecord>(`/sessions/${sessionId}/state/me/spells/prepare`, {
      preparedSpellIds,
    }),
  listCastableOutOfCombat: (sessionId: string) =>
    http.get<OutOfCombatCastableSpell[]>(
      `/sessions/${sessionId}/state/me/spells/castable-out-of-combat`,
    ),
  listCastableOutOfCombatForPlayer: (sessionId: string, playerUserId: string) =>
    http.get<OutOfCombatCastableSpell[]>(
      `/sessions/${sessionId}/state/${playerUserId}/spells/castable-out-of-combat`,
    ),
  castSpellOutOfCombat: (sessionId: string, req: OutOfCombatCastRequest) =>
    http.post<SessionStateRecord>(`/sessions/${sessionId}/state/me/spells/cast`, req),
  castSpellOutOfCombatForPlayer: (
    sessionId: string,
    playerUserId: string,
    req: OutOfCombatCastRequest,
  ) =>
    http.post<SessionStateRecord>(`/sessions/${sessionId}/state/${playerUserId}/spells/cast`, req),
};
