import type { RollEvent } from "../../entities/roll";
import { http } from "./http";

export type RollActivityEvent = {
  type: "roll";
  userId?: string | null;
  username?: string | null;
  displayName?: string | null;
  expression: string;
  results: number[];
  total: number;
  label?: string | null;
  timestamp: string;
  sessionOffsetSeconds: number;
};

export type PurchaseActivityEvent = {
  type: "purchase";
  userId?: string | null;
  username?: string | null;
  displayName?: string | null;
  itemName: string;
  quantity: number;
  timestamp: string;
  sessionOffsetSeconds: number;
};

export type ActivityEvent = RollActivityEvent | PurchaseActivityEvent;

export type SessionJoinResponse = {
  campaignId: string;
  campaignName: string;
  gmName?: string | null;
  sessionId: string;
  memberId: string;
  displayName: string;
  roleMode: "GM" | "PLAYER";
};

export type LobbyPlayer = { userId: string; displayName: string };

export type LobbyStatus = {
  sessionId: string;
  expected: LobbyPlayer[];
  ready: string[];
};

export type SessionSummary = {
  id: string;
  campaignId: string;
  number: number;
  title?: string | null;
  partyId?: string | null;
  status: "LOBBY" | "ACTIVE" | "CLOSED";
  isActive: boolean;
  startedAt?: string | null;
  endedAt?: string | null;
  durationSeconds: number;
  createdAt: string;
  updatedAt?: string | null;
};

export type ActiveSession = SessionSummary;

export const sessionsRepo = {
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
  getActivity: (sessionId: string) =>
    http.get<ActivityEvent[]>(`/sessions/${sessionId}/activity`),
  manualRoll: (sessionId: string, payload: { expression: string; result: number; label?: string | null }) =>
    http.post<unknown>(`/sessions/${sessionId}/rolls/manual`, payload),
  getLobbyStatus: (sessionId: string) =>
    http.get<LobbyStatus>(`/sessions/${sessionId}/lobby`),
  joinLobby: (sessionId: string) =>
    http.post<{ ok: boolean }>(`/sessions/${sessionId}/lobby/join`, {}),
  forceStartLobby: (sessionId: string) =>
    http.post<ActiveSession>(`/sessions/${sessionId}/lobby/force-start`, {}),
};
