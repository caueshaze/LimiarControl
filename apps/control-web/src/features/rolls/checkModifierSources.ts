import type { AbilityName, SkillName } from "../../entities/roll/rollResolution.types";
import type { ActiveEffect } from "../../shared/api/combatRepo";
import { SKILL_ABILITY_MAP } from "../character-sheet/constants";

type RequestRollType = "ability" | "skill";

export type CheckModifierSourcePreview = {
  source_label: string;
  modifier_type: "advantage" | "disadvantage";
  roll_type: RequestRollType;
  ability?: string | null;
  skill?: string | null;
  against?: "any" | "effect_target" | "selected_target" | null;
  selected_target_participant_id?: string | null;
  selected_target_display_name?: string | null;
  applied: boolean;
  skip_reason?: "target_mismatch" | "ability_mismatch" | "skill_mismatch" | "missing_target" | null;
};

type RollPreviewRequest = {
  rollType: RequestRollType;
  ability?: AbilityName | null;
  skill?: SkillName | null;
  targetParticipantId?: string | null;
};

const CHECK_MODIFIER_TYPES = new Set(["advantage_on_checks", "disadvantage_on_checks"]);

const resolveRequestAbility = (request: RollPreviewRequest): AbilityName | null => {
  if (request.rollType === "skill") {
    return request.skill ? SKILL_ABILITY_MAP[request.skill] : null;
  }
  return request.ability ?? null;
};

const normalizeAgainst = (
  value: unknown,
): "any" | "effect_target" | "selected_target" => (
  value === "selected_target" || value === "effect_target" ? value : "any"
);

export const deriveCheckModifierPreviewSources = (
  activeEffects: ActiveEffect[] | null | undefined,
  request: RollPreviewRequest,
): CheckModifierSourcePreview[] => {
  const requestAbility = resolveRequestAbility(request);
  if (!requestAbility) {
    return [];
  }

  const previewSources: CheckModifierSourcePreview[] = [];
  for (const effect of activeEffects ?? []) {
    if (effect.kind !== "spell_effect" || !effect.metadata || typeof effect.metadata !== "object") {
      continue;
    }
    const declarative = (effect.metadata as Record<string, unknown>).declarative_effect;
    if (!declarative || typeof declarative !== "object") {
      continue;
    }
    const effectType = (declarative as Record<string, unknown>).type;
    if (!CHECK_MODIFIER_TYPES.has(String(effectType))) {
      continue;
    }
    const params = (declarative as Record<string, unknown>).params;
    if (!params || typeof params !== "object") {
      continue;
    }

    const effectAbility = typeof (params as Record<string, unknown>).ability === "string"
      ? ((params as Record<string, unknown>).ability as string)
      : null;
    const against = normalizeAgainst((params as Record<string, unknown>).against);
    const selectedTargetParticipantId =
      typeof (effect.metadata as Record<string, unknown>).selected_target_participant_id === "string"
        ? ((effect.metadata as Record<string, unknown>).selected_target_participant_id as string)
        : null;
    const selectedTargetDisplayName =
      typeof (effect.metadata as Record<string, unknown>).selected_target_display_name === "string"
        ? ((effect.metadata as Record<string, unknown>).selected_target_display_name as string)
        : null;

    const entry: CheckModifierSourcePreview = {
      source_label:
        (typeof (effect.metadata as Record<string, unknown>).source_spell_name === "string"
          ? ((effect.metadata as Record<string, unknown>).source_spell_name as string)
          : effect.display_label) || "efeito ativo",
      modifier_type: effectType === "disadvantage_on_checks" ? "disadvantage" : "advantage",
      roll_type: request.rollType,
      ability: effectAbility,
      skill: request.rollType === "skill" ? request.skill ?? null : null,
      against,
      selected_target_participant_id: selectedTargetParticipantId,
      selected_target_display_name: selectedTargetDisplayName,
      applied: false,
      skip_reason: null,
    };

    if (effectAbility !== requestAbility) {
      entry.skip_reason = request.rollType === "skill" ? "skill_mismatch" : "ability_mismatch";
      previewSources.push(entry);
      continue;
    }

    if (against === "selected_target") {
      if (!request.targetParticipantId) {
        entry.skip_reason = "missing_target";
        previewSources.push(entry);
        continue;
      }
      if (request.targetParticipantId !== selectedTargetParticipantId) {
        entry.skip_reason = "target_mismatch";
        previewSources.push(entry);
        continue;
      }
    }

    entry.applied = true;
    previewSources.push(entry);
  }

  return previewSources;
};
