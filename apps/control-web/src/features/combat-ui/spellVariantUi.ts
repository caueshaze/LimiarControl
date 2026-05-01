import type { SpellVariantManualNote } from "../../entities/base-spell";
import type { ActiveEffect, CombatSpellContextOrigin } from "../../shared/api/combatRepo";

type TargetVariantAssignmentLike = {
  target_participant_id?: string | null;
  target_ref_id?: string | null;
  variant_key: string;
  variant_label?: string | null;
};

type ManualNotesByTargetEntryLike = {
  target_participant_id?: string | null;
  target_ref_id?: string | null;
  target_display_name: string;
  variant_key: string;
  variant_label?: string | null;
  manual_notes: SpellVariantManualNote[];
};

type TargetLookup = {
  targetParticipantId?: string | null;
  targetRefId?: string | null;
};

const humanizeVariantKey = (variantKey: string) =>
  variantKey
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");

const matchesTarget = (
  entry: { target_participant_id?: string | null; target_ref_id?: string | null },
  lookup: TargetLookup,
) => {
  if (lookup.targetParticipantId && entry.target_participant_id === lookup.targetParticipantId) {
    return true;
  }
  if (lookup.targetRefId && entry.target_ref_id === lookup.targetRefId) {
    return true;
  }
  return false;
};

export const findTargetVariantAssignment = (
  targetVariantAssignments: TargetVariantAssignmentLike[] | null | undefined,
  lookup: TargetLookup,
) => {
  if (!targetVariantAssignments?.length) {
    return null;
  }
  return targetVariantAssignments.find((entry) => matchesTarget(entry, lookup)) ?? null;
};

export const findManualNotesForTarget = (
  manualNotesByTarget: ManualNotesByTargetEntryLike[] | null | undefined,
  lookup: TargetLookup,
) => {
  if (!manualNotesByTarget?.length) {
    return null;
  }
  return manualNotesByTarget.find((entry) => matchesTarget(entry, lookup)) ?? null;
};

export const resolveTargetVariantLabel = ({
  targetVariantAssignments,
  manualNotesByTarget,
  selectedVariantKey,
  selectedVariantLabel,
  targetParticipantId,
  targetRefId,
}: {
  targetVariantAssignments?: TargetVariantAssignmentLike[] | null;
  manualNotesByTarget?: ManualNotesByTargetEntryLike[] | null;
  selectedVariantKey?: string | null;
  selectedVariantLabel?: string | null;
  targetParticipantId?: string | null;
  targetRefId?: string | null;
}) => {
  const assignment = findTargetVariantAssignment(targetVariantAssignments, {
    targetParticipantId,
    targetRefId,
  });
  if (assignment?.variant_label) {
    return assignment.variant_label;
  }
  if (assignment?.variant_key) {
    return humanizeVariantKey(assignment.variant_key);
  }

  const manualNotesEntry = findManualNotesForTarget(manualNotesByTarget, {
    targetParticipantId,
    targetRefId,
  });
  if (manualNotesEntry?.variant_label) {
    return manualNotesEntry.variant_label;
  }
  if (manualNotesEntry?.variant_key) {
    return humanizeVariantKey(manualNotesEntry.variant_key);
  }

  if (selectedVariantKey) {
    const assignmentByKey = targetVariantAssignments?.find(
      (entry) => entry.variant_key === selectedVariantKey,
    );
    if (assignmentByKey?.variant_label) {
      return assignmentByKey.variant_label;
    }
    const manualNotesByKey = manualNotesByTarget?.find(
      (entry) => entry.variant_key === selectedVariantKey,
    );
    if (manualNotesByKey?.variant_label) {
      return manualNotesByKey.variant_label;
    }
  }

  if (selectedVariantLabel) {
    return selectedVariantLabel;
  }
  return selectedVariantKey ? `Variante desconhecida (${humanizeVariantKey(selectedVariantKey)})` : null;
};

export const buildPendingSaveReason = ({
  spellName,
  saveAbility,
  variantLabel,
}: {
  spellName: string;
  saveAbility: string;
  variantLabel?: string | null;
}) =>
  variantLabel
    ? `${spellName} - save de ${saveAbility} - variante: ${variantLabel}`
    : `${spellName} - save de ${saveAbility}`;

