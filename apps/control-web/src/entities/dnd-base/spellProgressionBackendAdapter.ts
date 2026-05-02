import {
  getCantripCountForClassLevel,
  getMaxUnlockedSpellLevel,
  getSlotProgressionForLevel,
  LEVELED_SPELLS_KNOWN_BY_CLASS,
  SPELLCASTING_TYPE_BY_CLASS,
} from "./spellProgression";

/**
 * Pure class spell progression as returned by GET /api/rules/spell-progression.
 * Does NOT include preparedSpells — that depends on character ability scores
 * and is computed on the frontend via getLeveledSpellCountForClassLevel.
 */
export type ClassSpellProgression = {
  className: string;
  level: number;
  slots: Record<number, number>;
  maxSpellLevel: number;
  cantrips: number;
  leveledSpellsKnown: number | null;
  spellcastingType: "known" | "prepared" | "spellbook" | null;
};

const USE_BACKEND = import.meta.env.VITE_USE_BACKEND_PROGRESSION === "true";

/**
 * Fetch spell progression from the backend API.
 * Only called when VITE_USE_BACKEND_PROGRESSION=true.
 * Returns null on any error so callers can fall back to local tables.
 */
export async function fetchFromBackend(
  className: string,
  level: number
): Promise<ClassSpellProgression | null> {
  try {
    const params = new URLSearchParams({ class: className, level: String(level) });
    const response = await fetch(`/api/rules/spell-progression?${params}`);
    if (!response.ok) return null;
    const data = await response.json();
    // JSON serializes dict[int, int] with string keys ("1", "2").
    // Normalize to numeric keys so the shape matches getSlotProgressionForLevel.
    if (data?.slots && typeof data.slots === "object") {
      data.slots = Object.fromEntries(
        Object.entries(data.slots).map(([k, v]) => [Number(k), v])
      );
    }
    return data as ClassSpellProgression;
  } catch {
    return null;
  }
}

/**
 * Build progression from local spellProgression.ts tables.
 * Guaranteed synchronous and offline-safe.
 */
export function fromLocalTables(
  className: string,
  level: number
): ClassSpellProgression | null {
  const slots = getSlotProgressionForLevel(className, level);
  const maxSpellLevel = getMaxUnlockedSpellLevel(className, level);
  const isKnownCaster = Object.keys(LEVELED_SPELLS_KNOWN_BY_CLASS).includes(
    className.toLowerCase()
  );

  if (maxSpellLevel === 0 && Object.keys(slots).length === 0) {
    const table = getSlotProgressionForLevel(className, 20);
    if (Object.keys(table).length === 0) return null;
  }

  const cantrips = getCantripCountForClassLevel(className, level) ?? 0;
  const leveledSpellsKnown = isKnownCaster
    ? (LEVELED_SPELLS_KNOWN_BY_CLASS[
        className.toLowerCase() as keyof typeof LEVELED_SPELLS_KNOWN_BY_CLASS
      ]?.[Math.max(1, Math.min(20, level))] ?? null)
    : null;
  const spellcastingType =
    (SPELLCASTING_TYPE_BY_CLASS[className.toLowerCase()] as ClassSpellProgression["spellcastingType"]) ??
    null;

  return {
    className: className.toLowerCase(),
    level: Math.max(1, Math.min(20, level)),
    slots,
    maxSpellLevel,
    cantrips,
    leveledSpellsKnown,
    spellcastingType,
  };
}

/**
 * Fetch class spell progression data (optional async source).
 *
 * ## When to use this
 * Async contexts only: debug panels, admin UIs, optional validation, prefetch hooks.
 *
 * ## When NOT to use this
 * The synchronous creation flow. That flow uses spellProgression.ts directly:
 *   getSlotProgressionForLevel / getMaxUnlockedSpellLevel / getCantripCountForClassLevel
 * This adapter does NOT replace those calls and must not be inserted into that path.
 *
 * ## Behavior by flag
 * - VITE_USE_BACKEND_PROGRESSION=true  → fetch from /api/rules/spell-progression,
 *                                         fall back to local tables on any error
 * - flag off (default)                 → local tables only, no network request made
 */
export async function fetchClassSpellProgression(
  className: string,
  level: number
): Promise<ClassSpellProgression | null> {
  if (USE_BACKEND) {
    const result = await fetchFromBackend(className, level);
    if (result !== null) return result;
  }
  return fromLocalTables(className, level);
}
