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
  /** Optional combat target context for debug explanations. */
  targetParticipantId?: string | null;
  /** Debug-only modifier explanations shown in the authoritative dialog. */
  debugModifiers?: Array<{
    source_label: string;
    modifier_type: "advantage" | "disadvantage";
    roll_type: "ability" | "skill";
    ability?: string | null;
    skill?: string | null;
    against?: "any" | "effect_target" | "selected_target" | null;
    selected_target_participant_id?: string | null;
    selected_target_display_name?: string | null;
    applied: boolean;
    skip_reason?: "target_mismatch" | "ability_mismatch" | "skill_mismatch" | "missing_target" | null;
  }> | null;
};

export type PlayerBoardStatusSummary = {
  ac: number;
  baseCarryingCapacityKg: number;
  carryingCapacityKg: number;
  carryingCapacitySources?: Array<{ label: string; multiplier: number }> | null;
  currentHp: number;
  currentWeapon: PlayerBoardWeaponSummary | null;
  deathSaveFailures: number;
  deathSaveSuccesses: number;
  encumbranceTier: "normal" | "encumbered" | "heavily_encumbered" | "overloaded";
  encumbranceNormalMaxKg: number;
  encumbranceEncumberedMaxKg: number;
  encumbranceHeavilyEncumberedMaxKg: number;
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
  passivePerceptionBonus?: number | null;
  passivePerceptionBonusSources?: Array<{ label: string; value: number }> | null;
  pushDragLiftKg: number;
  spellAttack: number | null;
  spellSaveDC: number | null;
  tempHp: number;
  totalWeightKg: number;
  xpPercent: number;
};

export type PlayerBoardWeaponSummary = {
  attackBonus: number;
  damageLabel: string;
  name: string;
  proficient: boolean;
  rangeMeters: number | null;
  rangeLongMeters: number | null;
  isRanged: boolean;
};

const normalizeTimestamp = (ts: string): string =>
  ts.replace(/\+00:00$/, "Z");

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
    normalizeTimestamp(payload.timestamp),
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
