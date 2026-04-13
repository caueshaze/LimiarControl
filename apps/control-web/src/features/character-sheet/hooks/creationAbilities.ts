import { getRace } from "../data/races";
import type {
  AbilityName,
  CharacterSheet,
  SpellcastingData,
} from "../model/characterSheet.types";

export const clampAbilityScore = (value: number) => Math.max(0, Math.min(30, value));

export const ABILITY_ORDER: AbilityName[] = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
];

export const EMPTY_SAVES: CharacterSheet["savingThrowProficiencies"] = {
  strength: false,
  dexterity: false,
  constitution: false,
  intelligence: false,
  wisdom: false,
  charisma: false,
};

export const createEmptySpellcasting = (
  ability: AbilityName = "intelligence",
  mode: SpellcastingData["mode"] = "known",
): SpellcastingData => ({
  ability,
  mode,
  slots: Object.fromEntries(Array.from({ length: 9 }, (_, i) => [i + 1, { max: 0, used: 0 }])),
  spells: [],
});

export const applyRaceBonusesToAbilities = (
  abilities: CharacterSheet["abilities"],
  raceName: string,
  raceConfig: CharacterSheet["raceConfig"] = null,
) => {
  const race = getRace(raceName, raceConfig);
  if (!race) return { ...abilities };
  const next = { ...abilities };
  for (const [key, bonus] of Object.entries(race.abilityBonuses)) {
    const abilityKey = key as AbilityName;
    next[abilityKey] = clampAbilityScore((next[abilityKey] ?? 0) + (bonus ?? 0));
  }
  return next;
};

export const stripRaceBonusesFromAbilities = (
  abilities: CharacterSheet["abilities"],
  raceName: string,
  raceConfig: CharacterSheet["raceConfig"] = null,
) => {
  const race = getRace(raceName, raceConfig);
  if (!race) return { ...abilities };
  const next = { ...abilities };
  for (const [key, bonus] of Object.entries(race.abilityBonuses)) {
    const abilityKey = key as AbilityName;
    next[abilityKey] = clampAbilityScore((next[abilityKey] ?? 0) - (bonus ?? 0));
  }
  return next;
};

export const applyRaceBonusSwap = (
  abilities: CharacterSheet["abilities"],
  previousRaceName: string,
  nextRaceName: string,
  previousRaceConfig: CharacterSheet["raceConfig"] = null,
  nextRaceConfig: CharacterSheet["raceConfig"] = null,
) =>
  applyRaceBonusesToAbilities(
    stripRaceBonusesFromAbilities(abilities, previousRaceName, previousRaceConfig),
    nextRaceName,
    nextRaceConfig,
  );
