import { METERS_PER_CELL } from "../../../features/combat-ui/hooks/useTargetingPreview";
import type { CombatAreaPreviewResponse } from "../../../shared/api/combatRepo";
import type { GridCell } from "./areaTargetingUi";
import type { EffectInstanceTargetInput } from "./InstanceTargetSelector";
import type { SpellPreviewModel } from "./spellPreviewModel";

export type SpellMapPreviewStatus = "valid" | "invalid" | "partial" | "unknown";

export type SpellInstanceMapStatus = {
  instanceIndex: number;
  targetRefId: string | null;
  status: SpellMapPreviewStatus;
  reason?: string | null;
};

export type SpellMapPreviewModel = {
  status: SpellMapPreviewStatus;
  reason?: string | null;
  affectedTargetCount?: number;
  affectedTargetNames?: string[];
  rangeMeters: number | null;
  areaShape: string | null;
  areaSizeMeters: number | null;
  effectInstanceCount: number;
  instanceStatuses?: SpellInstanceMapStatus[];
};

export type SpellMapTargetPosition = {
  refId: string;
  cell: GridCell;
};

export type BuildSpellMapPreviewModelParams = {
  spellPreviewModel: SpellPreviewModel;
  casterPosition?: GridCell | null;
  selectedTargetRefId?: string | null;
  effectInstanceTargets?: EffectInstanceTargetInput[];
  existingAreaPreviewResult?: CombatAreaPreviewResponse | null;
  targetPositions?: SpellMapTargetPosition[];
};

const euclideanMeters = (a: GridCell, b: GridCell): number =>
  Math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2) * METERS_PER_CELL;

const checkRange = (
  casterPosition: GridCell,
  targetCell: GridCell,
  rangeMeters: number,
): SpellMapPreviewStatus =>
  euclideanMeters(casterPosition, targetCell) <= rangeMeters ? "valid" : "invalid";

export const buildSpellMapPreviewModel = ({
  spellPreviewModel,
  casterPosition,
  selectedTargetRefId,
  effectInstanceTargets,
  existingAreaPreviewResult,
  targetPositions,
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
    if (existingAreaPreviewResult) {
      return {
        ...base,
        status: existingAreaPreviewResult.is_valid ? "valid" : "invalid",
        reason: existingAreaPreviewResult.reason ?? null,
        affectedTargetCount: existingAreaPreviewResult.affected_target_ref_ids.length,
      };
    }
    return { ...base, status: "unknown" };
  }

  // Multi-instance spells (Magic Missile, Eldritch Blast, etc.)
  if (effectInstanceCount > 1) {
    const targets = effectInstanceTargets ?? [];
    const positions = targetPositions ?? [];

    const instanceStatuses: SpellInstanceMapStatus[] = Array.from(
      { length: effectInstanceCount },
      (_, i) => {
        const instanceIndex = i + 1;
        const entry = targets.find((t) => t.instance_index === instanceIndex);
        const targetRefId = entry?.target_ref_id ?? null;

        if (!targetRefId || !casterPosition || rangeMeters == null) {
          return { instanceIndex, targetRefId, status: "unknown" as SpellMapPreviewStatus };
        }

        const targetCell = positions.find((p) => p.refId === targetRefId)?.cell;
        if (!targetCell) {
          return { instanceIndex, targetRefId, status: "unknown" as SpellMapPreviewStatus };
        }

        const status = checkRange(casterPosition, targetCell, rangeMeters);
        return {
          instanceIndex,
          targetRefId,
          status,
          reason: status === "invalid" ? "Alvo fora do alcance" : null,
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
  if (!selectedTargetRefId || !casterPosition || rangeMeters == null) {
    return { ...base, status: "unknown" };
  }

  const targetCell = targetPositions?.find((p) => p.refId === selectedTargetRefId)?.cell;
  if (!targetCell) {
    return { ...base, status: "unknown" };
  }

  const status = checkRange(casterPosition, targetCell, rangeMeters);
  return {
    ...base,
    status,
    reason: status === "invalid" ? "Alvo fora do alcance" : null,
  };
};
