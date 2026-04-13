/**
 * Phase U2 — Failure Explanation Layer
 *
 * Translates TargetingDiagnostics (machine-readable) into
 * FailureExplanation (human-readable, PT-BR).
 *
 * Core principle: diagnostics are for machines; this module is for humans.
 *
 * Rules:
 * - No game logic. Pure string/data mapping.
 * - Primary failure is chosen by a fixed priority order, not by the order
 *   reasons were added to the diagnostics list (backend ordering is an
 *   implementation detail, not a contract).
 * - Details are built from metadata fields — never recomputed here.
 * - Unknown failure codes degrade gracefully (fallback label, no crash).
 */

import type { TacticalDiagnostics } from "../battle-map/battle-map-store";
import { getFailureLabel, getFailureSeverity } from "./preview-labels";
import type { FailureSeverity } from "./preview-labels";

export type { FailureSeverity };

export interface FailureExplanation {
  /** Short bold label — shown prominently. ≤ 22 chars. */
  primary: string;
  /** 0–2 lines of context — shown in smaller text below primary. */
  details: string[];
  /** Raw values used to build details (for consumers that render their own UI). */
  context: Record<string, number | string | boolean>;
  /** Visual severity hint for styling (color, border). */
  severity: FailureSeverity;
}

// ─── Priority order ───────────────────────────────────────────────────────────
//
// Lower index = higher priority. When multiple reasons are present, the one
// with the lowest index wins the "primary" slot.
//
// Design rationale:
//   - Conditions block action entirely (most disruptive) → first
//   - Target not found / invalid → player needs to re-select
//   - Range → common, actionable ("move closer")
//   - LoS / LoE → environmental, less actionable
//   - Visibility → soft block
//   - Infrastructure / unknown → last

const FAILURE_PRIORITY: readonly string[] = Object.freeze([
  "blocked_by_condition",
  "target_not_found",
  "invalid_target_type",
  "target_out_of_reach",
  "no_line_of_sight",
  "no_line_of_effect",
  "not_visible",
  "self_target_not_allowed",
  "map_unreachable",
]);

// ─── Detail builders ──────────────────────────────────────────────────────────
//
// Each builder receives the full metadata dict and returns up to 2 strings.
// Builders must be pure — no side effects, no throws.

type DetailBuilder = (
  meta: Record<string, number | string | boolean>
) => { details: string[]; context: Record<string, number | string | boolean> };

const DETAIL_BUILDERS: Record<string, DetailBuilder> = {
  target_out_of_reach: (meta) => {
    const distance =
      typeof meta.distance_cells === "number" ? meta.distance_cells : null;
    const reach =
      typeof meta.reach_cells === "number" ? meta.reach_cells : null;
    const details: string[] = [];
    const context: Record<string, number | string | boolean> = {};
    if (distance !== null) {
      details.push(`Distância: ${distance} célula${distance === 1 ? "" : "s"}`);
      context.distance = distance;
    }
    if (reach !== null) {
      details.push(`Alcance: ${reach} célula${reach === 1 ? "" : "s"}`);
      context.range = reach;
    }
    return { details, context };
  },

  no_line_of_sight: () => ({
    details: ["Visão bloqueada por obstáculo"],
    context: {},
  }),

  no_line_of_effect: () => ({
    details: ["Efeito bloqueado por obstáculo"],
    context: {},
  }),

  not_visible: () => ({
    details: ["Alvo não pode ser visto"],
    context: {},
  }),

  blocked_by_condition: (meta) => {
    const condition =
      typeof meta.condition === "string" ? meta.condition : null;
    return {
      details: [condition ? `Condição: ${condition}` : "Você está incapacitado"],
      context: condition ? { condition } : {},
    };
  },

  map_unreachable: () => ({
    details: ["Reconecte ao mapa"],
    context: {},
  }),

  // Reasons with no useful extra detail — empty builders
  target_not_found: () => ({ details: [], context: {} }),
  invalid_target_type: () => ({ details: [], context: {} }),
  self_target_not_allowed: () => ({ details: [], context: {} }),
};

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Translates a TargetingDiagnostics object into a human-readable
 * FailureExplanation, or returns null when the targeting is valid.
 *
 * Primary failure is chosen by FAILURE_PRIORITY, not by the order reasons
 * appear in the list. This makes the UI resilient to backend ordering changes.
 */
export function buildFailureExplanation(
  diagnostics: TacticalDiagnostics
): FailureExplanation | null {
  if (diagnostics.isValid) return null;
  if (diagnostics.failureReasons.length === 0) return null;

  const primary = _pickPrimaryReason(diagnostics.failureReasons);
  const builder = DETAIL_BUILDERS[primary] ?? (() => ({ details: [], context: {} }));
  const { details, context } = builder(diagnostics.metadata);

  return {
    primary: getFailureLabel(primary),
    details,
    context,
    severity: getFailureSeverity(primary),
  };
}

/**
 * Pick the highest-priority reason from a list.
 * Falls back to the first item in the list if none match the known order.
 */
function _pickPrimaryReason(reasons: readonly string[]): string {
  for (const candidate of FAILURE_PRIORITY) {
    if (reasons.includes(candidate)) return candidate;
  }
  return reasons[0];
}
