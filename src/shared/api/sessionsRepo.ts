import type { RollEvent } from "../../entities/roll";
import type { InventoryItem } from "../../entities/inventory";
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

export type ShopActivityEvent = {
  type: "shop";
  userId?: string | null;
  username?: string | null;
  displayName?: string | null;
  action: "opened" | "closed";
  timestamp: string;
  sessionOffsetSeconds: number;
};

export type RollRequestActivityEvent = {
  type: "roll_request";
  userId?: string | null;
  username?: string | null;
  displayName?: string | null;
  expression: string;
  reason?: string | null;
  mode?: "advantage" | "disadvantage" | null;
  targetUserId?: string | null;
  targetDisplayName?: string | null;
  timestamp: string;
  sessionOffsetSeconds: number;
};

export type CombatActivityEvent = {
  type: "combat";
  userId?: string | null;
  username?: string | null;
  displayName?: string | null;
  action: "started" | "ended";
  note?: string | null;
  timestamp: string;
  sessionOffsetSeconds: number;
};

export type EntityActivityEvent = {
  type: "entity";
  userId?: string | null;
  username?: string | null;
  displayName?: string | null;
  action: "added" | "removed" | "revealed" | "hidden" | "damaged" | "healed" | "hp_set";
  entityName: string;
  entityCategory?: string | null;
  label?: string | null;
  currentHp?: number | null;
  previousHp?: number | null;
  delta?: number | null;
  maxHp?: number | null;
  timestamp: string;
  sessionOffsetSeconds: number;
};

export type SessionGrantCurrencyResult = {
  playerUserId: string;
  currentCurrency: {
    cp: number;
    sp: number;
    ep: number;
    gp: number;
    pp: number;
  };
  grantedCurrency: {
    cp: number;
    sp: number;
    ep: number;
    gp: number;
    pp: number;
  };
};

export type SessionGrantItemResult = {
  playerUserId: string;
  itemId: string;
  itemName: string;
  quantity: number;
  inventoryItem: InventoryItem;
};

export type ActivityEvent =
  | RollActivityEvent
  | PurchaseActivityEvent
  | ShopActivityEvent
  | RollRequestActivityEvent
  | CombatActivityEvent
  | EntityActivityEvent;

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
  campaignId?: string | null;
  partyId?: string | null;
  expected: LobbyPlayer[];
  ready: string[];
  readyCount: number;
  totalCount: number;
};

export type SessionRuntime = {
  sessionId: string;
  campaignId: string;
  partyId?: string | null;
  status: "LOBBY" | "ACTIVE" | "CLOSED";
  shopOpen: boolean;
  combatActive: boolean;
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
  submitRoll: (
    sessionId: string,
    payload: { expression: string; label?: string | null; advantage?: "advantage" | "disadvantage" | null },
  ) => http.post<RollEvent>(`/sessions/${sessionId}/rolls`, payload),
  getActivity: (sessionId: string) =>
    http.get<ActivityEvent[]>(`/sessions/${sessionId}/activity`),
  manualRoll: (sessionId: string, payload: { expression: string; result: number; label?: string | null }) =>
    http.post<unknown>(`/sessions/${sessionId}/rolls/manual`, payload),
  getLobbyStatus: (sessionId: string) =>
    http.get<LobbyStatus>(`/sessions/${sessionId}/lobby`),
  getRuntime: (sessionId: string) =>
    http.get<SessionRuntime>(`/sessions/${sessionId}/runtime`),
  joinLobby: (sessionId: string) =>
    http.post<{ ok: boolean }>(`/sessions/${sessionId}/lobby/join`, {}),
  forceStartLobby: (sessionId: string) =>
    http.post<ActiveSession>(`/sessions/${sessionId}/lobby/force-start`, {}),
  grantCurrency: (
    sessionId: string,
    payload: {
      playerUserId: string;
      currency: { cp?: number; sp?: number; ep?: number; gp?: number; pp?: number };
    },
  ) => http.post<SessionGrantCurrencyResult>(`/sessions/${sessionId}/grants/currency`, payload),
  grantItem: (
    sessionId: string,
    payload: { playerUserId: string; itemId: string; quantity?: number; notes?: string | null },
  ) => http.post<SessionGrantItemResult>(`/sessions/${sessionId}/grants/item`, payload),
};
