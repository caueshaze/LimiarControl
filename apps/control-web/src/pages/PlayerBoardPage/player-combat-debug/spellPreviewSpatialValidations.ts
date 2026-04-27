import { metersToCells, type RangeStatus, type TargetingPreviewResult } from "../../../features/combat-ui/hooks/useTargetingPreview";
import type {
  CombatPreviewResponse,
  TacticalDiagnosticsPayload,
} from "../../../shared/api/combatRepo";
import type {
  SpellAreaSpatialValidation,
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

type PositionalPreviewAction = (
  sessionId: string,
  payload: {
    source_ref_id: string;
    target_position: { x: number; y: number };
    action_type: "spell";
    reach_cells: number;
  },
) => Promise<CombatPreviewResponse>;

export const buildAreaSpatialValidationFromPreview = ({
  diagnostics,
  rangeStatus,
  originCell,
  unavailableReason = null,
}: {
  diagnostics: TacticalDiagnosticsPayload | null;
  rangeStatus?: RangeStatus;
  originCell: { x: number; y: number };
  unavailableReason?: "missing_position" | "missing_map_data" | null;
}): SpellAreaSpatialValidation => {
  const failureReasons = diagnostics?.failureReasons ?? [];
  const primaryFailure = resolvePrimaryFailureReason(failureReasons);

  return {
    originCell,
    inRange: deriveRangeCheck(diagnostics, rangeStatus),
    hasLineOfSight:
      primaryFailure === "no_line_of_sight"
        ? false
        : primaryFailure === "no_line_of_effect" || primaryFailure === "full_cover"
          ? true
          : null,
    hasLineOfEffect:
      primaryFailure === "no_line_of_effect" || primaryFailure === "full_cover" ? false : null,
    unavailableReason,
  };
};

export const fetchAreaSpatialValidation = async ({
  actorRefId,
  anchorCell,
  previewAction,
  rangeMeters,
  sessionId,
}: {
  actorRefId: string;
  anchorCell: { x: number; y: number };
  previewAction: PositionalPreviewAction;
  rangeMeters: number | null;
  sessionId: string;
}): Promise<SpellAreaSpatialValidation> => {
  const reachCells = rangeMeters != null ? metersToCells(rangeMeters) : 1;
  try {
    const response = await previewAction(sessionId, {
      source_ref_id: actorRefId,
      target_position: anchorCell,
      action_type: "spell",
      reach_cells: reachCells,
    });
    return buildAreaSpatialValidationFromPreview({
      diagnostics: response.diagnostics ?? null,
      originCell: anchorCell,
    });
  } catch {
    return buildAreaSpatialValidationFromPreview({
      diagnostics: null,
      originCell: anchorCell,
      unavailableReason: "missing_map_data",
    });
  }
};

export type PreviewFanoutCacheEntry = {
  result: SpellTargetSpatialValidation;
};

export function buildSpellPreviewFanoutKey(input: {
  sessionId: string;
  actorRefId: string;
  spellId: string;
  slotLevel: number | null;
  targetRefId: string;
}): string {
  return [
    input.sessionId,
    input.actorRefId,
    input.spellId,
    input.slotLevel ?? "none",
    input.targetRefId,
  ].join("|");
}

export async function fetchPreviewValidationsWithCache({
  actorRefId,
  buildKey,
  cache,
  inFlight,
  previewAction,
  rangeMeters,
  sessionId,
  targetRefIds,
}: {
  actorRefId: string;
  buildKey: (targetRefId: string) => string;
  cache: Map<string, PreviewFanoutCacheEntry>;
  inFlight: Map<string, Promise<SpellTargetSpatialValidation>>;
  previewAction: PreviewAction;
  rangeMeters: number | null;
  sessionId: string;
  targetRefIds: readonly string[];
}): Promise<Map<string, SpellTargetSpatialValidation>> {
  const reachCells = rangeMeters != null ? metersToCells(rangeMeters) : 1;
  const uniqueTargetRefIds = buildUniqueTargetRefIds(targetRefIds);

  const entries = await Promise.all(
    uniqueTargetRefIds.map(async (targetRefId): Promise<readonly [string, SpellTargetSpatialValidation]> => {
      const key = buildKey(targetRefId);

      const cached = cache.get(key);
      if (cached) {
        return [targetRefId, cached.result] as const;
      }

      const existing = inFlight.get(key);
      if (existing) {
        return [targetRefId, await existing] as const;
      }

      const promise: Promise<SpellTargetSpatialValidation> = previewAction(sessionId, {
        source_ref_id: actorRefId,
        target_ref_id: targetRefId,
        action_type: "spell",
        reach_cells: reachCells,
      })
        .then((response) => {
          const result = buildTargetSpatialValidationFromPreview({
            diagnostics: response.diagnostics ?? null,
            targetRefId,
          });
          if (!result.unavailableReason) {
            cache.set(key, { result });
          }
          return result;
        })
        .catch(() =>
          buildTargetSpatialValidationFromPreview({
            diagnostics: null,
            targetRefId,
            unavailableReason: "missing_map_data",
          }),
        )
        .finally(() => {
          inFlight.delete(key);
        });

      inFlight.set(key, promise);
      return [targetRefId, await promise] as const;
    }),
  );

  return new Map(entries);
}

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
