import type { CharacterSheet } from "../../../features/character-sheet/model/characterSheet.types";
import type { CombatSpellMode } from "../../../shared/api/combatRepo";
import type { PlayerBoardStatusSummary } from "../playerBoard.types";

export type DeathSaveFeedback = {
  death_saves?: {
    failures?: number;
    successes?: number;
  };
  message?: string;
  roll?: number;
  status?: string;
};

export type PlayerCombatDebugPanelProps = {
  campaignId?: string | null;
  playerSheet?: CharacterSheet | null;
  playerStatus?: PlayerBoardStatusSummary | null;
  sessionId: string;
  userId?: string;
};

export type CombatSpellOption = {
  id: string;
  name: string;
  canonicalKey: string | null;
  level: number;
  prepared: boolean;
  suggestedMode: CombatSpellMode | null;
  damageType: string | null;
  savingThrow: string | null;
};
