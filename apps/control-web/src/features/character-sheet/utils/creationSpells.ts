import { nanoid } from "nanoid";
import {
  findBaseSpell,
  getBaseSpells,
  getBaseSpellsForClass,
  getSpellAvailabilityClassIds,
  isSameSpellAuthority,
  resolveSpellSourceClassId,
  resolveSpellByAuthority,
} from "../../../entities/dnd-base";
import { getModifier } from "./calculations";
import { getClassCreationConfig } from "../data/classCreation";
import type {
  CharacterSheet,
  Spell,
  SpellcastingData
} from "../model/characterSheet.types";

type StartingSpellOptionGroup = {
  level: number;
  spells: ReturnType<typeof getBaseSpellsForClass>;
};

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

const FULL_CASTER_SLOTS = buildSlotTable([
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

const HALF_CASTER_SLOTS = buildSlotTable([
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

const WARLOCK_SLOTS = buildSlotTable([
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

const SLOT_TABLES_BY_CLASS: Record<string, Record<number, Record<number, number>>> = {
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

const CANTRIPS_BY_CLASS = {
  bard: buildLevelTable([2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]),
  cleric: buildLevelTable([3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]),
  druid: buildLevelTable([2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]),
  sorcerer: buildLevelTable([4, 4, 4, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6]),
  warlock: buildLevelTable([2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]),
  wizard: buildLevelTable([3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]),
} as const;

const LEVELED_SPELLS_KNOWN_BY_CLASS = {
  bard: buildLevelTable([4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 15, 16, 18, 19, 19, 20, 22, 22, 22]),
  ranger: buildLevelTable([0, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11]),
  sorcerer: buildLevelTable([2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 12, 13, 13, 14, 14, 15, 15, 15, 15]),
  warlock: buildLevelTable([2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15]),
} as const;

const PREPARED_SPELL_LEVEL_DIVISOR_BY_CLASS: Record<string, number> = {
  cleric: 1,
  druid: 1,
  paladin: 2,
  wizard: 1,
};

const clampCharacterLevel = (level: number) => Math.max(1, Math.min(20, level));

const getNormalizedSpellProgressionClassId = (className: string) =>
  resolveSpellSourceClassId(className.trim().toLowerCase());

const getSlotProgressionForLevel = (
  className: string,
  level: number
): Record<number, number> => {
  const table = SLOT_TABLES_BY_CLASS[getNormalizedSpellProgressionClassId(className)];
  if (!table) return {};
  return table[clampCharacterLevel(level)] ?? {};
};

const getMaxUnlockedSpellLevel = (
  className: string,
  level: number,
  fallbackLevelOneSlots = 0
) => {
  const highestSlotLevel = Math.max(
    0,
    ...Object.entries(getSlotProgressionForLevel(className, level))
      .filter(([, count]) => count > 0)
      .map(([slotLevel]) => Number(slotLevel))
  );

  if (highestSlotLevel > 0) return highestSlotLevel;
  return fallbackLevelOneSlots > 0 ? 1 : 0;
};

const sortSpells = (spells: Spell[]) =>
  [...spells].sort(
    (left, right) =>
      left.level - right.level || left.name.localeCompare(right.name)
  );

const sortCatalogSpells = <T extends { level: number; name: string }>(
  spells: T[]
) =>
  [...spells].sort(
    (left, right) =>
      left.level - right.level || left.name.localeCompare(right.name)
  );

const uniqueSpellKeys = (keys: string[]) => [
  ...new Set(keys.map((key) => key.trim()).filter(Boolean))
];

const getFixedSpellKeys = (
  className: string,
  level: number,
  kind: "cantrip" | "leveled"
) => {
  const config = getClassCreationConfig(className)?.startingSpells;
  if (!config) return [];
  if (config.minimumLevel && level < config.minimumLevel) return [];

  const levelConfig = config.byLevel?.[level];
  return uniqueSpellKeys([
    ...(kind === "cantrip"
      ? (config.fixedCantripCanonicalKeys ?? [])
      : (config.fixedLeveledSpellCanonicalKeys ?? [])),
    ...(kind === "cantrip"
      ? (levelConfig?.fixedCantripCanonicalKeys ?? [])
      : (levelConfig?.fixedLeveledSpellCanonicalKeys ?? []))
  ]);
};

const toSheetSpell = (
  spellIdentifier: string,
  className: string,
  mode: SpellcastingData["mode"],
  campaignId?: string | null
): Spell | null => {
  const baseSpell = findBaseSpell(spellIdentifier, campaignId);
  const allowedClassIds = new Set(getSpellAvailabilityClassIds(className));
  if (
    !baseSpell ||
    !baseSpell.classes.some(
      (entry) => allowedClassIds.has(entry.toLowerCase())
    )
  ) {
    return null;
  }
  return {
    id: nanoid(),
    name: baseSpell.name,
    canonicalKey: baseSpell.canonicalKey,
    campaignSpellId: baseSpell.campaignSpellId,
    level: baseSpell.level,
    school: baseSpell.school || "Evocation",
    // Cantrips are always prepared. Leveled spells: known/prepared -> auto-prepared, spellbook -> not prepared until player chooses.
    prepared: baseSpell.level === 0 || mode !== "spellbook",
    notes: ""
  };
};

export const getCatalogSpellOptions = (
  className: string,
  campaignId?: string | null
) =>
  sortCatalogSpells(
    className
      ? getBaseSpellsForClass(className, 9, campaignId)
      : getBaseSpells(campaignId)
  );

export const selectCatalogSpellForSheet = (
  spellIdentifier: string,
  className: string,
  mode: SpellcastingData["mode"],
  campaignId?: string | null,
  existingSpell?: Spell | null
): Spell | null => {
  const nextSpell = toSheetSpell(spellIdentifier, className, mode, campaignId);
  if (!nextSpell) return null;

  return {
    ...nextSpell,
    id: existingSpell?.id ?? nextSpell.id,
    prepared:
      nextSpell.level === 0
        ? true
        : (existingSpell?.prepared ?? nextSpell.prepared),
    notes: existingSpell?.notes ?? ""
  };
};

export const hasUnresolvedCreationSpellSelections = (
  spellcasting: SpellcastingData | null,
  className: string,
  campaignId?: string | null
) => {
  if (!spellcasting) return false;
  const availableSpells = getCatalogSpellOptions(className, campaignId);
  return spellcasting.spells.some(
    (spell) => !resolveSpellByAuthority(availableSpells, spell)
  );
};

const ensureFixedStartingSpells = (
  spells: Spell[],
  className: string,
  level: number,
  mode: SpellcastingData["mode"],
  campaignId?: string | null
) => {
  const fixedSpells = [
    ...getFixedSpellKeys(className, level, "cantrip"),
    ...getFixedSpellKeys(className, level, "leveled")
  ]
    .map((spellKey) => toSheetSpell(spellKey, className, mode, campaignId))
    .filter((spell): spell is Spell => spell !== null);

  const merged = [...spells];
  for (const fixedSpell of fixedSpells) {
    const existingIndex = merged.findIndex((spell) =>
      isSameSpellAuthority(spell, fixedSpell)
    );
    if (existingIndex >= 0) {
      merged[existingIndex] = {
        ...fixedSpell,
        ...merged[existingIndex],
        canonicalKey: fixedSpell.canonicalKey,
        campaignSpellId:
          merged[existingIndex]?.campaignSpellId ??
          fixedSpell.campaignSpellId ??
          null,
        name: merged[existingIndex]?.name || fixedSpell.name,
        level: merged[existingIndex]?.level ?? fixedSpell.level,
        school: merged[existingIndex]?.school || fixedSpell.school,
        prepared:
          merged[existingIndex]?.level === 0
            ? true
            : (merged[existingIndex]?.prepared ?? fixedSpell.prepared),
        notes: merged[existingIndex]?.notes ?? ""
      };
      continue;
    }
    merged.push(fixedSpell);
  }
  return merged;
};

const prioritizeFixedSpells = (spells: Spell[], fixedSpellKeys: string[]) => {
  if (fixedSpellKeys.length === 0) return spells;
  const fixedLookup = new Set(fixedSpellKeys.map((key) => key.toLowerCase()));
  const fixed = spells.filter(
    (spell) =>
      spell.canonicalKey && fixedLookup.has(spell.canonicalKey.toLowerCase())
  );
  const rest = spells.filter(
    (spell) =>
      !spell.canonicalKey || !fixedLookup.has(spell.canonicalKey.toLowerCase())
  );
  return [...fixed, ...rest];
};

export const getFixedStartingSpellCanonicalKeys = (
  className: string,
  level: number
): string[] =>
  uniqueSpellKeys([
    ...getFixedSpellKeys(className, level, "cantrip"),
    ...getFixedSpellKeys(className, level, "leveled")
  ]);

export const getFixedStartingSpells = (
  className: string,
  level: number,
  campaignId?: string | null
) =>
  getFixedStartingSpellCanonicalKeys(className, level)
    .map((spellKey) => findBaseSpell(spellKey, campaignId))
    .filter(
      (spell): spell is NonNullable<ReturnType<typeof findBaseSpell>> =>
        spell !== undefined
    );

const getCantripCountForClassLevel = (className: string, level: number) =>
  CANTRIPS_BY_CLASS[
    getNormalizedSpellProgressionClassId(className) as keyof typeof CANTRIPS_BY_CLASS
  ]?.[clampCharacterLevel(level)];

const getLeveledSpellCountForClassLevel = (
  className: string,
  level: number,
  mode: SpellcastingData["mode"],
  preparationAbility: keyof CharacterSheet["abilities"] | undefined,
  abilities: CharacterSheet["abilities"]
) => {
  const normalizedClassName = getNormalizedSpellProgressionClassId(className);
  const clampedLevel = clampCharacterLevel(level);

  if (mode === "spellbook" && normalizedClassName === "wizard") {
    return 6 + Math.max(0, clampedLevel - 1) * 2;
  }

  if (mode === "prepared" && preparationAbility) {
    const levelDivisor =
      PREPARED_SPELL_LEVEL_DIVISOR_BY_CLASS[normalizedClassName] ?? 1;
    const effectiveCasterLevel = Math.max(
      1,
      Math.floor(clampedLevel / levelDivisor)
    );
    return Math.max(
      1,
      effectiveCasterLevel + getModifier(abilities[preparationAbility])
    );
  }

  return LEVELED_SPELLS_KNOWN_BY_CLASS[
    normalizedClassName as keyof typeof LEVELED_SPELLS_KNOWN_BY_CLASS
  ]?.[clampedLevel];
};

export const getStartingSpellLimits = (
  className: string,
  abilities: CharacterSheet["abilities"],
  level: number
) => {
  const config = getClassCreationConfig(className)?.startingSpells;
  if (!config) return null;
  if (config.minimumLevel && level < config.minimumLevel) return null;

  const clampedLevel = clampCharacterLevel(level);
  const levelConfig = config.byLevel?.[clampedLevel] ?? {};
  const cantrips =
    levelConfig.cantrips ??
    getCantripCountForClassLevel(className, clampedLevel) ??
    config.cantrips;
  const effectivePreparationAbility = config.preparationAbility;
  const leveledMode = config.leveledMode;
  const fixedCantripCount = getFixedSpellKeys(
    className,
    clampedLevel,
    "cantrip"
  ).length;
  const fixedLeveledCount = getFixedSpellKeys(
    className,
    clampedLevel,
    "leveled"
  ).length;

  const leveledSpells =
    levelConfig.leveledSpells ??
    getLeveledSpellCountForClassLevel(
      className,
      clampedLevel,
      leveledMode,
      effectivePreparationAbility,
      abilities
    ) ??
    config.leveledSpells ??
    0;

  const legacyLevelOneSlots = levelConfig.levelOneSlots ?? config.levelOneSlots ?? 0;
  const slots = getSlotProgressionForLevel(className, clampedLevel);
  const maxSpellLevel = getMaxUnlockedSpellLevel(
    className,
    clampedLevel,
    legacyLevelOneSlots
  );

  return {
    cantrips: Math.max(cantrips, fixedCantripCount),
    leveledSpells: Math.max(leveledSpells, fixedLeveledCount),
    leveledMode,
    levelOneSlots: legacyLevelOneSlots,
    maxSpellLevel,
    slots:
      Object.keys(slots).length > 0
        ? slots
        : legacyLevelOneSlots > 0
          ? { 1: legacyLevelOneSlots }
          : {}
  };
};

export const getAvailableStartingSpells = (
  className: string,
  level = 1,
  campaignId?: string | null
) => {
  const config = getClassCreationConfig(className)?.startingSpells;
  if (!config) {
    return {
      cantrips: [],
      leveled: [],
      leveledGroups: [] as StartingSpellOptionGroup[],
    };
  }
  if (config.minimumLevel && level < config.minimumLevel) {
    return {
      cantrips: [],
      leveled: [],
      leveledGroups: [] as StartingSpellOptionGroup[],
    };
  }

  const fallbackLevelOneSlots = config.byLevel?.[level]?.levelOneSlots ?? config.levelOneSlots ?? 0;
  const maxSpellLevel = getMaxUnlockedSpellLevel(
    className,
    level,
    fallbackLevelOneSlots
  );
  const spells = getBaseSpellsForClass(className, maxSpellLevel, campaignId);
  const leveled = spells.filter((spell) => spell.level > 0);
  const leveledGroups = Array.from(new Set(leveled.map((spell) => spell.level)))
    .sort((left, right) => left - right)
    .map((spellLevel) => ({
      level: spellLevel,
      spells: leveled.filter((spell) => spell.level === spellLevel),
    }));

  return {
    cantrips: spells.filter((spell) => spell.level === 0),
    leveled,
    leveledGroups,
  };
};

export const normalizeCreationSpellSelection = (
  spellcasting: SpellcastingData | null,
  className: string,
  abilities: CharacterSheet["abilities"],
  level: number,
  campaignId?: string | null
): SpellcastingData | null => {
  if (!spellcasting) return null;

  const config = getClassCreationConfig(className)?.startingSpells;
  if (!config) return spellcasting;
  const limits = getStartingSpellLimits(className, abilities, level);
  if (!limits) return null;

  const mode = spellcasting.mode;
  const allowedSpells = getBaseSpellsForClass(
    className,
    limits.maxSpellLevel,
    campaignId
  );
  const selected = ensureFixedStartingSpells(
    spellcasting.spells.filter((spell) =>
      Boolean(resolveSpellByAuthority(allowedSpells, spell))
    ),
    className,
    level,
    mode,
    campaignId
  );
  const cantrips = prioritizeFixedSpells(
    selected.filter((spell) => spell.level === 0),
    getFixedSpellKeys(className, level, "cantrip")
  ).slice(0, limits.cantrips);
  const leveled = prioritizeFixedSpells(
    selected.filter((spell) => spell.level > 0),
    getFixedSpellKeys(className, level, "leveled")
  ).slice(0, limits.leveledSpells);

  return {
    ...spellcasting,
    slots: Object.fromEntries(
      Array.from({ length: 9 }, (_, index) => index + 1).map((slotLevel) => {
        const slotLimit = limits.slots[slotLevel] ?? 0;
        const existingSlot = spellcasting.slots[slotLevel] ?? { max: 0, used: 0 };
        return [
          slotLevel,
          {
            max: slotLimit,
            used: Math.min(existingSlot.used, slotLimit),
          },
        ];
      })
    ),
    spells: sortSpells(
      [...cantrips, ...leveled].map((spell) => ({
        ...spell,
        // Cantrips always prepared. Leveled: known/prepared → auto-prepared, spellbook → not until chosen.
        prepared: spell.level === 0 ? true : mode !== "spellbook"
      }))
    )
  };
};

export const toggleStartingSpell = (
  spellcasting: SpellcastingData | null,
  className: string,
  abilities: CharacterSheet["abilities"],
  level: number,
  spellName: string,
  campaignId?: string | null
): SpellcastingData | null => {
  if (!spellcasting) return null;
  const limits = getStartingSpellLimits(className, abilities, level);
  const spell = findBaseSpell(spellName, campaignId);
  if (!limits || !spell || spell.level > limits.maxSpellLevel) return spellcasting;
  if (
    getFixedStartingSpellCanonicalKeys(className, level).includes(
      spell.canonicalKey
    )
  ) {
    return spellcasting;
  }

  const existing = spellcasting.spells.find((entry) =>
    isSameSpellAuthority(entry, spell)
  );
  if (existing) {
    return normalizeCreationSpellSelection(
      {
        ...spellcasting,
        spells: spellcasting.spells.filter((entry) => entry.id !== existing.id)
      },
      className,
      abilities,
      level,
      campaignId
    );
  }

  const selectedLeveledCount = spellcasting.spells.filter(
    (entry) => entry.level > 0
  ).length;
  const limit = spell.level === 0 ? limits.cantrips : limits.leveledSpells;
  if (
    (spell.level === 0
      ? spellcasting.spells.filter((entry) => entry.level === 0).length
      : selectedLeveledCount) >= limit
  ) {
    return spellcasting;
  }

  const nextSpell = toSheetSpell(
    spellName,
    className,
    spellcasting.mode,
    campaignId
  );
  if (!nextSpell) return spellcasting;

  return normalizeCreationSpellSelection(
    { ...spellcasting, spells: [...spellcasting.spells, nextSpell] },
    className,
    abilities,
    level,
    campaignId
  );
};
