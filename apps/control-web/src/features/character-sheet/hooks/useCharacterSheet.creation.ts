import { computeMaxHpAtLevel } from "../utils/calculations";
import { getClass } from "../data/classes";
import { getBackground } from "../data/backgrounds";
import { getRace, getRaceFixedToolProficiencies, normalizeRaceState } from "../data/races";
import {
  applyClassLevelAbilityBonuses,
  buildClassFeatures,
  getFixedFightingStyleForClassLevel,
  getFixedSubclassForClassLevel,
  swapClassLevelAbilityBonuses,
} from "../data/classFeatures";
import { buildCreationLoadout, getInitialClassEquipmentSelections } from "../utils/creationEquipment";
import type { CharacterSheet } from "../model/characterSheet.types";

export { createEmptySpellcasting, applyRaceBonusesToAbilities, stripRaceBonusesFromAbilities, applyRaceBonusSwap, ABILITY_ORDER, EMPTY_SAVES } from "./creationAbilities";
export {
  buildCreationSkillProficiencies,
  deriveLanguages,
  mergeToolProficiencies,
} from "./creationProficiencies";

import { EMPTY_SAVES, applyRaceBonusSwap } from "./creationAbilities";
import {
  buildCreationSkillProficiencies,
  buildWeaponProficiencies,
  buildArmorProficiencies,
  deriveLanguages,
  countLanguageChoiceSlots,
  buildCreationSpellcasting,
  mergeToolProficiencies,
  normalizeRaceConfigForRace,
} from "./creationProficiencies";

export const normalizeCreationAfterClassChange = (
  sheet: CharacterSheet,
  className: string,
  campaignId?: string | null,
): CharacterSheet => {
  const cls = getClass(className);
  const abilities = swapClassLevelAbilityBonuses(
    sheet.abilities,
    sheet.class,
    sheet.level,
    className,
    sheet.level,
  );
  const classEquipmentSelections = getInitialClassEquipmentSelections(className);
  const loadout = buildCreationLoadout(className, sheet.background, classEquipmentSelections);
  if (!cls) {
    return {
      ...sheet,
      class: className,
      abilities,
      classSkillChoices: [],
      expertiseChoices: [],
      classEquipmentSelections,
      skillProficiencies: buildCreationSkillProficiencies(sheet.skillProficiencies, sheet.background, []),
      savingThrowProficiencies: { ...EMPTY_SAVES },
      armorProficiencies: [],
      weaponProficiencies: [],
      hitDiceType: "",
      hitDiceTotal: sheet.level,
      hitDiceRemaining: sheet.level,
      maxHP: 0,
      currentHP: 0,
      classFeatures: [],
      spellcasting: null,
      inventory: loadout.inventory,
      currency: loadout.currency,
      equippedArmor: loadout.equippedArmor,
      equippedArmorItemId: loadout.equippedArmorItemId,
      equippedShield: loadout.equippedShield,
      weapons: loadout.weapons,
    };
  }

  const filteredChoices = sheet.classSkillChoices.filter((skill) => cls.skillChoices.includes(skill));
  const trimmedChoices = filteredChoices.slice(0, cls.skillCount);
  const savingThrowProficiencies = { ...EMPTY_SAVES };
  cls.savingThrows.forEach((ability) => { savingThrowProficiencies[ability] = true; });
  const raceFixedSkills = getRace(sheet.race, sheet.raceConfig)?.skillProficiencies ?? [];
  const skillProficiencies = buildCreationSkillProficiencies(sheet.skillProficiencies, sheet.background, trimmedChoices, [], raceFixedSkills);
  const maxHP = computeMaxHpAtLevel(cls.hitDice, sheet.level, abilities.constitution);
  const subclass = getFixedSubclassForClassLevel(className, sheet.level);
  const fightingStyle = getFixedFightingStyleForClassLevel(className, sheet.level);
  const classFeatures = buildClassFeatures(className, sheet.level, subclass, null);

  return {
    ...sheet,
    class: className,
    abilities,
    subclass,
    subclassConfig: null,
    fightingStyle,
    expertiseChoices: [],
    classFeatures,
    classSkillChoices: trimmedChoices,
    classEquipmentSelections,
    skillProficiencies,
    savingThrowProficiencies,
    armorProficiencies: buildArmorProficiencies(sheet.race, className, sheet.raceConfig),
    weaponProficiencies: buildWeaponProficiencies(sheet.race, className, sheet.raceConfig),
    classToolProficiencyChoices: [],
    toolProficiencies: mergeToolProficiencies(getBackground(sheet.background)?.toolProficiencies ?? [], [], [
      ...getRaceFixedToolProficiencies(sheet.race, sheet.raceConfig),
      ...sheet.raceToolProficiencyChoices,
    ]),
    languages: deriveLanguages(sheet.race, sheet.background, sheet.languageChoices, sheet.raceConfig),
    hitDiceType: cls.hitDice,
    hitDiceTotal: sheet.level,
    hitDiceRemaining: sheet.level,
    maxHP,
    currentHP: maxHP,
    spellcasting: buildCreationSpellcasting(
      className,
      cls.spellcastingAbility,
      abilities,
      sheet.level,
      null,
      campaignId,
    ),
    inventory: loadout.inventory,
    currency: loadout.currency,
    equippedArmor: loadout.equippedArmor,
    equippedArmorItemId: loadout.equippedArmorItemId,
    equippedShield: loadout.equippedShield,
    weapons: loadout.weapons,
  };
};

