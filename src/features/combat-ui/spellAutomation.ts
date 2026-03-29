import type { CombatActionCost, CombatSpellMode, TurnResources } from "../../shared/api/combatRepo";

type CombatSpellAutomationConfig = {
  defaultMode: CombatSpellMode;
  requiresEffectInputs: boolean;
};

const SPELL_AUTOMATION_REGISTRY: Record<string, CombatSpellAutomationConfig> = {
  animal_friendship: {
    defaultMode: "saving_throw",
    requiresEffectInputs: false,
  },
  hunters_mark: {
    defaultMode: "utility",
    requiresEffectInputs: false,
  },
  goodberry: {
    defaultMode: "utility",
    requiresEffectInputs: false,
  },
  magic_missile: {
    defaultMode: "direct_damage",
    requiresEffectInputs: false,
  },
};

const normalizeSpellKey = (canonicalKey?: string | null) =>
  canonicalKey?.trim().toLowerCase().replace(/\s+/g, "_") ?? "";

export const resolveCombatSpellActionCost = (
  castingTimeType?: string | null,
): CombatActionCost | null => {
  const normalized = castingTimeType?.trim().toLowerCase() ?? "";
  if (normalized === "action" || normalized === "bonus_action" || normalized === "reaction") {
    return normalized;
  }
  if (!normalized) {
    return "action";
  }
  return null;
};

export const isCombatSpellActionCostAvailable = (
  actionCost: CombatActionCost | null | undefined,
  turnResources?: TurnResources | null,
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

export const getCombatSpellAutomation = (canonicalKey?: string | null) =>
  SPELL_AUTOMATION_REGISTRY[normalizeSpellKey(canonicalKey)] ?? null;

export const spellModeNeedsEffectInputs = (mode: CombatSpellMode) => mode !== "utility";

export const spellModeNeedsDamageType = (mode: CombatSpellMode) =>
  mode !== "heal" && mode !== "utility";

export const spellModeNeedsSaveAbility = (mode: CombatSpellMode) => mode === "saving_throw";
