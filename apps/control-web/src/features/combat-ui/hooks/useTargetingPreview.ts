import { useEffect, useState } from "react";
import {
  combatRepo,
  type CombatPreviewResponse,
  type TacticalDiagnosticsPayload,
} from "../../../shared/api/combatRepo";

export const METERS_PER_CELL = 1.5;
const DEBOUNCE_MS = 200;

export type RangeStatus = "normal" | "long" | "out" | "unknown";

export type TargetingPreviewState = {
  loading: boolean;
  error: string | null;
  diagnostics: TacticalDiagnosticsPayload | null;
  distanceMeters: number | null;
  normalRangeMeters: number | null;
  maxRangeMeters: number | null;
  effectiveReachMeters: number | null;
  rangeStatus: RangeStatus;
  hasDisadvantage: boolean;
  failureReasons: string[];
};

export type TargetingPreviewResult = TargetingPreviewState;

export type UseTargetingPreviewOptions = {
  sessionId: string;
  actorRefId: string | null | undefined;
  targetRefId: string | null | undefined;
  actionType: "attack" | "spell";
  normalRangeMeters?: number | null;
  longRangeMeters?: number | null;
  enabled?: boolean;
};

export function metersToCells(meters: number): number {
  return Math.max(1, Math.round(meters / METERS_PER_CELL));
}

export function classifyRange(
  distanceMeters: number | null,
  normalRangeMeters: number | null | undefined,
  longRangeMeters: number | null | undefined,
): { status: RangeStatus; hasDisadvantage: boolean } {
  if (distanceMeters == null) return { status: "unknown", hasDisadvantage: false };
  const normal = normalRangeMeters ?? null;
  const long = longRangeMeters ?? null;
  if (normal == null && long == null) return { status: "unknown", hasDisadvantage: false };
  if (normal != null && distanceMeters <= normal) return { status: "normal", hasDisadvantage: false };
  if (long != null && distanceMeters <= long) return { status: "long", hasDisadvantage: true };
  return { status: "out", hasDisadvantage: false };
}

const INITIAL: TargetingPreviewState = {
  loading: false,
  error: null,
  diagnostics: null,
  distanceMeters: null,
  normalRangeMeters: null,
  maxRangeMeters: null,
  effectiveReachMeters: null,
  rangeStatus: "unknown",
  hasDisadvantage: false,
  failureReasons: [],
};

export function useTargetingPreview(opts: UseTargetingPreviewOptions): TargetingPreviewState {
  const {
    sessionId,
    actorRefId,
    targetRefId,
    actionType,
    normalRangeMeters,
    longRangeMeters,
    enabled = true,
  } = opts;

  const [state, setState] = useState<TargetingPreviewState>(INITIAL);

  useEffect(() => {
    if (!enabled || !sessionId || !actorRefId || !targetRefId) {
      setState(INITIAL);
      return;
    }

    let cancelled = false;
    const reachMeters = longRangeMeters ?? normalRangeMeters ?? null;
    const reachCells = reachMeters != null ? metersToCells(reachMeters) : 1;

    const handle = window.setTimeout(() => {
      setState((s) => ({ ...s, loading: true, error: null }));
      combatRepo
        .previewAction(sessionId, {
          source_ref_id: actorRefId,
          target_ref_id: targetRefId,
          action_type: actionType,
          reach_cells: reachCells,
        })
        .then((res: CombatPreviewResponse) => {
          if (cancelled) return;
          const diag = res.diagnostics ?? null;
          const meta = diag?.metadata ?? {};
          const distanceMeters =
            typeof meta["distance_meters"] === "number"
              ? (meta["distance_meters"] as number)
              : typeof meta["distance_cells"] === "number"
                ? (meta["distance_cells"] as number) * METERS_PER_CELL
                : null;
          const resolvedNormalRangeMeters =
            typeof meta["normal_range_meters"] === "number"
              ? (meta["normal_range_meters"] as number)
              : typeof meta["normal_range_cells"] === "number"
                ? (meta["normal_range_cells"] as number) * METERS_PER_CELL
                : normalRangeMeters;
          const resolvedLongRangeMeters =
            typeof meta["long_range_meters"] === "number"
              ? (meta["long_range_meters"] as number)
              : typeof meta["long_range_cells"] === "number"
                ? (meta["long_range_cells"] as number) * METERS_PER_CELL
                : longRangeMeters;
          const resolvedMaxRangeMeters =
            typeof meta["max_range_meters"] === "number"
              ? (meta["max_range_meters"] as number)
              : resolvedLongRangeMeters ?? resolvedNormalRangeMeters ?? null;
          const effectiveReachMeters =
            typeof res.effectiveReachCells === "number"
              ? res.effectiveReachCells * METERS_PER_CELL
              : null;
          const { status, hasDisadvantage } = classifyRange(
            distanceMeters,
            resolvedNormalRangeMeters,
            resolvedLongRangeMeters,
          );
          const checks = diag?.checks ?? {};
          const inRange = checks["in_range"];
          const finalStatus = inRange === false ? "out" : status;
          setState({
            loading: false,
            error: null,
            diagnostics: diag,
            distanceMeters,
            normalRangeMeters: resolvedNormalRangeMeters ?? null,
            maxRangeMeters: resolvedMaxRangeMeters,
            effectiveReachMeters,
            rangeStatus: finalStatus,
            hasDisadvantage: finalStatus === "long" ? true : hasDisadvantage,
            failureReasons: diag?.failureReasons ?? [],
          });
        })
        .catch((err: any) => {
          if (cancelled) return;
          setState({
            ...INITIAL,
            error: err?.data?.detail || err?.message || "preview failed",
          });
        });
    }, DEBOUNCE_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [
    enabled,
    sessionId,
    actorRefId,
    targetRefId,
    actionType,
    normalRangeMeters,
    longRangeMeters,
  ]);

  return state;
}
