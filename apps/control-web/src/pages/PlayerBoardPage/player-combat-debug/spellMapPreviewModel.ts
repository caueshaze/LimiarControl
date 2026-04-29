import { METERS_PER_CELL } from "../../../features/combat-ui/hooks/useTargetingPreview";
import type {
  CombatAreaGuardrailOutcome,
  AreaPreviewAffectedTargetSpatialMetadata,
  CombatAreaPreviewResponse,
} from "../../../shared/api/combatRepo";
import type { GridCell } from "./areaTargetingUi";
import type { EffectInstanceTargetInput } from "./InstanceTargetSelector";
import type { SpellPreviewModel } from "./spellPreviewModel";

export type SpellMapPreviewStatus = "valid" | "invalid" | "partial" | "unknown";

export type SpellCoverRank = "none" | "half" | "three_quarters" | "unknown";

export type SpellCoverPreview = {
  rank: SpellCoverRank;
  bonus: number | null;
};

export type SpellMapPreviewReason =
  | "out_of_range"
  | "blocked_line_of_sight"
  | "blocked_line_of_effect"
  | "missing_position"
  | "missing_map_data";

export type SpellInstanceMapStatus = {
  instanceIndex: number;
  targetRefId: string | null;
  status: SpellMapPreviewStatus;
  reason?: SpellMapPreviewReason | string | null;
  cover?: SpellCoverPreview | null;
};

export type AreaTargetSpatialMetadata = {
  targetRefId: string;
  targetDisplayName: string | null;
  cover: string | null;
  baseSaveDc: number | null;
  effectiveSaveDc: number | null;
  coverModifier: number;
};

export type SpellMapPreviewModel = {
  status: SpellMapPreviewStatus;
  reason?: SpellMapPreviewReason | string | null;
  affectedTargetCount?: number;
  affectedTargetNames?: string[];
  affectedTargetSpatialMetadata?: AreaTargetSpatialMetadata[];
  guardrailTargetOutcomes?: CombatAreaGuardrailOutcome[];
  rangeMeters: number | null;
  areaShape: string | null;
  areaSizeMeters: number | null;
  effectInstanceCount: number;
  instanceStatuses?: SpellInstanceMapStatus[];
  cover?: SpellCoverPreview | null;
};

export type SpellMapTargetPosition = {
  refId: string;
  cell: GridCell;
  displayName?: string | null;
};

type SpellSpatialUnavailableReason = Extract<
  SpellMapPreviewReason,
  "missing_position" | "missing_map_data"
>;

type SpellBaseSpatialValidation = {
  inRange?: boolean | null;
  hasLineOfSight?: boolean | null;
  hasLineOfEffect?: boolean | null;
  unavailableReason?: SpellSpatialUnavailableReason | null;
  cover?: SpellCoverPreview | null;
};

export type SpellTargetSpatialValidation = SpellBaseSpatialValidation & {
  targetRefId: string;
};

export type SpellInstanceSpatialValidation = SpellBaseSpatialValidation & {
  instanceIndex: number;
  targetRefId: string;
};

export type SpellAreaSpatialValidation = SpellBaseSpatialValidation & {
  originCell?: GridCell | null;
};

export type BuildSpellMapPreviewModelParams = {
  spellPreviewModel: SpellPreviewModel;
  casterPosition?: GridCell | null;
  selectedTargetRefId?: string | null;
  effectInstanceTargets?: EffectInstanceTargetInput[];
  existingAreaPreviewResult?: CombatAreaPreviewResponse | null;
  targetPositions?: SpellMapTargetPosition[];
  spatialValidations?: {
    targets?: SpellTargetSpatialValidation[];
    instances?: SpellInstanceSpatialValidation[];
    area?: SpellAreaSpatialValidation | null;
  };
};

// Chebyshev distance matches the tactical engine (reach.py / coordinates.py):
// max(|dx|, |dy|) — king-moves on the grid, same as D&D diagonal-equals-cardinal.
const chebyshevMeters = (a: GridCell, b: GridCell): number =>
  Math.max(Math.abs(b.x - a.x), Math.abs(b.y - a.y)) * METERS_PER_CELL;

