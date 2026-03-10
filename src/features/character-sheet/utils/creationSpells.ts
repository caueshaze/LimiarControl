import { nanoid } from "nanoid";
import { findBaseSpell, getBaseSpellsForClass } from "../../../entities/dnd-base";
import { getModifier } from "./calculations";
import { getClassCreationConfig } from "../data/classCreation";
import type { CharacterSheet, Spell, SpellcastingData } from "../model/characterSheet.types";

const sortSpells = (spells: Spell[]) =>
  [...spells].sort((left, right) => left.level - right.level || left.name.localeCompare(right.name));

export const getStartingSpellLimits = (
  className: string,
  abilities: CharacterSheet["abilities"],
  level: number,
) => {
  const config = getClassCreationConfig(className)?.startingSpells;
  if (!config) return null;

  const cantrips = config.cantrips;
  const leveledSpells =
    config.leveledMode === "prepared" && config.preparationAbility
      ? Math.max(1, level + getModifier(abilities[config.preparationAbility]))
      : config.leveledSpells;

  return {
    cantrips,
    leveledSpells,
    leveledMode: config.leveledMode,
    levelOneSlots: config.levelOneSlots ?? 0,
  };
};

export const getAvailableStartingSpells = (className: string) => {
  const spells = getBaseSpellsForClass(className, 1);
  return {
    cantrips: spells.filter((spell) => spell.level === 0),
    leveled: spells.filter((spell) => spell.level === 1),
  };
};

const toSheetSpell = (spellName: string, className: string, level: number): Spell | null => {
  const baseSpell = findBaseSpell(spellName);
  if (!baseSpell || !baseSpell.classes.some((entry) => entry.toLowerCase() === className.toLowerCase())) {
    return null;
  }
  return {
    id: nanoid(),
    name: baseSpell.name,
    level: baseSpell.level,
    school: baseSpell.school || "Evocation",
    prepared: level === 0 || getClassCreationConfig(className)?.startingSpells?.leveledMode !== "spellbook",
    notes: "",
  };
};

export const normalizeCreationSpellSelection = (
  spellcasting: SpellcastingData | null,
  className: string,
  abilities: CharacterSheet["abilities"],
  level: number,
): SpellcastingData | null => {
  if (!spellcasting) return null;

  const limits = getStartingSpellLimits(className, abilities, level);
  if (!limits) return spellcasting;

  const allowedNames = new Set(getBaseSpellsForClass(className, 1).map((spell) => spell.name.toLowerCase()));
  const selected = spellcasting.spells.filter((spell) => allowedNames.has(spell.name.toLowerCase()));
  const cantrips = selected.filter((spell) => spell.level === 0).slice(0, limits.cantrips);
  const leveled = selected.filter((spell) => spell.level === 1).slice(0, limits.leveledSpells);

  return {
    ...spellcasting,
    slots: {
      ...spellcasting.slots,
      1: { max: limits.levelOneSlots, used: Math.min(spellcasting.slots[1]?.used ?? 0, limits.levelOneSlots) },
    },
    spells: sortSpells(
      [...cantrips, ...leveled].map((spell) => ({
        ...spell,
        prepared:
          spell.level === 0
            ? true
            : getClassCreationConfig(className)?.startingSpells?.leveledMode !== "spellbook",
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
): SpellcastingData | null => {
  if (!spellcasting) return null;
  const limits = getStartingSpellLimits(className, abilities, level);
  const spell = findBaseSpell(spellName);
  if (!limits || !spell || spell.level > 1) return spellcasting;

  const existing = spellcasting.spells.find((entry) => entry.name.toLowerCase() === spellName.toLowerCase());
  if (existing) {
    return {
      ...spellcasting,
      spells: spellcasting.spells.filter((entry) => entry.id !== existing.id),
    };
  }

  const sameLevelCount = spellcasting.spells.filter((entry) => entry.level === spell.level).length;
  const limit = spell.level === 0 ? limits.cantrips : limits.leveledSpells;
  if (sameLevelCount >= limit) {
    return spellcasting;
  }

  const nextSpell = toSheetSpell(spellName, className, level);
  if (!nextSpell) return spellcasting;

  return normalizeCreationSpellSelection(
    { ...spellcasting, spells: [...spellcasting.spells, nextSpell] },
    className,
    abilities,
    level,
  );
};
