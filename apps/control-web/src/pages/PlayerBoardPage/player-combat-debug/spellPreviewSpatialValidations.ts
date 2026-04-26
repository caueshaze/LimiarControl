import { metersToCells, type RangeStatus, type TargetingPreviewResult } from "../../../features/combat-ui/hooks/useTargetingPreview";
import type {
  CombatPreviewResponse,
  TacticalDiagnosticsPayload,
} from "../../../shared/api/combatRepo";
import type {
  SpellInstanceSpatialValidation,
  SpellTargetSpatialValidation,
} from "./spellMapPreviewModel";

type PreviewFailureReason =
  | "no_line_of_sight"
  | "no_line_of_effect"
  | "full_cover"
  | "target_out_of_reach";

type PreviewRequestArgs = {
  actorRefId: string;
  rangeMeters: number | null;
  sessionId: string;
  targetRefId: string;
};

type PreviewAction = (
  sessionId: string,
  payload: {
    source_ref_id: string;
    target_ref_id: string;
    action_type: "spell";
    reach_cells: number;
  },
) => Promise<CombatPreviewResponse>;

type BuildValidationOptions = {
  diagnostics: TacticalDiagnosticsPayload | null;
  rangeStatus?: RangeStatus;
  targetRefId: string;
  unavailableReason?: "missing_position" | "missing_map_data" | null;
};

const FAILURE_REASON_PRIORITY: readonly PreviewFailureReason[] = Object.freeze([
  "target_out_of_reach",
  "no_line_of_sight",
  "no_line_of_effect",
  "full_cover",
]);

const hasFailureReason = (
  reasons: readonly string[],
  reason: PreviewFailureReason,
): boolean => reasons.includes(reason);

const resolvePrimaryFailureReason = (
  reasons: readonly string[],
): PreviewFailureReason | null => {
  for (const reason of FAILURE_REASON_PRIORITY) {
    if (hasFailureReason(reasons, reason)) {
      return reason;
    }
  }
  return null;
};

const deriveRangeCheck = (
  diagnostics: TacticalDiagnosticsPayload | null,
  rangeStatus?: RangeStatus,
): boolean | null => {
  const inRangeCheck = diagnostics?.checks?.["in_range"];
  if (typeof inRangeCheck === "boolean") {
    return inRangeCheck;
  }
  if (rangeStatus === "out") {
    return false;
  }
  if (rangeStatus === "normal" || rangeStatus === "long") {
    return true;
  }
  return null;
};

export const buildTargetSpatialValidationFromPreview = ({
  diagnostics,
  rangeStatus,
  targetRefId,
  unavailableReason = null,
}: BuildValidationOptions): SpellTargetSpatialValidation => {
  const failureReasons = diagnostics?.failureReasons ?? [];
  const primaryFailure = resolvePrimaryFailureReason(failureReasons);

  return {
    targetRefId,
    inRange: deriveRangeCheck(diagnostics, rangeStatus),
    hasLineOfSight:
      primaryFailure === "no_line_of_sight"
        ? false
        : primaryFailure === "no_line_of_effect" || primaryFailure === "full_cover"
          ? true
          : null,
    hasLineOfEffect:
      primaryFailure === "no_line_of_effect" || primaryFailure === "full_cover"
        ? false
        : null,
    unavailableReason,
  };
};

export const buildSingleTargetSpatialValidations = (
  targetPreview: TargetingPreviewResult,
  selectedTargetRefId?: string | null,
): SpellTargetSpatialValidation[] | undefined => {
  if (!selectedTargetRefId) {
    return undefined;
  }

  if (targetPreview.error) {
    return [
      buildTargetSpatialValidationFromPreview({
        diagnostics: null,
        rangeStatus: targetPreview.rangeStatus,
        targetRefId: selectedTargetRefId,
        unavailableReason: "missing_map_data",
      }),
    ];
  }

  return [
    buildTargetSpatialValidationFromPreview({
      diagnostics: targetPreview.diagnostics,
      rangeStatus: targetPreview.rangeStatus,
      targetRefId: selectedTargetRefId,
    }),
  ];
};

export const buildUniqueTargetRefIds = (
  targetRefIds: readonly (string | null | undefined)[],
): string[] => Array.from(new Set(targetRefIds.filter((targetRefId): targetRefId is string => Boolean(targetRefId))));

export const buildInstanceSpatialValidations = (
  effectInstanceTargets: readonly { instance_index: number; target_ref_id: string }[],
  validationsByTargetRefId: ReadonlyMap<string, SpellTargetSpatialValidation>,
): SpellInstanceSpatialValidation[] =>
  effectInstanceTargets.map((target) => {
    const validation = validationsByTargetRefId.get(target.target_ref_id);
    return {
      instanceIndex: target.instance_index,
      targetRefId: target.target_ref_id,
      inRange: validation?.inRange ?? null,
      hasLineOfSight: validation?.hasLineOfSight ?? null,
      hasLineOfEffect: validation?.hasLineOfEffect ?? null,
      unavailableReason: validation?.unavailableReason ?? null,
    };
  });

export const fetchPreviewValidationsByTargetRefId = async ({
  actorRefId,
  previewAction,
  rangeMeters,
  sessionId,
  targetRefIds,
}: {
  actorRefId: string;
  previewAction: PreviewAction;
  rangeMeters: number | null;
  sessionId: string;
  targetRefIds: readonly string[];
}): Promise<Map<string, SpellTargetSpatialValidation>> => {
  const reachCells = rangeMeters != null ? metersToCells(rangeMeters) : 1;
  const uniqueTargetRefIds = buildUniqueTargetRefIds(targetRefIds);
  const entries = await Promise.all(
    uniqueTargetRefIds.map(async (targetRefId) => {
      try {
        const response = await previewAction(sessionId, {
          source_ref_id: actorRefId,
          target_ref_id: targetRefId,
          action_type: "spell",
          reach_cells: reachCells,
        });
        return [
          targetRefId,
          buildTargetSpatialValidationFromPreview({
            diagnostics: response.diagnostics ?? null,
            targetRefId,
          }),
        ] as const;
      } catch {
        return [
          targetRefId,
          buildTargetSpatialValidationFromPreview({
            diagnostics: null,
            targetRefId,
            unavailableReason: "missing_map_data",
          }),
        ] as const;
      }
    }),
  );

  return new Map(entries);
};

export const createPreviewRequestGate = () => {
  let currentRequestId = 0;

  return {
    issue(): number {
      currentRequestId += 1;
      return currentRequestId;
    },
    isCurrent(requestId: number): boolean {
      return requestId === currentRequestId;
    },
  };
};
