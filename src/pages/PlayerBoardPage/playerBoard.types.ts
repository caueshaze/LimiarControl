export type PendingRoll = {
  requestKey: string;
  expression: string;
  issuedBy?: string;
  reason?: string;
  mode?: "advantage" | "disadvantage" | null;
  /** When present, the request uses the authoritative roll flow. */
  rollType?: "ability" | "save" | "skill" | "initiative" | "attack" | null;
  /** Ability for ability/save rolls. */
  ability?: string | null;
  /** Skill for skill rolls. */
  skill?: string | null;
  /** DC set by GM. */
  dc?: number | null;
};

export type PlayerBoardStatusSummary = {
  ac: number;
  currentHp: number;
  currentWeapon: PlayerBoardWeaponSummary | null;
  deathSaveFailures: number;
  deathSaveSuccesses: number;
  experiencePoints: number;
  hitDiceRemaining: number;
  hitDiceTotal: number;
  hitDieType: string;
  hpPercent: number;
  initiative: number;
  level: number;
  maxHp: number;
  nextLevelThreshold: number | null;
  passivePerception: number;
  spellAttack: number | null;
  spellSaveDC: number | null;
  tempHp: number;
  xpPercent: number;
};

export type PlayerBoardWeaponSummary = {
  attackBonus: number;
  damageLabel: string;
  name: string;
  proficient: boolean;
};

export const buildRollRequestKey = (payload: {
  expression: string;
  mode?: "advantage" | "disadvantage" | null;
  reason?: string | null;
  sessionId: string;
  targetUserId?: string | null;
  timestamp: string;
}) =>
  [
    payload.sessionId,
    payload.timestamp,
    payload.expression.trim(),
    payload.reason?.trim() ?? "",
    payload.mode ?? "",
    payload.targetUserId ?? "",
  ].join(":");

export const readHandledRollRequestKey = (sessionId: string | null | undefined) => {
  if (!sessionId || typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage.getItem(`limiar:handledRollRequest:${sessionId}`);
};

export const writeHandledRollRequestKey = (
  sessionId: string | null | undefined,
  requestKey: string,
) => {
  if (!sessionId || typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(`limiar:handledRollRequest:${sessionId}`, requestKey);
};
