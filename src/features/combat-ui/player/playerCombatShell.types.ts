import type {
  CombatActionCost,
  CombatAttackResult,
  CombatParticipant,
  CombatSpellResult,
  CombatStandardActionResult,
  CombatState,
} from "../../../shared/api/combatRepo";
import type { DragonbornBreathWeaponAction } from "./dragonbornBreathWeapon";

export type AttackResult = CombatAttackResult;
export type SpellResult = CombatSpellResult;
export type UseObjectResult = CombatStandardActionResult;
export type CombatMyParticipant = CombatParticipant;

export type CombatShellData = {
  state: CombatState | null;
  isMyTurn: boolean;
  loading?: boolean;
  error?: string | null;
  currentParticipant: CombatParticipant | null;
  livingParticipants: CombatParticipant[];
};

export type SpellOption = {
  id: string;
  name: string;
  range?: string | null;
  actionCost?: CombatActionCost | null;
  sourceType?: "sheet" | "magic_item";
  sourceItemName?: string | null;
  inventoryItemId?: string | null;
  chargesCurrent?: number | null;
  chargesMax?: number | null;
};
export type ConsumableOption = { id: string; label: string };
export type UseObjectTargetOption = { id: string; display_name: string };
export type DragonbornBreathWeaponOption = DragonbornBreathWeaponAction;
export type SelectedConsumable = {
  isHealingConsumable: boolean;
  manualRollCount: number;
  manualRollSides: number;
  healingLabel?: string | null;
};
