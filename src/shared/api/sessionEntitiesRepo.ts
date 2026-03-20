import type {
  SessionEntity,
  SessionEntityPlayer,
  SessionEntityCreatePayload,
  SessionEntityUpdatePayload,
} from "../../entities/session-entity";
import { http } from "./http";

export const sessionEntitiesRepo = {
  list: (sessionId: string) =>
    http.get<SessionEntity[]>(`/sessions/${sessionId}/entities`),

  listVisible: (sessionId: string) =>
    http.get<SessionEntityPlayer[]>(`/sessions/${sessionId}/entities/visible`),

  add: (sessionId: string, payload: SessionEntityCreatePayload) =>
    http.post<SessionEntity>(`/sessions/${sessionId}/entities`, payload),

  update: (sessionId: string, sessionEntityId: string, payload: SessionEntityUpdatePayload) =>
    http.put<SessionEntity>(`/sessions/${sessionId}/entities/${sessionEntityId}`, payload),

  remove: (sessionId: string, sessionEntityId: string) =>
    http.del<void>(`/sessions/${sessionId}/entities/${sessionEntityId}`),

  reveal: (sessionId: string, sessionEntityId: string) =>
    http.post<SessionEntity>(`/sessions/${sessionId}/entities/${sessionEntityId}/reveal`, {}),

  hide: (sessionId: string, sessionEntityId: string) =>
    http.post<SessionEntity>(`/sessions/${sessionId}/entities/${sessionEntityId}/hide`, {}),
};
