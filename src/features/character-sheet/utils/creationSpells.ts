import { nanoid } from "nanoid";
import {
  findBaseSpell,
  getBaseSpells,
  getBaseSpellsForClass,
} from "../../../entities/dnd-base";
import { getModifier } from "./calculations";
import { getClassCreationConfig } from "../data/classCreation";
import { resolveClassMechanicsFamily } from "../data/classFeatures";
import type { CharacterSheet, Spell, SpellcastingData } from "../model/characterSheet.types";

const sortSpells = (spells: Spell[]) =>
  [...spells].sort((left, right) => left.level - right.level || left.name.localeCompare(right.name));

const sortCatalogSpells = <T extends { level: number; name: string }>(spells: T[]) =>
  [...spells].sort((left, right) => left.level - right.level || left.name.localeCompare(right.name));

const uniqueSpellKeys = (keys: string[]) => [...new Set(keys.map((key) => key.trim()).filter(Boolean))];

const getFixedSpellKeys = (
  className: string,
  level: number,
  kind: "cantrip" | "leveled",
) => {
  const config = getClassCreationConfig(className)?.startingSpells;
  if (!config) return [];
  if (config.minimumLevel && level < config.minimumLevel) return [];

  const levelConfig = config.byLevel?.[level];
  return uniqueSpellKeys([
    ...(kind === "cantrip"
      ? config.fixedCantripCanonicalKeys ?? []
      : config.fixedLeveledSpellCanonicalKeys ?? []),
    ...(kind === "cantrip"
      ? levelConfig?.fixedCantripCanonicalKeys ?? []
      : levelConfig?.fixedLeveledSpellCanonicalKeys ?? []),
  ]);
};

const spellMatchesBaseSpell = (spell: Spell, baseSpellName: string, baseSpellKey: string) =>
  spell.canonicalKey?.toLowerCase() === baseSpellKey.toLowerCase() ||
  spell.name.toLowerCase() === baseSpellName.toLowerCase();

const toSheetSpell = (
  spellIdentifier: string,
  className: string,
  mode: SpellcastingData["mode"],
  campaignId?: string | null,
): Spell | null => {
  const baseSpell = findBaseSpell(spellIdentifier, campaignId);
  const spellClassId = resolveClassMechanicsFamily(className);
  if (!baseSpell || !baseSpell.classes.some((entry) => entry.toLowerCase() === spellClassId.toLowerCase())) {
    return null;
  }
  return {
    id: nanoid(),
    name: baseSpell.name,
    canonicalKey: baseSpell.canonicalKey,
    level: baseSpell.level,
    school: baseSpell.school || "Evocation",
    // Cantrips are always prepared. Leveled spells: known/prepared -> auto-prepared, spellbook -> not prepared until player chooses.
    prepared: baseSpell.level === 0 || mode !== "spellbook",
    notes: "",
  };
};

export const getCatalogSpellOptions = (
  className: string,
  campaignId?: string | null,
) => sortCatalogSpells(
  className
    ? getBaseSpellsForClass(className, 9, campaignId)
    : getBaseSpells(campaignId),
);

export const selectCatalogSpellForSheet = (
  spellIdentifier: string,
  className: string,
  mode: SpellcastingData["mode"],
  campaignId?: string | null,
  existingSpell?: Spell | null,
): Spell | null => {
  const nextSpell = toSheetSpell(spellIdentifier, className, mode, campaignId);
  if (!nextSpell) return null;

  return {
    ...nextSpell,
    id: existingSpell?.id ?? nextSpell.id,
    prepared:
      nextSpell.level === 0
        ? true
        : existingSpell?.prepared ?? nextSpell.prepared,
    notes: existingSpell?.notes ?? "",
  };
};

export const hasUnresolvedCreationSpellSelections = (
  spellcasting: SpellcastingData | null,
  className: string,
  campaignId?: string | null,
) => {
  if (!spellcasting) return false;

  const availableSpellKeys = new Set(
    getCatalogSpellOptions(className, campaignId).map((spell) => spell.canonicalKey.toLowerCase()),
  );

  return spellcasting.spells.some((spell) => {
    const lookup = spell.canonicalKey?.trim().toLowerCase();
    return !lookup || !availableSpellKeys.has(lookup);
  });
};

