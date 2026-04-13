import type { AbilityName, CharacterSheet } from "../model/characterSheet.types";
import { getClass } from "../data/classes";
import {
  buildClassFeatures,
  getFixedFightingStyleForClassLevel,
  getFixedSubclassForClassLevel,
  swapClassLevelAbilityBonuses,
  stripClassLevelAbilityBonuses,
  applyClassLevelAbilityBonuses,
} from "../data/classFeatures";
import {
  computeMaxHpAtLevel,
  safeParseInt,
} from "../utils/calculations";
import { loadSpellCatalog } from "../../../entities/dnd-base";
import { loadCreationItemCatalog } from "../utils/creationItemCatalog";
import {
  applyRaceBonusesToAbilities,
  stripRaceBonusesFromAbilities,
} from "./creationAbilities";
import { buildCreationSpellcasting } from "./creationProficiencies";

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
    if (mode === "creation" && key === "speedMeters") return sheet;
    if (mode === "creation" && key === "level") {
      const level = Math.max(1, safeParseInt(String(value), 1));
      const cls = getClass(sheet.class);
      const abilities = swapClassLevelAbilityBonuses(
        sheet.abilities,
        sheet.class,
        sheet.level,
        sheet.class,
        level,
      );
      if (!cls) return { ...sheet, level, abilities, classFeatures: buildClassFeatures(sheet.class, level, null, sheet.subclassConfig) };
      const fixedSubclass = getFixedSubclassForClassLevel(sheet.class, level);
      const fixedFightingStyle = getFixedFightingStyleForClassLevel(sheet.class, level);
      const nextSubclass = fixedSubclass ?? (sheet.class === "guardian" ? null : sheet.subclass);
      const nextFightingStyle = fixedFightingStyle ?? (sheet.class === "guardian" ? null : sheet.fightingStyle);
      const maxHP = computeMaxHpAtLevel(cls.hitDice, level, abilities.constitution);
      const spellcasting = buildCreationSpellcasting(
        sheet.class,
        cls.spellcastingAbility,
        abilities,
        level,
        sheet.spellcasting,
        campaignId,
      );
      return {
        ...sheet,
        level,
        abilities,
        subclass: nextSubclass,
        fightingStyle: nextFightingStyle,
        classFeatures: buildClassFeatures(sheet.class, level, nextSubclass, sheet.subclassConfig),
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
  options: {
    allowCreationEditing?: boolean;
  } = {},
) =>
  (sheet: CharacterSheet, ability: AbilityName, value: number) => {
    const allowCreationEditing = options.allowCreationEditing ?? false;
    if (mode === "creation") {
      if (!allowCreationEditing && !STANDARD_ARRAY.includes(value)) return sheet;
      const baseAbilities = stripClassLevelAbilityBonuses(
        stripRaceBonusesFromAbilities(sheet.abilities, sheet.race, sheet.raceConfig),
        sheet.class,
        sheet.level,
      );
      const nextBase = { ...baseAbilities, [ability]: clampAbilityScore(value) };
      if (!allowCreationEditing) {
        const previousValue = baseAbilities[ability];
        const swappedAbility = ABILITY_ORDER.find((entry) => entry !== ability && baseAbilities[entry] === value);
        if (swappedAbility) nextBase[swappedAbility] = previousValue;
      }
      const nextAbilities = applyClassLevelAbilityBonuses(
        applyRaceBonusesToAbilities(nextBase, sheet.race, sheet.raceConfig),
        sheet.class,
        sheet.level,
      );
      const cls = getClass(sheet.class);
      if (!cls) {
        return {
          ...sheet,
          abilities: nextAbilities,
          spellcasting: sheet.spellcasting,
        };
      }
      const maxHP = computeMaxHpAtLevel(cls.hitDice, sheet.level, nextAbilities.constitution);
      return {
        ...sheet,
        abilities: nextAbilities,
        maxHP,
        currentHP: maxHP,
        spellcasting: buildCreationSpellcasting(
          sheet.class,
          cls.spellcastingAbility,
          nextAbilities,
          sheet.level,
          sheet.spellcasting,
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
