import type {
  CombatActionCost,
  CombatAttackResult,
  CombatParticipant,
  CombatSpellResult,
  CombatStandardActionResult,
  CombatState,
} from "../../../shared/api/combatRepo";
import type { SpellSelectionType } from "../../../entities/base-spell";
import type { DragonbornBreathWeaponAction } from "./dragonbornBreathWeapon";
import type { SpellSlotSummaryEntry } from "../../../shared/ui/SpellSlotSummary";
import type { SessionInventorySelectOption } from "../../inventory/components/sessionInventoryPanel.utils";

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
  level?: number;
  range?: string | null;
  rangeMeters?: number | null;
  actionCost?: CombatActionCost | null;
  targetType?: "self" | "touch" | "ranged" | "special" | null;
  selectionType?: SpellSelectionType | null;
  areaShape?: "sphere" | "cone" | "line" | "cube" | "cylinder" | null;
  sourceType?: "sheet" | "magic_item";
  sourceItemName?: string | null;
  inventoryItemId?: string | null;
  chargesCurrent?: number | null;
  chargesMax?: number | null;
  availableSlotLevels?: number[];
  slotSummary?: SpellSlotSummaryEntry[];
};
export type ConsumableOption = { id: string; label: string };
export type UseObjectTargetOption = { id: string; display_name: string };
export type DragonbornBreathWeaponOption = DragonbornBreathWeaponAction;
export type WeaponOption = SessionInventorySelectOption;
export type SelectedConsumable = {
  isHealingConsumable: boolean;
  manualRollCount: number;
  manualRollSides: number;
  healingLabel?: string | null;
};
