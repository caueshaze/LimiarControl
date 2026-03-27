import type { LocaleKey } from "../../shared/i18n";
import type { ActiveEffect, CombatParticipant } from "../../shared/api/combatRepo";
import type {
  CombatLogEntry,
  CombatParticipantView,
  CombatParticipantVitals,
} from "./types";
export { localizeCombatLogMessage } from "./combatLogLocalization";

const STATUS_LABELS: Record<CombatParticipant["status"], LocaleKey> = {
  active: "combatUi.status.active",
  downed: "combatUi.status.downed",
  stable: "combatUi.status.stable",
  dead: "combatUi.status.dead",
  defeated: "combatUi.status.defeated",
};

const EFFECT_KIND_LABELS: Record<Exclude<ActiveEffect["kind"], "condition">, LocaleKey> = {
  temp_ac_bonus: "combatUi.effect.temp_ac_bonus",
  attack_bonus: "combatUi.effect.attack_bonus",
  damage_bonus: "combatUi.effect.damage_bonus",
  advantage_on_attacks: "combatUi.effect.advantage_on_attacks",
  disadvantage_on_attacks: "combatUi.effect.disadvantage_on_attacks",
  dodging: "combatUi.effect.dodging",
  hidden: "combatUi.effect.hidden",
};

const CONDITION_LABELS: Record<NonNullable<ActiveEffect["condition_type"]>, LocaleKey> = {
  prone: "combatUi.condition.prone",
  poisoned: "combatUi.condition.poisoned",
  restrained: "combatUi.condition.restrained",
  blinded: "combatUi.condition.blinded",
  frightened: "combatUi.condition.frightened",
};

type BuildCombatParticipantViewsOptions = {
  currentTurnIndex: number;
  entityVitalsByRefId?: Record<string, CombatParticipantVitals | undefined>;
  participants: CombatParticipant[];
  playerVitalsByUserId?: Record<string, CombatParticipantVitals | undefined>;
  userId?: string | null;
};

export const buildCombatParticipantViews = ({
  currentTurnIndex,
  entityVitalsByRefId = {},
  participants,
  playerVitalsByUserId = {},
  userId = null,
}: BuildCombatParticipantViewsOptions): CombatParticipantView[] =>
  participants.map((participant, index) => {
    const vitals =
      participant.kind === "player"
        ? (participant.actor_user_id ? playerVitalsByUserId[participant.actor_user_id] : undefined)
        : entityVitalsByRefId[participant.ref_id];
    return {
      ...participant,
      activeEffects: participant.active_effects ?? [],
      currentHp: vitals?.currentHp ?? null,
      isCurrentTurn: currentTurnIndex === index,
      isSelf:
        Boolean(userId) &&
        (participant.actor_user_id === userId || participant.ref_id === userId),
      maxHp: vitals?.maxHp ?? null,
      turnResources: participant.turn_resources ?? null,
    };
  });

export const toCombatLogEntry = (
  payload: Record<string, unknown>,
  id: string,
): CombatLogEntry => ({
  actorUserId:
    typeof payload.actorUserId === "string" ? payload.actorUserId : null,
  id,
  message: typeof payload.message === "string" ? payload.message : "",
  source: typeof payload.source === "string" ? payload.source : null,
});

export const appendCombatLogEntries = (
  current: CombatLogEntry[],
  nextEntries: CombatLogEntry[],
  limit = 8,
) => {
  const merged = [...current];
  nextEntries.forEach((entry) => {
    if (!entry.message.trim()) {
      return;
    }
    const existingIndex = merged.findIndex((candidate) => candidate.id === entry.id);
    if (existingIndex >= 0) {
      merged[existingIndex] = entry;
      return;
    }
    merged.push(entry);
  });
  return merged.slice(-limit);
};

export const getCombatStatusLabel = (
  t: (key: LocaleKey) => string,
  status: CombatParticipant["status"],
) => t(STATUS_LABELS[status]);

export const getCombatEffectLabel = (
  t: (key: LocaleKey) => string,
  effect: ActiveEffect,
) => {
  const labelKey =
    effect.kind === "condition"
      ? effect.condition_type
        ? CONDITION_LABELS[effect.condition_type]
        : "combatUi.effect.condition"
      : EFFECT_KIND_LABELS[effect.kind];
  const label = t(labelKey);
  if (effect.numeric_value != null) {
    return `${label} ${effect.numeric_value > 0 ? "+" : ""}${effect.numeric_value}`;
  }
  if (effect.remaining_rounds != null) {
    return `${label} · ${effect.remaining_rounds}r`;
  }
  return label;
};

export const getTurnResourceLabel = (
  t: (key: LocaleKey) => string,
  resource: "action" | "bonus" | "reaction",
  used: boolean,
) => {
  const prefix =
    resource === "action"
      ? t("combatUi.turnResource.action")
      : resource === "bonus"
        ? t("combatUi.turnResource.bonus")
        : t("combatUi.turnResource.reaction");
  return `${prefix} ${used ? "X" : "✓"}`;
};
