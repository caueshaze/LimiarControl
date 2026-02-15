import type { RollEvent } from "../../entities/roll";
import { http } from "./http";

export type SessionJoinResponse = {
  campaignId: string;
  campaignName: string;
  gmName?: string | null;
  sessionId: string;
  memberId: string;
  displayName: string;
  roleMode: "GM" | "PLAYER";
};

export type SessionSummary = {
  id: string;
  campaignId: string;
  number: number;
  title?: string | null;
  joinCode?: string | null;
  status: "ACTIVE" | "CLOSED";
  isActive: boolean;
  startedAt?: string | null;
  endedAt?: string | null;
  durationSeconds: number;
  createdAt: string;
  updatedAt?: string | null;
};

export type ActiveSession = SessionSummary;

export const sessionsRepo = {
  join: (payload: { joinCode: string }) =>
    http.post<SessionJoinResponse>("/sessions/join", payload),
  getActive: (campaignId: string) =>
    http.get<ActiveSession>(`/campaigns/${campaignId}/sessions/active`),
  list: (campaignId: string) =>
    http.get<SessionSummary[]>(`/campaigns/${campaignId}/sessions`),
  activate: (campaignId: string, payload: { title: string }) =>
    http.post<ActiveSession>(`/campaigns/${campaignId}/sessions`, payload),
  end: (sessionId: string) =>
    http.post<ActiveSession>(`/sessions/${sessionId}/close`, {}),
  resume: (sessionId: string) =>
    http.post<ActiveSession>(`/sessions/${sessionId}/resume`, {}),
  command: (sessionId: string, payload: { type: string; payload?: Record<string, unknown> }) =>
    http.post<{ ok: boolean }>(`/sessions/${sessionId}/commands`, payload),
  rolls: (sessionId: string, limit = 50) =>
    http.get<RollEvent[]>(`/sessions/${sessionId}/rolls?limit=${limit}`),
};
