import type { SessionStateRecord } from "../../entities/character";
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
};
