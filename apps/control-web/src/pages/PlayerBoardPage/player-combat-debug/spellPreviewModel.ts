import type { CombatResolvedSpellContext, CombatSpellMode } from "../../../shared/api/combatRepo";
import type { CombatSpellOption } from "./types";
import { resolveEffectInstanceContext } from "./InstanceTargetSelector";

export type SpellPreviewModel = {
  resolutionType: CombatSpellMode | null;
  damagePreview: string | null;
  delayedDamagePreview: string | null;
  damageType: string | null;
  attackMissOutcome: "none" | "half_damage" | null;
  effectInstanceCount: number;
  effectInstanceDice: string | null;
  targetType: string | null;
  selectionType: string | null;
  areaShape: "sphere" | "cone" | "line" | "cube" | "cylinder" | null;
  areaSizeMeters: number | null;
  rangeMeters: number | null;
  requiresAttackRoll: boolean;
  requiresSavingThrow: boolean;
  saveAbility: string | null;
  coverAppliesToSave: boolean | null;
  source: "resolved" | "fallback";
};

type FallbackInputs = {
  spell: Pick<
    CombatSpellOption,
    | "areaShape"
    | "cantripScaling"
    | "characterLevel"
    | "damageType"
    | "level"
    | "rangeMeters"
    | "savingThrow"
    | "selectionType"
    | "targetType"
    | "upcast"
  >;
  selectedSlotLevel: number | null;
  spellMode: CombatSpellMode | null;
  spellEffectDice: string | null;
};

const normalizeNumber = (value: number | null | undefined): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

const normalizeString = (value: string | null | undefined): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
};

/**
 * Build a preview model that the tactical/spell preview UI consumes.
 *
 * resolvedContext is the source of truth: when present, every mechanical
 * field is taken from it. fallback only fills gaps (or the whole model
 * when the backend resolve-context call is unavailable). Fallback never
 * recalculates upcast/cantripScaling on top of resolvedContext — instance
 * count derivation is gated on resolvedContext being absent.
 */
export const buildSpellPreviewModel = (
  resolvedContext: CombatResolvedSpellContext | null,
  fallback: FallbackInputs,
): SpellPreviewModel => {
  if (resolvedContext) {
    return {
      resolutionType: resolvedContext.resolution_type ?? null,
      damagePreview: normalizeString(resolvedContext.damage_preview),
      delayedDamagePreview: normalizeString(resolvedContext.delayed_damage_preview),
      damageType: normalizeString(resolvedContext.damage_type),
      attackMissOutcome: resolvedContext.attack_miss_outcome ?? null,
      effectInstanceCount: Math.max(1, resolvedContext.effect_instance_count ?? 1),
      effectInstanceDice: normalizeString(resolvedContext.effect_instance_dice),
      targetType: normalizeString(resolvedContext.target_type),
      selectionType: normalizeString(resolvedContext.selection_type),
      areaShape: resolvedContext.area_shape ?? null,
      areaSizeMeters: normalizeNumber(resolvedContext.area_size_meters ?? null),
      rangeMeters: normalizeNumber(resolvedContext.range_meters ?? null),
      requiresAttackRoll: Boolean(resolvedContext.requires_attack_roll),
      requiresSavingThrow: Boolean(resolvedContext.requires_saving_throw),
      saveAbility: normalizeString(resolvedContext.save_ability),
      coverAppliesToSave: resolvedContext.cover_applies_to_save === "physical" ? true : resolvedContext.cover_applies_to_save === "none" ? false : null,
      source: "resolved",
    };
  }

  const fallbackInstance = resolveEffectInstanceContext(
    fallback.spell,
    fallback.selectedSlotLevel,
  );
  return {
    resolutionType: fallback.spellMode ?? null,
    damagePreview: normalizeString(fallback.spellEffectDice),
    delayedDamagePreview: null,
    damageType: normalizeString(fallback.spell.damageType ?? null),
    attackMissOutcome: null,
    effectInstanceCount: Math.max(1, fallbackInstance.instanceCount),
    effectInstanceDice: normalizeString(fallbackInstance.instanceDice),
    targetType: normalizeString(fallback.spell.targetType ?? null),
    selectionType: normalizeString(fallback.spell.selectionType ?? null),
    areaShape: fallback.spell.areaShape ?? null,
    areaSizeMeters: null,
    rangeMeters: normalizeNumber(fallback.spell.rangeMeters ?? null),
    requiresAttackRoll: fallback.spellMode === "spell_attack",
    requiresSavingThrow: fallback.spellMode === "saving_throw",
    saveAbility: normalizeString(fallback.spell.savingThrow ?? null),
    coverAppliesToSave: null,
    source: "fallback",
  };
};
