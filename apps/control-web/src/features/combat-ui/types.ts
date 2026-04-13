import type {
  ActiveEffect,
  CombatParticipant,
  TurnResources,
} from "../../shared/api/combatRepo";

export type CombatLogEntry = {
  actorUserId?: string | null;
  id: string;
  message: string;
  source?: string | null;
};

export type CombatParticipantVitals = {
  currentHp: number | null;
  maxHp: number | null;
};

export type CombatParticipantView = CombatParticipant & {
  activeEffects: ActiveEffect[];
  currentHp: number | null;
  isCurrentTurn: boolean;
  isSelf: boolean;
  maxHp: number | null;
  turnResources: TurnResources | null;
};
