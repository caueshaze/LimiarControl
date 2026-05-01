import type { SpellVariantManualNote } from "../../entities/base-spell";

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
