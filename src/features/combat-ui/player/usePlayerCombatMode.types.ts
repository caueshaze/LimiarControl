import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import type { SpellUpcast } from "../../../entities/base-spell";
import type { CharacterSheet } from "../../../features/character-sheet/model/characterSheet.types";
import type { CombatActionCost, CombatSpellMode } from "../../../shared/api/combatRepo";
import type { Locale } from "../../../shared/i18n";
import type { PlayerBoardStatusSummary } from "../../../pages/PlayerBoardPage/playerBoard.types";
import type { DragonbornBreathWeaponAction } from "./dragonbornBreathWeapon";

export type CombatSpellOption = {
  actionCost: CombatActionCost | null;
  canonicalKey: string | null;
  damageType: string | null;
  id: string;
  inventoryItemId?: string | null;
  sourceItemName?: string | null;
  sourceType?: "sheet" | "magic_item";
  level: number;
  name: string;
  fixedCastLevel?: number | null;
  ignoreComponents?: boolean;
  noFreeHandRequired?: boolean;
  prepared: boolean;
  range: string;
  chargesCurrent?: number | null;
  chargesMax?: number | null;
  saveSuccessOutcome?: "none" | "half_damage" | null;
  savingThrow: string | null;
  suggestedMode: CombatSpellMode | null;
  availableSlotLevels: number[];
  upcast?: SpellUpcast | null;
};

export type CombatConsumableOption = {
  healingLabel: string | null;
  id: string;
  isHealingConsumable: boolean;
  item: Item | null;
  label: string;
  manualRollCount: number;
  manualRollSides: number;
};

export type CombatDragonbornBreathWeaponAction = DragonbornBreathWeaponAction;

export type DeathSaveFeedback = {
  death_saves?: {
    failures?: number;
    successes?: number;
  };
  message?: string;
  roll?: number;
  status?: string;
};

export type UsePlayerCombatModeProps = {
  campaignId?: string | null;
  inventory: InventoryItem[] | null;
  itemsById: Record<string, Item>;
  locale: Locale;
  playerSheet?: CharacterSheet | null;
  playerStatus?: PlayerBoardStatusSummary | null;
  sessionId: string;
  userId?: string | null;
};
