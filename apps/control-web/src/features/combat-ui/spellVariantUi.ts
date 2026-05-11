import type { SpellDeclarativeEffect, SpellVariant, SpellVariantManualNote } from "../../entities/base-spell";
import type {
  ActiveEffect,
  AppliedDeclarativeEffectsByTargetEntry,
  CombatSpellContextOrigin,
} from "../../shared/api/combatRepo";

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

type DeclarativeEffectSummaryLike = {
  type?: unknown;
  params?: Record<string, unknown> | null;
  observability?: Record<string, unknown> | null;
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

const ABILITY_LABELS_PT: Record<string, string> = {
  strength: "Força",
  dexterity: "Destreza",
  constitution: "Constituição",
  intelligence: "Inteligência",
  wisdom: "Sabedoria",
  charisma: "Carisma",
};

const formatAbilityList = (abilities: unknown[]) =>
  abilities
    .filter((ability): ability is string => typeof ability === "string")
    .map((ability) => ABILITY_LABELS_PT[ability] ?? ability)
    .join(", ");

export const formatDeclarativeEffectSummaryLine = (
  declarative: DeclarativeEffectSummaryLike | null | undefined,
  metadata?: Record<string, unknown> | null,
) => {
  if (!declarative || typeof declarative !== "object") {
    return null;
  }
  const p = declarative.params ?? {};
  if (
    (declarative.type === "advantage_on_checks" || declarative.type === "disadvantage_on_checks")
    && typeof p.ability === "string"
  ) {
    return `${declarative.type === "advantage_on_checks" ? "Vantagem" : "Desvantagem"} em testes de ${ABILITY_LABELS_PT[p.ability] ?? p.ability}`;
  }
  if (declarative.type === "modify_stat" && typeof p.stat === "string") {
    return `Effect: ${p.stat}`;
  }
  if (declarative.type === "modify_weapon_damage" && typeof p.dice === "string") {
    const operation = p.operation === "subtract" ? "-" : "+";
    return `Dano de arma ${operation}${p.dice}`;
  }
  if (
    (declarative.type === "advantage_on_saves" || declarative.type === "disadvantage_on_saves")
    && Array.isArray(p.abilities)
  ) {
    return `${declarative.type === "advantage_on_saves" ? "Vantagem" : "Desvantagem"} em salvaguardas de ${formatAbilityList(p.abilities)}`;
  }
  if (declarative.type === "size_modifier" && typeof p.value === "number") {
    if (p.value > 0) {
      return "Tamanho aumentado";
    }
    if (p.value < 0) {
      return "Tamanho reduzido";
    }
    return "Tamanho inalterado";
  }
  if (declarative.type === "apply_condition" && typeof p.condition === "string") {
    return `Condition: ${p.condition}`;
  }
  if (declarative.type === "grant_temp_hp") {
    const observed = declarative.observability ?? metadata ?? null;
    const rolled = typeof observed?.rolled_temp_hp === "number" ? observed.rolled_temp_hp : null;
    const applied = observed?.applied_temp_hp === true;
    const previous = typeof observed?.previous_temp_hp === "number" ? observed.previous_temp_hp : null;
    const final = typeof observed?.final_temp_hp === "number" ? observed.final_temp_hp : null;
    const noExpire =
      metadata && observed?.does_not_expire_temp_hp === true
        ? " Não expiram com a concentração."
        : "";
    if (applied && rolled !== null && previous !== null && final !== null && final <= previous) {
      return `PV temporários: ${rolled} rolados, mantidos ${previous} existentes.${noExpire}`;
    }
    if (applied && rolled !== null && final !== null) {
      return `PV temporários: +${rolled} (final: ${final}).${noExpire}`;
    }
    if (rolled !== null) {
      return `PV temporários: ${rolled} (aguardando aplicação)`;
    }
    if (typeof p.dice === "string") {
      return `PV temporários: ${p.dice}`;
    }
    return null;
  }
  if (declarative.type === "passive_skill_bonus" && typeof p.skill === "string" && typeof p.bonus === "number") {
    return `Bônus passivo: +${p.bonus} em ${p.skill}`;
  }
  if (declarative.type === "carrying_capacity_multiplier" && typeof p.multiplier === "number") {
    return `Capacidade de carga: x${p.multiplier}`;
  }
  if (declarative.type === "fall_damage_immunity_threshold" && typeof p.max_distance_meters === "number") {
    return `Imunidade a queda: até ${p.max_distance_meters}m`;
  }
  return null;
};

export const formatSpellVariantSummaryLines = (
  variant: Pick<SpellVariant, "effects" | "manualNotes"> | null | undefined,
) => {
  const effectLines = (variant?.effects ?? [])
    .map((effect: SpellDeclarativeEffect) => formatDeclarativeEffectSummaryLine(effect))
    .filter((line): line is string => Boolean(line));
  const manualLines = (variant?.manualNotes ?? []).map((note) => `${note.label} - ${note.description}`);
  return [...effectLines, ...manualLines];
};

export const filterManualNotesByAppliedEffects = (
  notes: SpellVariantManualNote[] | null | undefined,
  effects: Array<DeclarativeEffectSummaryLike> | null | undefined,
) => {
  if (!notes?.length) {
    return [];
  }
  const appliedKeys = new Set(
    (effects ?? [])
      .map((effect) => (typeof effect.type === "string" ? effect.type : null))
      .filter((value): value is string => value !== null),
  );
  return notes.filter((note) => !appliedKeys.has(note.key));
};

export const formatAppliedDeclarativeEffectsByTarget = (
  entries: AppliedDeclarativeEffectsByTargetEntry[] | null | undefined,
  manualNotesByTarget: ManualNotesByTargetEntryLike[] | null | undefined,
) => {
  if (!entries?.length) {
    return [];
  }
  return entries
    .map((entry) => {
      const lines = entry.effects
        .map((effect) => formatDeclarativeEffectSummaryLine(effect))
        .filter((line): line is string => Boolean(line));
      if (!lines.length) {
        return null;
      }
      const manualNotesEntry = findManualNotesForTarget(manualNotesByTarget, {
        targetParticipantId: entry.target_participant_id,
        targetRefId: entry.target_ref_id,
      });
      return {
        targetDisplayName: entry.target_display_name,
        variantLabel:
          entry.variant_label
          ?? resolveTargetVariantLabel({
            manualNotesByTarget,
            targetParticipantId: entry.target_participant_id,
            targetRefId: entry.target_ref_id,
          }),
        effectLines: lines,
        manualNoteLines: filterManualNotesByAppliedEffects(
          manualNotesEntry?.manual_notes,
          entry.effects,
        ).map((note) => `${note.label} - ${note.description}`),
      };
    })
    .filter((entry) => entry !== null);
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
    const summaryLine = formatDeclarativeEffectSummaryLine(
      declarative as DeclarativeEffectSummaryLike,
      metadata,
    );
    if (summaryLine) {
      lines.push(summaryLine);
    }
  }
  return lines;
};
