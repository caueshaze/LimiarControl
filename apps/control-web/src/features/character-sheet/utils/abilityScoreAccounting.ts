import type { AbilityName, CharacterSheet } from "../model/characterSheet.types";
import { stripClassLevelAbilityBonuses } from "../data/classFeatures";
import { getRace } from "../data/races";
import { computeAbilityScoreTotal } from "./calculations";

export function computeBaseAbilitiesForPointAccounting(
  abilities: Record<AbilityName, number>,
  race: CharacterSheet["race"],
  raceConfig: CharacterSheet["raceConfig"],
  className: string,
  level: number,
): Record<AbilityName, number> {
  const base = stripClassLevelAbilityBonuses({ ...abilities }, className, level);
  const raceData = getRace(race, raceConfig);
  if (raceData) {
    for (const [key, bonus] of Object.entries(raceData.abilityBonuses)) {
      base[key as AbilityName] -= bonus ?? 0;
    }
  }
  return base;
}

export function computeBaseAbilityScoreTotal(
  abilities: Record<AbilityName, number>,
  race: CharacterSheet["race"],
  raceConfig: CharacterSheet["raceConfig"],
  className: string,
  level: number,
): number {
  return computeAbilityScoreTotal(
    computeBaseAbilitiesForPointAccounting(abilities, race, raceConfig, className, level),
  );
}
