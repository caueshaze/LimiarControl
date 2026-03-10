import type { SessionStateRecord } from "../../entities/character";
import { http } from "./http";

export const sessionStatesRepo = {
  getMine: (sessionId: string) =>
    http.get<SessionStateRecord>(`/sessions/${sessionId}/state/me`),
  getByPlayer: (sessionId: string, playerUserId: string) =>
    http.get<SessionStateRecord>(`/sessions/${sessionId}/state/${playerUserId}`),
  updateByPlayer: (sessionId: string, playerUserId: string, state: unknown) =>
    http.put<SessionStateRecord>(`/sessions/${sessionId}/state/${playerUserId}`, { state }),
};
