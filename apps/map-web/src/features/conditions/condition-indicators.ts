/**
 * condition-indicators.ts — Single source of truth for condition presentation.
 *
 * Maps canonical D&D 5e condition codes (as sent by LimiarControl via syncTokens)
 * to display metadata used across:
 *   - Board token chips  (canvas-renderers.ts → drawTokenLayer)
 *   - Selected-token HUD panel (battle-map-canvas.tsx)
 *   - Future: tooltip descriptions, initiative list badges, etc.
 *
 * Priority: lower number = rendered/listed first (most impactful).
 * colorToken: CSS hex string, used both in PixiJS canvas and React JSX panels.
 */

export interface ConditionIndicator {
  /** Canonical code from LimiarControl (e.g. "incapacitated"). */
  conditionType: string;
  /** ≤ 2 uppercase chars — fits inside a small canvas chip dot title. */
  shortLabel: string;
  /** Full PT-BR name displayed in the selected-token panel. */
  label: string;
  /** Sort key: lower = higher severity, shown first. */
  priority: number;
  /** CSS hex color string (e.g. "#ef4444"). */
  colorToken: string;
  /** false only for conditions that are not inherently harmful (e.g. invisible can be beneficial). */
  isNegative: boolean;
}

const CONDITION_INDICATORS: Record<string, ConditionIndicator> = {
  incapacitated: {
    conditionType: "incapacitated",
    shortLabel: "IC",
    label: "Incapacitado",
    priority: 1,
    colorToken: "#ef4444",
    isNegative: true
  },
  paralyzed: {
    conditionType: "paralyzed",
    shortLabel: "PL",
    label: "Paralisado",
    priority: 2,
    colorToken: "#dc2626",
    isNegative: true
  },
  stunned: {
    conditionType: "stunned",
    shortLabel: "AT",
    label: "Atordoado",
    priority: 3,
    colorToken: "#e11d48",
    isNegative: true
  },
  petrified: {
    conditionType: "petrified",
    shortLabel: "PT",
    label: "Petrificado",
    priority: 4,
    colorToken: "#b45309",
    isNegative: true
  },
  blinded: {
    conditionType: "blinded",
    shortLabel: "CG",
    label: "Cego",
    priority: 5,
    colorToken: "#f97316",
    isNegative: true
  },
  exhausted: {
    conditionType: "exhausted",
    shortLabel: "EX",
    label: "Exausto",
    priority: 6,
    colorToken: "#d97706",
    isNegative: true
  },
  frightened: {
    conditionType: "frightened",
    shortLabel: "AP",
    label: "Apavorado",
    priority: 7,
    colorToken: "#f59e0b",
    isNegative: true
  },
  restrained: {
    conditionType: "restrained",
    shortLabel: "IM",
    label: "Imobilizado",
    priority: 8,
    colorToken: "#ca8a04",
    isNegative: true
  },
  invisible: {
    conditionType: "invisible",
    shortLabel: "IV",
    label: "Invisível",
    priority: 9,
    colorToken: "#a78bfa",
    isNegative: false
  },
  charmed: {
    conditionType: "charmed",
    shortLabel: "EC",
    label: "Encantado",
    priority: 10,
    colorToken: "#ec4899",
    isNegative: true
  },
  poisoned: {
    conditionType: "poisoned",
    shortLabel: "EN",
    label: "Envenenado",
    priority: 11,
    colorToken: "#22c55e",
    isNegative: true
  },
  grappled: {
    conditionType: "grappled",
    shortLabel: "AG",
    label: "Agarrado",
    priority: 12,
    colorToken: "#64748b",
    isNegative: true
  },
  deafened: {
    conditionType: "deafened",
    shortLabel: "SD",
    label: "Ensurdecido",
    priority: 13,
    colorToken: "#94a3b8",
    isNegative: true
  },
  prone: {
    conditionType: "prone",
    shortLabel: "CD",
    label: "Caído",
    priority: 14,
    colorToken: "#78716c",
    isNegative: true
  }
};

/**
 * Build a fallback ConditionIndicator for unrecognised condition codes.
 * Uses the first two uppercase characters of the code as the short label.
 * Priority is set high (999) so unknowns sort after all known conditions.
 */
function buildUnknownIndicator(conditionType: string): ConditionIndicator {
  return {
    conditionType,
    shortLabel: conditionType.slice(0, 2).toUpperCase(),
    label: conditionType,
    priority: 999,
    colorToken: "#475569",
    isNegative: true
  };
}

/**
 * Returns ConditionIndicator objects for each code in `conditions`,
 * sorted by ascending priority (most impactful first).
 * Unknown codes degrade gracefully — they always appear last.
 *
 * @param conditions - Array of condition code strings (may be empty).
 */
export function getConditionIndicators(conditions: string[]): ConditionIndicator[] {
  return conditions
    .map((code) => CONDITION_INDICATORS[code] ?? buildUnknownIndicator(code))
    .sort((a, b) => a.priority - b.priority);
}
