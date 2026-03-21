import type { AbilityName, CharacterSheet } from "../model/characterSheet.types";
import { getClass } from "../data/classes";
import {
  computeMaxHpAtLevel,
  safeParseInt,
} from "../utils/calculations";
import { normalizeCreationSpellSelection } from "../utils/creationSpells";
import { loadSpellCatalog } from "../../../entities/dnd-base";
import { loadCreationItemCatalog } from "../utils/creationItemCatalog";
import {
  applyRaceBonusesToAbilities,
  stripRaceBonusesFromAbilities,
} from "./useCharacterSheet.creation.helpers";

const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8];

const clampAbilityScore = (value: number) => Math.max(0, Math.min(30, value));

const ABILITY_ORDER: AbilityName[] = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
];

export const preloadCreationCatalogs = async (campaignId?: string | null) => {
  await Promise.all([
    loadCreationItemCatalog(campaignId),
    loadSpellCatalog(campaignId),
  ]);
};

export const buildCreationSetField = (
  mode: "creation" | "play",
  campaignId: string | null,
) =>
  <K extends keyof CharacterSheet>(sheet: CharacterSheet, key: K, value: CharacterSheet[K]) => {
    if (mode === "creation" && key === "speed") return sheet;
    if (mode === "creation" && key === "level") {
      const level = Math.max(1, safeParseInt(String(value), 1));
      const cls = getClass(sheet.class);
      if (!cls) return { ...sheet, level };
      const maxHP = computeMaxHpAtLevel(cls.hitDice, level, sheet.abilities.constitution);
      const spellcasting = normalizeCreationSpellSelection(
        sheet.spellcasting,
        sheet.class,
        sheet.abilities,
        level,
        campaignId,
      );
      return {
        ...sheet,
        level,
        hitDiceTotal: level,
        hitDiceRemaining: level,
        maxHP,
        currentHP: maxHP,
        spellcasting,
      };
    }
    return { ...sheet, [key]: value };
  };

export const buildCreationSetAbility = (
  mode: "creation" | "play",
  campaignId: string | null,
) =>
  (sheet: CharacterSheet, ability: AbilityName, value: number) => {
    if (mode === "creation") {
      if (!STANDARD_ARRAY.includes(value)) return sheet;
      const baseAbilities = stripRaceBonusesFromAbilities(sheet.abilities, sheet.race, sheet.raceConfig);
      const previousValue = baseAbilities[ability];
      const swappedAbility = ABILITY_ORDER.find((entry) => entry !== ability && baseAbilities[entry] === value);
      const nextBase = { ...baseAbilities, [ability]: value };
      if (swappedAbility) nextBase[swappedAbility] = previousValue;
      const nextAbilities = applyRaceBonusesToAbilities(nextBase, sheet.race, sheet.raceConfig);
      const cls = getClass(sheet.class);
      if (!cls) {
        return {
          ...sheet,
          abilities: nextAbilities,
          spellcasting: normalizeCreationSpellSelection(
            sheet.spellcasting,
            sheet.class,
            nextAbilities,
            sheet.level,
            campaignId,
          ),
        };
      }
      const maxHP = computeMaxHpAtLevel(cls.hitDice, sheet.level, nextAbilities.constitution);
      return {
        ...sheet,
        abilities: nextAbilities,
        maxHP,
        currentHP: maxHP,
        spellcasting: normalizeCreationSpellSelection(
          sheet.spellcasting,
          sheet.class,
          nextAbilities,
          sheet.level,
          campaignId,
        ),
      };
    }

    return {
      ...sheet,
      abilities: {
        ...sheet.abilities,
        [ability]: clampAbilityScore(value),
      },
    };
  };
