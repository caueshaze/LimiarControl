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
async function fetchFromBackend(
  className: string,
  level: number
): Promise<ClassSpellProgression | null> {
  try {
    const params = new URLSearchParams({ class: className, level: String(level) });
    const response = await fetch(`/api/rules/spell-progression?${params}`);
    if (!response.ok) return null;
    const data = await response.json();
    return data as ClassSpellProgression;
  } catch {
    return null;
  }
}

/**
 * Build progression from local spellProgression.ts tables.
 * Guaranteed synchronous and offline-safe.
 */
function fromLocalTables(
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
 * Fetch class spell progression data.
 *
 * When VITE_USE_BACKEND_PROGRESSION=true: queries the backend API with
 * fallback to local tables on failure.
 * Otherwise: returns local tables directly (synchronous path wrapped in Promise).
 *
 * Does NOT replace the synchronous creation flow — use getSlotProgressionForLevel
 * and related functions from spellProgression.ts for that.
 * This adapter is for components or hooks that can tolerate async loading.
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