const ensureFixedStartingSpells = (
  spells: Spell[],
  className: string,
  level: number,
  mode: SpellcastingData["mode"],
  campaignId?: string | null,
) => {
  const fixedSpells = [
    ...getFixedSpellKeys(className, level, "cantrip"),
    ...getFixedSpellKeys(className, level, "leveled"),
  ]
    .map((spellKey) => toSheetSpell(spellKey, className, mode, campaignId))
    .filter((spell): spell is Spell => spell !== null);

  const merged = [...spells];
  for (const fixedSpell of fixedSpells) {
    const existingIndex = merged.findIndex((spell) =>
      spellMatchesBaseSpell(spell, fixedSpell.name, fixedSpell.canonicalKey ?? ""),
    );
    if (existingIndex >= 0) {
      merged[existingIndex] = {
        ...fixedSpell,
        ...merged[existingIndex],
        canonicalKey: fixedSpell.canonicalKey,
        name: merged[existingIndex]?.name || fixedSpell.name,
        level: merged[existingIndex]?.level ?? fixedSpell.level,
        school: merged[existingIndex]?.school || fixedSpell.school,
        prepared:
          merged[existingIndex]?.level === 0
            ? true
            : merged[existingIndex]?.prepared ?? fixedSpell.prepared,
        notes: merged[existingIndex]?.notes ?? "",
      };
      continue;
    }
    merged.push(fixedSpell);
  }
  return merged;
};

const prioritizeFixedSpells = (
  spells: Spell[],
  fixedSpellKeys: string[],
) => {
  if (fixedSpellKeys.length === 0) return spells;
  const fixedLookup = new Set(fixedSpellKeys.map((key) => key.toLowerCase()));
  const fixed = spells.filter((spell) => spell.canonicalKey && fixedLookup.has(spell.canonicalKey.toLowerCase()));
  const rest = spells.filter((spell) => !spell.canonicalKey || !fixedLookup.has(spell.canonicalKey.toLowerCase()));
  return [...fixed, ...rest];
};

export const getFixedStartingSpellCanonicalKeys = (
  className: string,
  level: number,
): string[] => uniqueSpellKeys([
  ...getFixedSpellKeys(className, level, "cantrip"),
  ...getFixedSpellKeys(className, level, "leveled"),
]);

export const getFixedStartingSpells = (
  className: string,
  level: number,
  campaignId?: string | null,
) => getFixedStartingSpellCanonicalKeys(className, level)
  .map((spellKey) => findBaseSpell(spellKey, campaignId))
  .filter((spell): spell is NonNullable<ReturnType<typeof findBaseSpell>> => spell !== undefined);

export const getStartingSpellLimits = (
  className: string,
  abilities: CharacterSheet["abilities"],
  level: number,
) => {
  const config = getClassCreationConfig(className)?.startingSpells;
  if (!config) return null;
  if (config.minimumLevel && level < config.minimumLevel) return null;

  const levelConfig = config.byLevel?.[level] ?? {};
  const cantrips = levelConfig.cantrips ?? config.cantrips;
  const effectivePreparationAbility = config.preparationAbility;
  const leveledMode = config.leveledMode;
  const fixedCantripCount = getFixedSpellKeys(className, level, "cantrip").length;
  const fixedLeveledCount = getFixedSpellKeys(className, level, "leveled").length;

  const leveledSpells =
    leveledMode === "prepared" && effectivePreparationAbility
      ? Math.max(1, level + getModifier(abilities[effectivePreparationAbility]))
      : (levelConfig.leveledSpells ?? config.leveledSpells);

  return {
    cantrips: Math.max(cantrips, fixedCantripCount),
    leveledSpells: Math.max(leveledSpells, fixedLeveledCount),
    leveledMode,
    levelOneSlots: levelConfig.levelOneSlots ?? config.levelOneSlots ?? 0,
  };
};