const toAreaTargetSpatialMetadata = (
  raw?: AreaPreviewAffectedTargetSpatialMetadata[],
): AreaTargetSpatialMetadata[] | undefined => {
  if (!raw || raw.length === 0) return undefined;
  return raw.map((item) => ({
    targetRefId: item.target_ref_id,
    targetDisplayName: item.target_display_name ?? null,
    cover: item.cover ?? null,
    baseSaveDc: item.base_save_dc ?? null,
    effectiveSaveDc: item.effective_save_dc ?? null,
    coverModifier: item.cover_modifier ?? 0,
  }));
};

const toGuardrailTargetOutcomes = (
  raw?: CombatAreaGuardrailOutcome[],
): CombatAreaGuardrailOutcome[] | undefined => {
  if (!raw || raw.length === 0) return undefined;
  return raw.map((item) => ({
    target_ref_id: item.target_ref_id,
    target_display_name: item.target_display_name,
    target_kind: item.target_kind,
    excluded_by_guardrail: item.excluded_by_guardrail ?? true,
    guardrail_reason: item.guardrail_reason,
  }));
};

const checkRange = (
  casterPosition: GridCell,
  targetCell: GridCell,
  rangeMeters: number,
): SpellMapPreviewStatus =>
  chebyshevMeters(casterPosition, targetCell) <= rangeMeters ? "valid" : "invalid";

const toRangeValidation = (
  casterPosition: GridCell | null | undefined,
  targetCell: GridCell | null | undefined,
  rangeMeters: number | null,
): boolean | null => {
  if (!casterPosition || !targetCell || rangeMeters == null) {
    return null;
  }
  return checkRange(casterPosition, targetCell, rangeMeters) === "valid";
};

type SpatialOutcome = {
  status: SpellMapPreviewStatus;
  reason: SpellMapPreviewReason | null;
};

const resolveSpatialOutcome = ({
  inRange,
  hasLineOfSight,
  hasLineOfEffect,
  unavailableReason,
}: SpellBaseSpatialValidation): SpatialOutcome => {
  if (unavailableReason) {
    return { status: "unknown", reason: unavailableReason };
  }

  if (inRange == null) {
    return { status: "unknown", reason: "missing_position" };
  }

  if (!inRange) {
    return { status: "invalid", reason: "out_of_range" };
  }

  if (hasLineOfSight === false) {
    return { status: "invalid", reason: "blocked_line_of_sight" };
  }

  if (hasLineOfEffect === false) {
    return { status: "invalid", reason: "blocked_line_of_effect" };
  }

  return { status: "valid", reason: null };
};

