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
  action: "bought" | "sold";
  itemName: string;
  quantity: number;
  amountLabel?: string | null;
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
  rollType?: string | null;
  ability?: string | null;
  skill?: string | null;
  dc?: number | null;
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

export type RestActivityEvent = {
  type: "rest";
  userId?: string | null;
  username?: string | null;
  displayName?: string | null;
  action: "short_started" | "short_ended" | "long_started" | "long_ended";
  timestamp: string;
  sessionOffsetSeconds: number;
};

export type RewardActivityEvent = {
  type: "reward";
  userId?: string | null;
  username?: string | null;
  displayName?: string | null;
  action: "currency" | "item" | "xp";
  targetUserId?: string | null;
  targetDisplayName?: string | null;
  amountLabel?: string | null;
  itemName?: string | null;
  quantity?: number | null;
  currentXp?: number | null;
  nextLevelThreshold?: number | null;
  timestamp: string;
  sessionOffsetSeconds: number;
};

export type LevelUpActivityEvent = {
  type: "level_up";
  userId?: string | null;
  username?: string | null;
  displayName?: string | null;
  action: "requested" | "approved" | "denied";
  targetUserId?: string | null;
  targetDisplayName?: string | null;
  level: number;
  experiencePoints: number;
  pendingLevelUp: boolean;
  timestamp: string;
  sessionOffsetSeconds: number;
};

export type HitDiceActivityEvent = {
  type: "hit_dice";
  userId?: string | null;
  username?: string | null;
  displayName?: string | null;
  roll: number;
  healingApplied: number;
  currentHp: number;
  maxHp?: number | null;
  hitDiceRemaining: number;
  hitDiceTotal: number;
  hitDieType: string;
  timestamp: string;
  sessionOffsetSeconds: number;
};

export type ConsumableActivityEvent = {
  type: "consumable";
  userId?: string | null;
  username?: string | null;
  displayName?: string | null;
  itemName: string;
  targetUserId?: string | null;
  targetDisplayName?: string | null;
  targetKind: "player" | "session_entity";
  healingApplied: number;
  newHp?: number | null;
  maxHp?: number | null;
  remainingQuantity?: number | null;
  effectDice?: string | null;
  effectRolls: number[];
  effectRollSource?: "system" | "manual" | null;
  timestamp: string;
  sessionOffsetSeconds: number;
};

export type PlayerHpActivityEvent = {
  type: "player_hp";
  userId?: string | null;
  username?: string | null;
  displayName?: string | null;
  action: "damaged" | "healed" | "hp_set";
  targetUserId?: string | null;
  targetDisplayName?: string | null;
  currentHp?: number | null;
  previousHp?: number | null;
  delta?: number | null;
  maxHp?: number | null;
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
    copperValue: number;
  };
  grantedCurrency: {
    copperValue: number;
  };
};

export type SessionGrantItemResult = {
  playerUserId: string;
  itemId: string;
  itemName: string;
  quantity: number;
  inventoryItem: InventoryItem;
};

export type SessionGrantXpResult = {
  playerUserId: string;
  grantedAmount: number;
  currentXp: number;
  currentLevel: number;
  nextLevelThreshold: number | null;
};

export type SessionRestState = "exploration" | "short_rest" | "long_rest";

export type SessionUseHitDieResult = {
  sessionId: string;
  campaignId: string;
  partyId?: string | null;
  playerUserId: string;
  currentHp: number;
  maxHp: number;
  hitDiceRemaining: number;
  hitDiceTotal: number;
  hitDieType: string;
  roll: number;
  healingApplied: number;
  healingRolled: number;
  constitutionModifier: number;
};

export type SessionHealingConsumableTarget = {
  playerUserId: string;
  displayName: string;
  currentHp: number;
  maxHp: number;
  isSelf: boolean;
};

export type SessionUseConsumableResult = {
  sessionId: string;
  campaignId: string;
  partyId?: string | null;
  actorUserId: string;
  targetPlayerUserId: string;
  inventoryItemId?: string | null;
  itemId?: string | null;
  itemName: string;
  targetDisplayName: string;
  healingApplied: number;
  newHp: number;
  maxHp: number;
  remainingQuantity: number;
  effectDice?: string | null;
  effectBonus: number;
  effectRolls: number[];
  effectRollSource: "system" | "manual";
};

export type RollResolvedActivityEvent = {
  type: "roll_resolved";
  userId?: string | null;
  username?: string | null;
  displayName?: string | null;
  rollType: string;
  actorName: string;
  actorKind: string;
  ability?: string | null;
  skill?: string | null;
  rolls: number[];
  selectedRoll: number;
  total: number;
  modifierUsed: number;
  advantageMode: string;
  dc?: number | null;
  targetAc?: number | null;
  success?: boolean | null;
  isGmRoll: boolean;
  timestamp: string;
  sessionOffsetSeconds: number;
};

export type ActivityEvent =
  | RollActivityEvent
  | PurchaseActivityEvent
  | ShopActivityEvent
  | RollRequestActivityEvent
  | CombatActivityEvent
  | RestActivityEvent
  | RewardActivityEvent
  | LevelUpActivityEvent
  | HitDiceActivityEvent
  | ConsumableActivityEvent
  | PlayerHpActivityEvent
  | EntityActivityEvent
  | RollResolvedActivityEvent;

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
  restState: SessionRestState;
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
  listHealingConsumableTargets: (sessionId: string) =>
    http.get<SessionHealingConsumableTarget[]>(
      `/sessions/${sessionId}/consumables/healing-targets`,
    ),
  useConsumable: (
    sessionId: string,
    payload: {
      inventoryItemId: string;
      targetPlayerUserId?: string | null;
      rollSource?: "system" | "manual";
      manualRolls?: number[] | null;
    },
  ) => http.post<SessionUseConsumableResult>(`/sessions/${sessionId}/consumables/use`, payload),
  joinLobby: (sessionId: string) =>
    http.post<{ ok: boolean }>(`/sessions/${sessionId}/lobby/join`, {}),
  forceStartLobby: (sessionId: string) =>
    http.post<ActiveSession>(`/sessions/${sessionId}/lobby/force-start`, {}),
  grantCurrency: (
    sessionId: string,
    payload: {
      playerUserId: string;
      copperValue: number;
    },
  ) => http.post<SessionGrantCurrencyResult>(`/sessions/${sessionId}/grants/currency`, payload),
  grantItem: (
    sessionId: string,
    payload: { playerUserId: string; itemId: string; quantity?: number; notes?: string | null },
  ) => http.post<SessionGrantItemResult>(`/sessions/${sessionId}/grants/item`, payload),
  grantXp: (
    sessionId: string,
    payload: { playerUserId: string; amount: number },
  ) => http.post<SessionGrantXpResult>(`/sessions/${sessionId}/grants/xp`, payload),
  useHitDie: (sessionId: string) =>
    http.post<SessionUseHitDieResult>(`/sessions/${sessionId}/rest/use-hit-die`, {}),
};