export const getAvailableStartingSpells = (className: string, campaignId?: string | null) => {
  const spells = getBaseSpellsForClass(className, 1, campaignId);
  return {
    cantrips: spells.filter((spell) => spell.level === 0),
    leveled: spells.filter((spell) => spell.level === 1),
  };
};

export const normalizeCreationSpellSelection = (
  spellcasting: SpellcastingData | null,
  className: string,
  abilities: CharacterSheet["abilities"],
  level: number,
  campaignId?: string | null,
): SpellcastingData | null => {
  if (!spellcasting) return null;

  const config = getClassCreationConfig(className)?.startingSpells;
  if (!config) return spellcasting;
  const limits = getStartingSpellLimits(className, abilities, level);
  if (!limits) return null;

  const mode = spellcasting.mode;
  const allowedSpells = getBaseSpellsForClass(className, 1, campaignId);
  const allowedSpellKeys = new Set(allowedSpells.map((spell) => spell.canonicalKey.toLowerCase()));
  const allowedSpellNames = new Set(allowedSpells.map((spell) => spell.name.toLowerCase()));
  const selected = ensureFixedStartingSpells(
    spellcasting.spells.filter((spell) =>
      (spell.canonicalKey && allowedSpellKeys.has(spell.canonicalKey.toLowerCase())) ||
      allowedSpellNames.has(spell.name.toLowerCase()),
    ),
    className,
    level,
    mode,
    campaignId,
  );
  const cantrips = prioritizeFixedSpells(
    selected.filter((spell) => spell.level === 0),
    getFixedSpellKeys(className, level, "cantrip"),
  ).slice(0, limits.cantrips);
  const leveled = prioritizeFixedSpells(
    selected.filter((spell) => spell.level === 1),
    getFixedSpellKeys(className, level, "leveled"),
  ).slice(0, limits.leveledSpells);

  return {
    ...spellcasting,
    slots: {
      ...spellcasting.slots,
      1: { max: limits.levelOneSlots, used: Math.min(spellcasting.slots[1]?.used ?? 0, limits.levelOneSlots) },
    },
    spells: sortSpells(
      [...cantrips, ...leveled].map((spell) => ({
        ...spell,
        // Cantrips always prepared. Leveled: known/prepared → auto-prepared, spellbook → not until chosen.
        prepared: spell.level === 0 ? true : mode !== "spellbook",
      })),
    ),
  };
};

export const toggleStartingSpell = (
  spellcasting: SpellcastingData | null,
  className: string,
  abilities: CharacterSheet["abilities"],
  level: number,
  spellName: string,
  campaignId?: string | null,
): SpellcastingData | null => {
  if (!spellcasting) return null;
  const limits = getStartingSpellLimits(className, abilities, level);
  const spell = findBaseSpell(spellName, campaignId);
  if (!limits || !spell || spell.level > 1) return spellcasting;
  if (getFixedStartingSpellCanonicalKeys(className, level).includes(spell.canonicalKey)) {
    return spellcasting;
  }

  const existing = spellcasting.spells.find((entry) =>
    spellMatchesBaseSpell(entry, spell.name, spell.canonicalKey),
  );
  if (existing) {
    return normalizeCreationSpellSelection(
      {
        ...spellcasting,
        spells: spellcasting.spells.filter((entry) => entry.id !== existing.id),
      },
      className,
      abilities,
      level,
      campaignId,
    );
  }

  const sameLevelCount = spellcasting.spells.filter((entry) => entry.level === spell.level).length;
  const limit = spell.level === 0 ? limits.cantrips : limits.leveledSpells;
  if (sameLevelCount >= limit) {
    return spellcasting;
  }

  const nextSpell = toSheetSpell(spellName, className, spellcasting.mode, campaignId);
  if (!nextSpell) return spellcasting;

  return normalizeCreationSpellSelection(
    { ...spellcasting, spells: [...spellcasting.spells, nextSpell] },
    className,
    abilities,
    level,
    campaignId,
  );
};