export const formatVariantAssignmentDebug = (
  targetVariantAssignments: TargetVariantAssignmentLike[] | null | undefined,
  manualNotesByTarget: ManualNotesByTargetEntryLike[] | null | undefined,
) => {
  if (!targetVariantAssignments?.length) {
    return [];
  }
  return targetVariantAssignments.map((entry) => {
    const manualEntry = findManualNotesForTarget(manualNotesByTarget, {
      targetParticipantId: entry.target_participant_id,
      targetRefId: entry.target_ref_id,
    });
    const targetName =
      manualEntry?.target_display_name
      ?? entry.target_participant_id
      ?? entry.target_ref_id
      ?? "Target";
    const variantLabel = entry.variant_label ?? humanizeVariantKey(entry.variant_key);
    return `${targetName}: ${variantLabel}`;
  });
};

export const formatManualNotesByTarget = (
  manualNotesByTarget: ManualNotesByTargetEntryLike[] | null | undefined,
) => {
  if (!manualNotesByTarget?.length) {
    return [];
  }
  return manualNotesByTarget.flatMap((entry) =>
    entry.manual_notes.map((note) => `${entry.target_display_name}: ${note.label} - ${note.description}`),
  );
};

export const originLabel = (origin: CombatSpellContextOrigin | null | undefined) => {
  switch (origin) {
    case "initial_cast":
      return "initial cast";
    case "pending_save":
      return "pending save";
    case "pending_spell":
      return "pending spell";
    default:
      return null;
  }
};

const humanizeAgainst = (value: unknown) => {
  if (value === "selected_target") return "selected target";
  if (value === "effect_target") return "effect target";
  if (value === "any") return "any";
  return null;
};

export const formatEffectContextDebug = (
  effect: ActiveEffect,
  {
    targetDisplayName,
  }: {
    targetDisplayName?: string | null;
  } = {},
) => {
  const metadata = effect.metadata;
  if (!metadata || typeof metadata !== "object") {
    return [];
  }
  const lines: string[] = [];
  const sourceSpellName =
    typeof metadata.source_spell_name === "string" ? metadata.source_spell_name : null;
  if (sourceSpellName) {
    lines.push(`Source: ${sourceSpellName}`);
  }
  const variantLabel =
    typeof metadata.selected_variant_label === "string"
      ? metadata.selected_variant_label
      : typeof metadata.selected_variant_key === "string"
        ? humanizeVariantKey(metadata.selected_variant_key)
        : null;
  if (variantLabel) {
    lines.push(`Variant: ${variantLabel}`);
  }
  const recipient =
    typeof metadata.effect_target_display_name === "string"
      ? metadata.effect_target_display_name
      : targetDisplayName ?? null;
  if (recipient) {
    lines.push(`Recipient: ${recipient}`);
  }
  if (typeof metadata.selected_target_display_name === "string") {
    lines.push(`Selected target: ${metadata.selected_target_display_name}`);
  }
  const againstLabel = humanizeAgainst(metadata.against);
  if (againstLabel) {
    lines.push(`Against: ${againstLabel}`);
  }
  const origin = originLabel(
    typeof metadata.context_origin === "string"
      ? (metadata.context_origin as CombatSpellContextOrigin)
      : null,
  );
  if (origin) {
    lines.push(`Context: ${origin}`);
  }
  if (metadata.concentration === true) {
    lines.push(
      typeof metadata.concentration_group === "string"
        ? `Concentration: ${metadata.concentration_group}`
        : "Concentration: yes",
    );
  }
  const declarative = metadata.declarative_effect;
  if (declarative && typeof declarative === "object") {
    const entry = declarative as {
      type?: unknown;
      params?: { ability?: unknown; stat?: unknown; condition?: unknown } | null;
    };
    if (
      (entry.type === "advantage_on_checks" || entry.type === "disadvantage_on_checks")
      && entry.params
      && typeof entry.params.ability === "string"
    ) {
      lines.push(
        `${entry.type === "advantage_on_checks" ? "Advantage" : "Disadvantage"}: ${entry.params.ability} checks`,
      );
    } else if (entry.type === "modify_stat" && entry.params && typeof entry.params.stat === "string") {
      lines.push(`Effect: ${entry.params.stat}`);
    } else if (entry.type === "apply_condition" && entry.params && typeof entry.params.condition === "string") {
      lines.push(`Condition: ${entry.params.condition}`);
    }
  }
  return lines;
};
