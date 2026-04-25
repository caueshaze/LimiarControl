/**
 * Maps canonical targeting failure reason codes (from the backend) to
 * short, player-facing PT-BR labels and severity hints.
 *
 * Rules:
 * - Labels must be ≤ 22 chars so they fit in the floating hint badge.
 * - No game logic here — pure string lookup.
 * - Unknown codes fall back to the raw code string (safe for future additions).
 *
 * Severity categories (used by Phase U2 for colour-coding):
 *   orange — range/reach failures (actionable: "move closer")
 *   red    — LoS / LoE failures (environmental block)
 *   purple — condition blocks (character-state block)
 *   gray   — all other / informational
 */

/** Visual severity hint used for colour-coding failure badges. */
export type FailureSeverity = "orange" | "red" | "purple" | "gray";

const FAILURE_LABELS: Record<string, string> = {
  target_not_found: "Alvo não encontrado",
  invalid_target_type: "Tipo de alvo inválido",
  area_targeting_unavailable: "Área indisponível",
  target_out_of_reach: "Fora do alcance",
  no_line_of_sight: "Sem linha de visão",
  no_line_of_effect: "Bloqueado",
  origin_heavily_obscured: "Você está na neblina",
  target_heavily_obscured: "Alvo na neblina",
  point_heavily_obscured: "Ponto na neblina",
  line_of_sight_obscured: "Visão bloqueada por neblina",
  not_visible: "Não visível",
  blocked_by_condition: "Condição bloqueante",
  self_target_not_allowed: "Não pode alvejar a si",
  map_unreachable: "Mapa indisponível"
};

const FAILURE_SEVERITIES: Record<string, FailureSeverity> = {
  target_out_of_reach: "orange",
  no_line_of_sight: "red",
  no_line_of_effect: "red",
  origin_heavily_obscured: "red",
  target_heavily_obscured: "red",
  point_heavily_obscured: "red",
  line_of_sight_obscured: "red",
  blocked_by_condition: "purple",
  not_visible: "gray",
  target_not_found: "gray",
  invalid_target_type: "gray",
  area_targeting_unavailable: "gray",
  self_target_not_allowed: "gray",
  map_unreachable: "gray"
};

/** Returns the PT-BR label for a single failure reason code. */
export function getFailureLabel(reason: string): string {
  return FAILURE_LABELS[reason] ?? reason;
}

/** Returns the severity hint for a single failure reason code. */
export function getFailureSeverity(reason: string): FailureSeverity {
  return FAILURE_SEVERITIES[reason] ?? "gray";
}

/**
 * Returns the label for the first (primary) failure reason, or null when
 * the list is empty (i.e. valid target).
 *
 * Note: U2 code should prefer buildFailureExplanation() which applies the
 * canonical priority order instead of relying on list position.
 */
export function getPrimaryFailureLabel(
  failureReasons: string[]
): string | null {
  if (failureReasons.length === 0) return null;
  return getFailureLabel(failureReasons[0]);
}

/** All known canonical failure reason codes (mirrors Python constants). */
export const CANONICAL_FAILURE_REASONS = Object.freeze(
  Object.keys(FAILURE_LABELS)
);