export const normalizeCreationAfterBackgroundChange = (
  sheet: CharacterSheet,
  backgroundName: string,
): CharacterSheet => {
  const bg = getBackground(backgroundName);
  const nextBackgroundId = bg?.id ?? backgroundName;
  const classTools = sheet.classToolProficiencyChoices;
  const raceFixedSkills = getRace(sheet.race, sheet.raceConfig)?.skillProficiencies ?? [];
  const toolProficiencies = mergeToolProficiencies(bg?.toolProficiencies ?? [], classTools, [
    ...getRaceFixedToolProficiencies(sheet.race, sheet.raceConfig),
    ...sheet.raceToolProficiencyChoices,
  ]);
  const skillProficiencies = buildCreationSkillProficiencies(
    sheet.skillProficiencies,
    nextBackgroundId,
    sheet.classSkillChoices,
    sheet.expertiseChoices,
    raceFixedSkills,
  );
  const loadout = buildCreationLoadout(sheet.class, nextBackgroundId, sheet.classEquipmentSelections);

  return {
    ...sheet,
    background: nextBackgroundId,
    skillProficiencies,
    toolProficiencies,
    languages: deriveLanguages(sheet.race, nextBackgroundId, sheet.languageChoices, sheet.raceConfig),
    inventory: loadout.inventory,
    currency: loadout.currency,
    equippedArmor: loadout.equippedArmor,
    equippedArmorItemId: loadout.equippedArmorItemId,
    equippedShield: loadout.equippedShield,
    weapons: loadout.weapons,
  };
};