export const buildSpellMapPreviewModel = ({
  spellPreviewModel,
  casterPosition,
  selectedTargetRefId,
  effectInstanceTargets,
  existingAreaPreviewResult,
  targetPositions,
  spatialValidations,
}: BuildSpellMapPreviewModelParams): SpellMapPreviewModel => {
  const { effectInstanceCount, rangeMeters, areaShape, areaSizeMeters } = spellPreviewModel;

  const base: Pick<SpellMapPreviewModel, "effectInstanceCount" | "rangeMeters" | "areaShape" | "areaSizeMeters"> = {
    effectInstanceCount,
    rangeMeters: rangeMeters ?? null,
    areaShape: areaShape ?? null,
    areaSizeMeters: areaSizeMeters ?? null,
  };

  // Area spells delegate to the backend area preview result
  if (areaShape) {
    if (spatialValidations?.area) {
      const outcome = resolveSpatialOutcome({
        inRange: spatialValidations.area.inRange ?? null,
        hasLineOfSight: spatialValidations.area.hasLineOfSight ?? null,
        hasLineOfEffect: spatialValidations.area.hasLineOfEffect ?? null,
        unavailableReason: spatialValidations.area.unavailableReason ?? null,
      });
      return {
        ...base,
        status: outcome.status,
        reason: outcome.reason,
        affectedTargetCount: existingAreaPreviewResult?.affected_target_ref_ids.length ?? 0,
        affectedTargetNames: existingAreaPreviewResult?.affected_target_ref_ids
          .map(
            (targetRefId) =>
              targetPositions?.find((position) => position.refId === targetRefId)?.displayName ?? null,
          )
          .filter((name): name is string => Boolean(name)),
        affectedTargetSpatialMetadata: toAreaTargetSpatialMetadata(
          existingAreaPreviewResult?.affected_target_spatial_metadata,
        ),
        guardrailTargetOutcomes: toGuardrailTargetOutcomes(
          existingAreaPreviewResult?.guardrail_target_outcomes,
        ),
      };
    }

    if (existingAreaPreviewResult) {
      return {
        ...base,
        status: existingAreaPreviewResult.is_valid ? "valid" : "invalid",
        reason: existingAreaPreviewResult.reason ?? null,
        affectedTargetCount: existingAreaPreviewResult.affected_target_ref_ids.length,
        affectedTargetNames: existingAreaPreviewResult.affected_target_ref_ids
          .map(
            (targetRefId) =>
              targetPositions?.find((position) => position.refId === targetRefId)?.displayName ?? null,
          )
          .filter((name): name is string => Boolean(name)),
        affectedTargetSpatialMetadata: toAreaTargetSpatialMetadata(
          existingAreaPreviewResult.affected_target_spatial_metadata,
        ),
        guardrailTargetOutcomes: toGuardrailTargetOutcomes(
          existingAreaPreviewResult.guardrail_target_outcomes,
        ),
      };
    }
    return { ...base, status: "unknown", reason: "missing_map_data" };
  }

  // Multi-instance spells (Magic Missile, Eldritch Blast, etc.)
  if (effectInstanceCount > 1) {
    const targets = effectInstanceTargets ?? [];
    const positions = targetPositions ?? [];
    const validations = spatialValidations?.instances ?? [];

    const instanceStatuses: SpellInstanceMapStatus[] = Array.from(
      { length: effectInstanceCount },
      (_, i) => {
        const instanceIndex = i + 1;
        const entry = targets.find((t) => t.instance_index === instanceIndex);
        const targetRefId = entry?.target_ref_id ?? null;
        const validation = validations.find(
          (candidate) =>
            candidate.instanceIndex === instanceIndex && candidate.targetRefId === targetRefId,
        );

        if (!targetRefId) {
          return {
            instanceIndex,
            targetRefId,
            status: "unknown" as SpellMapPreviewStatus,
            reason: "missing_position",
          };
        }

        const targetCell = positions.find((p) => p.refId === targetRefId)?.cell;
        const outcome = resolveSpatialOutcome({
          inRange: validation?.inRange ?? toRangeValidation(casterPosition, targetCell, rangeMeters),
          hasLineOfSight: validation?.hasLineOfSight ?? null,
          hasLineOfEffect: validation?.hasLineOfEffect ?? null,
          unavailableReason: validation?.unavailableReason ?? null,
        });
        return {
          instanceIndex,
          targetRefId,
          status: outcome.status,
          reason: outcome.reason,
          cover: validation?.cover ?? null,
        };
      },
    );

    const validCount = instanceStatuses.filter((s) => s.status === "valid").length;
    const invalidCount = instanceStatuses.filter((s) => s.status === "invalid").length;
    const totalKnown = validCount + invalidCount;

    let overallStatus: SpellMapPreviewStatus;
    if (totalKnown === 0) {
      overallStatus = "unknown";
    } else if (validCount === instanceStatuses.length) {
      overallStatus = "valid";
    } else if (invalidCount === instanceStatuses.length) {
      overallStatus = "invalid";
    } else {
      overallStatus = "partial";
    }

    return { ...base, status: overallStatus, instanceStatuses };
  }

  // Single-target
  if (!selectedTargetRefId) {
    return { ...base, status: "unknown", reason: "missing_position" };
  }

  const validation = spatialValidations?.targets?.find(
    (candidate) => candidate.targetRefId === selectedTargetRefId,
  );
  const targetCell = targetPositions?.find((p) => p.refId === selectedTargetRefId)?.cell;
  const outcome = resolveSpatialOutcome({
    inRange: validation?.inRange ?? toRangeValidation(casterPosition, targetCell, rangeMeters),
    hasLineOfSight: validation?.hasLineOfSight ?? null,
    hasLineOfEffect: validation?.hasLineOfEffect ?? null,
    unavailableReason: validation?.unavailableReason ?? null,
  });
  return {
    ...base,
    status: outcome.status,
    reason: outcome.reason,
    cover: validation?.cover ?? null,
  };
};
