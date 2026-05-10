import type {
  CombatActionCost,
  CombatSpellMode,
  TurnResources
} from "../../shared/api/combatRepo";

/**
 * Presentation-only adapter for combat spell automation.
 *
 * Rule authority lives in the backend. The backend exposes:
 *   automationMode, defaultSpellMode, requiresEffectInputs, requiresMap, handlerKey
 * via the spell catalog API (BaseSpellRead / CampaignSpellRead).
 *
 * This module provides presentation helpers and retains a minimal
 * presentation-only adapter for the special-handler spells that
 * have UI-specific behavior not derivable from catalog metadata alone.
 * This is NOT a behavioral authority — it must not duplicate rule logic.
 */

export type SpellAutomationMetadata = {
  automationMode?: string | null;
  defaultSpellMode?: CombatSpellMode | null;
  requiresEffectInputs?: boolean | null;
  requiresMap?: boolean | null;
  handlerKey?: string | null;
};

const normalizeSpellKey = (canonicalKey?: string | null) =>
  canonicalKey?.trim().toLowerCase().replace(/\s+/g, "_") ?? "";

export const resolveCombatSpellActionCost = (
  castingTimeType?: string | null
): CombatActionCost | null => {
  const normalized = castingTimeType?.trim().toLowerCase() ?? "";
  if (
    normalized === "action" ||
    normalized === "bonus_action" ||
    normalized === "reaction"
  ) {
    return normalized;
  }
  if (!normalized) {
    return "action";
  }
  return null;
};

export const isCombatSpellActionCostAvailable = (
  actionCost: CombatActionCost | null | undefined,
  turnResources?: TurnResources | null
) => {
  if (!actionCost || actionCost === "free") {
    return true;
  }
  if (!turnResources) {
    return true;
  }
  switch (actionCost) {
    case "bonus_action":
      return !turnResources.bonus_action_used;
    case "reaction":
      return !turnResources.reaction_used;
    case "action":
    default:
      return !turnResources.action_used;
  }
};

export const getCombatSpellAutomation = (
  canonicalKey?: string | null
): SpellAutomationMetadata | null => {
  const key = normalizeSpellKey(canonicalKey);
  switch (key) {
    case "animal_friendship":
      return {
        automationMode: "special_handler",
        defaultSpellMode: "saving_throw",
        requiresEffectInputs: false,
        requiresMap: false,
        handlerKey: "_cast_animal_friendship_automation"
      };
    case "hunters_mark":
      return {
        automationMode: "special_handler",
        defaultSpellMode: "utility",
        requiresEffectInputs: false,
        requiresMap: false,
        handlerKey: "_cast_hunters_mark_automation"
      };
    case "goodberry":
      return {
        automationMode: "special_handler",
        defaultSpellMode: "utility",
        requiresEffectInputs: false,
        requiresMap: false,
        handlerKey: "_cast_goodberry_automation"
      };
    case "spiritual_weapon":
      return {
        automationMode: "special_handler",
        defaultSpellMode: "spell_attack",
        requiresEffectInputs: false,
        requiresMap: true,
        handlerKey: "_cast_spiritual_weapon_automation",
      };
    default:
      return null;
  }
};

export const resolveAutomationFromCatalog = (
  metadata: SpellAutomationMetadata
): SpellAutomationMetadata => {
  if (metadata.defaultSpellMode) {
    return metadata;
  }
  return { ...metadata, defaultSpellMode: null };
};

export const spellModeNeedsEffectInputs = (mode: CombatSpellMode) =>
  mode !== "utility";

export const spellModeNeedsDamageType = (mode: CombatSpellMode) =>
  mode !== "heal" && mode !== "utility";

export const spellModeNeedsSaveAbility = (mode: CombatSpellMode) =>
  mode === "saving_throw";