export const normalizeCreationAfterRaceChange = (
  sheet: CharacterSheet,
  raceName: string,
  campaignId?: string | null,
): CharacterSheet => {
  const normalizedRace = normalizeRaceState(raceName, sheet.raceConfig);
  const nextRaceName = normalizedRace.raceId;
  const nextRaceConfig = normalizeRaceConfigForRace(nextRaceName, normalizedRace.raceConfig);
  const race = getRace(nextRaceName, nextRaceConfig);
  const abilities = applyRaceBonusSwap(
    sheet.abilities,
    sheet.race,
    nextRaceName,
    sheet.raceConfig,
    nextRaceConfig,
  );
  const cls = getClass(sheet.class);
  const maxHP = cls ? computeMaxHpAtLevel(cls.hitDice, sheet.level, abilities.constitution) : sheet.maxHP;
  const totalLanguageSlots = countLanguageChoiceSlots(nextRaceName, sheet.background, nextRaceConfig);
  const nextLanguageChoices = sheet.languageChoices.slice(0, totalLanguageSlots);

  // Race tool choices: keep only those still valid for the new race
  const newRaceToolOptions = race?.toolProficiencyChoices?.options ?? [];
  const nextRaceToolChoices = sheet.raceToolProficiencyChoices.filter((t) => newRaceToolOptions.includes(t));

  const raceFixedSkills = race?.skillProficiencies ?? [];
  const skillProficiencies = buildCreationSkillProficiencies(
    sheet.skillProficiencies,
    sheet.background,
    sheet.classSkillChoices,
    sheet.expertiseChoices,
    raceFixedSkills,
  );

  return {
    ...sheet,
    race: nextRaceName,
    abilities,
    speedMeters: race?.speedMeters ?? 0,
    maxHP,
    currentHP: cls ? maxHP : sheet.currentHP,
    languages: deriveLanguages(nextRaceName, sheet.background, nextLanguageChoices, nextRaceConfig),
    languageChoices: nextLanguageChoices,
    raceConfig: nextRaceConfig,
    skillProficiencies,
    weaponProficiencies: buildWeaponProficiencies(nextRaceName, sheet.class, nextRaceConfig),
    armorProficiencies: buildArmorProficiencies(nextRaceName, sheet.class, nextRaceConfig),
    raceToolProficiencyChoices: nextRaceToolChoices,
    toolProficiencies: mergeToolProficiencies(
      getBackground(sheet.background)?.toolProficiencies ?? [],
      sheet.classToolProficiencyChoices,
      [...getRaceFixedToolProficiencies(nextRaceName, nextRaceConfig), ...nextRaceToolChoices],
    ),
    spellcasting: buildCreationSpellcasting(
      sheet.class,
      cls?.spellcastingAbility ?? null,
      abilities,
      sheet.level,
      sheet.spellcasting,
      campaignId,
    ),
  };
};

export const normalizeCreationAfterRaceConfigChange = (
  sheet: CharacterSheet,
  nextRaceConfig: CharacterSheet["raceConfig"],
  campaignId?: string | null,
): CharacterSheet => {
  const normalizedRaceConfig = normalizeRaceConfigForRace(sheet.race, nextRaceConfig);
  const race = getRace(sheet.race, normalizedRaceConfig);
  const abilities = applyRaceBonusSwap(
    sheet.abilities,
    sheet.race,
    sheet.race,
    sheet.raceConfig,
    normalizedRaceConfig,
  );
  const cls = getClass(sheet.class);
  const maxHP = cls ? computeMaxHpAtLevel(cls.hitDice, sheet.level, abilities.constitution) : sheet.maxHP;
  const totalLanguageSlots = countLanguageChoiceSlots(sheet.race, sheet.background, normalizedRaceConfig);
  const nextLanguageChoices = sheet.languageChoices.slice(0, totalLanguageSlots);
  const raceFixedSkills = race?.skillProficiencies ?? [];
  const skillProficiencies = buildCreationSkillProficiencies(
    sheet.skillProficiencies,
    sheet.background,
    sheet.classSkillChoices,
    sheet.expertiseChoices,
    raceFixedSkills,
  );

  return {
    ...sheet,
    abilities,
    maxHP,
    currentHP: cls ? maxHP : sheet.currentHP,
    languages: deriveLanguages(sheet.race, sheet.background, nextLanguageChoices, normalizedRaceConfig),
    languageChoices: nextLanguageChoices,
    raceConfig: normalizedRaceConfig,
    skillProficiencies,
    weaponProficiencies: buildWeaponProficiencies(sheet.race, sheet.class, normalizedRaceConfig),
    armorProficiencies: buildArmorProficiencies(sheet.race, sheet.class, normalizedRaceConfig),
    toolProficiencies: mergeToolProficiencies(
      getBackground(sheet.background)?.toolProficiencies ?? [],
      sheet.classToolProficiencyChoices,
      [...getRaceFixedToolProficiencies(sheet.race, normalizedRaceConfig), ...sheet.raceToolProficiencyChoices],
    ),
    spellcasting: buildCreationSpellcasting(
      sheet.class,
      cls?.spellcastingAbility ?? null,
      abilities,
      sheet.level,
      sheet.spellcasting,
      campaignId,
    ),
  };
};
