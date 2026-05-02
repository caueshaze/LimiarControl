/**
 * D&D 5e spellcasting progression tables (PHB).
 *
 * Frontend single source of truth for spell slot counts, cantrip progression,
 * spells-known counts, and prepared-spell divisors across all spellcasting classes.
 *
 * Backend counterpart (authoritative for server-side level-up logic):
 *   apps/control-server/app/services/class_progression.py
 *   (_FULL_CASTER_SLOTS, _HALF_CASTER_SLOTS, _WARLOCK_SLOTS, _CLASS_SLOT_TABLES)
 *
 * IMPORTANT: If slot data changes here, apply the same change to the Python file
 * and vice versa to keep both ends in sync.
 */
import { resolveSpellSourceClassId } from "./spellCatalogApi";

// ── Private builder utilities ─────────────────────────────────────────────────

const buildLevelTable = (values: number[]) =>
  Object.fromEntries(values.map((value, index) => [index + 1, value])) as Record<
    number,
    number
  >;

const buildSlotTable = (rows: Array<Record<number, number>>) =>
  Object.fromEntries(rows.map((row, index) => [index + 1, row])) as Record<
    number,
    Record<number, number>
  >;

// ── Spell slot progression tables (PHB) ──────────────────────────────────────

export const FULL_CASTER_SLOTS = buildSlotTable([
  { 1: 2 },
  { 1: 3 },
  { 1: 4, 2: 2 },
  { 1: 4, 2: 3 },
  { 1: 4, 2: 3, 3: 2 },
  { 1: 4, 2: 3, 3: 3 },
  { 1: 4, 2: 3, 3: 3, 4: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 2 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 2 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 1, 7: 1, 8: 1, 9: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 1, 8: 1, 9: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1 },
]);

export const HALF_CASTER_SLOTS = buildSlotTable([
  {},
  { 1: 2 },
  { 1: 3 },
  { 1: 3 },
  { 1: 4, 2: 2 },
  { 1: 4, 2: 2 },
  { 1: 4, 2: 3 },
  { 1: 4, 2: 3 },
  { 1: 4, 2: 3, 3: 2 },
  { 1: 4, 2: 3, 3: 2 },
  { 1: 4, 2: 3, 3: 3 },
  { 1: 4, 2: 3, 3: 3 },
  { 1: 4, 2: 3, 3: 3, 4: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 2 },
  { 1: 4, 2: 3, 3: 3, 4: 2 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 1 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 2 },
  { 1: 4, 2: 3, 3: 3, 4: 3, 5: 2 },
]);

export const WARLOCK_SLOTS = buildSlotTable([
  { 1: 1 },
  { 1: 2 },
  { 2: 2 },
  { 2: 2 },
  { 3: 2 },
  { 3: 2 },
  { 4: 2 },
  { 4: 2 },
  { 5: 2 },
  { 5: 2 },
  { 5: 3 },
  { 5: 3 },
  { 5: 3 },
  { 5: 3 },
  { 5: 3 },
  { 5: 3 },
  { 5: 4 },
  { 5: 4 },
  { 5: 4 },
  { 5: 4 },
]);

export const SLOT_TABLES_BY_CLASS: Record<string, Record<number, Record<number, number>>> = {
  bard: FULL_CASTER_SLOTS,
  cleric: FULL_CASTER_SLOTS,
  druid: FULL_CASTER_SLOTS,
  guardian: HALF_CASTER_SLOTS,
  paladin: HALF_CASTER_SLOTS,
  ranger: HALF_CASTER_SLOTS,
  sorcerer: FULL_CASTER_SLOTS,
  warlock: WARLOCK_SLOTS,
  wizard: FULL_CASTER_SLOTS,
};

// ── Cantrip and spells-known tables (PHB) ─────────────────────────────────────

export const CANTRIPS_BY_CLASS = {
  bard: buildLevelTable([2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]),
  cleric: buildLevelTable([3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]),
  druid: buildLevelTable([2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]),
  sorcerer: buildLevelTable([4, 4, 4, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6]),
  warlock: buildLevelTable([2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]),
  wizard: buildLevelTable([3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]),
} as const;

export const LEVELED_SPELLS_KNOWN_BY_CLASS = {
  bard: buildLevelTable([4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 15, 16, 18, 19, 19, 20, 22, 22, 22]),
  ranger: buildLevelTable([0, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11]),
  sorcerer: buildLevelTable([2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 12, 13, 13, 14, 14, 15, 15, 15, 15]),
  warlock: buildLevelTable([2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15]),
} as const;

export const PREPARED_SPELL_LEVEL_DIVISOR_BY_CLASS: Record<string, number> = {
  cleric: 1,
  druid: 1,
  paladin: 2,
  wizard: 1,
};

export const SPELLCASTING_TYPE_BY_CLASS: Record<string, "known" | "prepared" | "spellbook"> = {
  bard:     "known",
  cleric:   "prepared",
  druid:    "prepared",
  guardian: "known",
  paladin:  "prepared",
  ranger:   "known",
  sorcerer: "known",
  warlock:  "known",
  wizard:   "spellbook",
};

// ── Private helpers ───────────────────────────────────────────────────────────

const clampCharacterLevel = (level: number) => Math.max(1, Math.min(20, level));

const normalizeSpellProgressionClassId = (className: string) =>
  resolveSpellSourceClassId(className.trim().toLowerCase());

// ── Public lookup API ─────────────────────────────────────────────────────────

export const getSlotProgressionForLevel = (
  className: string,
  level: number
): Record<number, number> => {
  const table = SLOT_TABLES_BY_CLASS[normalizeSpellProgressionClassId(className)];
  if (!table) return {};
  return table[clampCharacterLevel(level)] ?? {};
};

export const getMaxUnlockedSpellLevel = (
  className: string,
  level: number,
  fallbackLevelOneSlots = 0
): number => {
  const highestSlotLevel = Math.max(
    0,
    ...Object.entries(getSlotProgressionForLevel(className, level))
      .filter(([, count]) => count > 0)
      .map(([slotLevel]) => Number(slotLevel))
  );

  if (highestSlotLevel > 0) return highestSlotLevel;
  return fallbackLevelOneSlots > 0 ? 1 : 0;
};

export const getCantripCountForClassLevel = (
  className: string,
  level: number
): number | undefined =>
  CANTRIPS_BY_CLASS[
    normalizeSpellProgressionClassId(className) as keyof typeof CANTRIPS_BY_CLASS
  ]?.[clampCharacterLevel(level)];
