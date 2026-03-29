import type { SpellUpcast } from "../../../entities/base-spell";
import type { CharacterSheet } from "../../../features/character-sheet/model/characterSheet.types";
import type { CombatActionCost, CombatSpellMode } from "../../../shared/api/combatRepo";
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
  sourceType?: "sheet" | "magic_item";
  sourceItemName?: string | null;
  inventoryItemId?: string | null;
  level: number;
  fixedCastLevel?: number | null;
  prepared: boolean;
  ignoreComponents?: boolean;
  noFreeHandRequired?: boolean;
  actionCost: CombatActionCost | null;
  suggestedMode: CombatSpellMode | null;
  damageType: string | null;
  savingThrow: string | null;
  saveSuccessOutcome?: "none" | "half_damage" | null;
  availableSlotLevels: number[];
  upcast?: SpellUpcast | null;
  chargesCurrent?: number | null;
  chargesMax?: number | null;
};
