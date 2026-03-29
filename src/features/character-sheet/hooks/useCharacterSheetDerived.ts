import {
  computeInitiative,
  computePassivePerception,
  computeSpellAttack,
  computeSpellSaveDC,
  getModifier,
  getProficiencyBonus,
} from "../utils/calculations";
import {
  buildCharacterAcStateFromSheet,
  calculateArmorClass,
  getArmorClassBreakdownRows,
} from "../utils/armorClass";
import type { CharacterSheet } from "../model/characterSheet.types";
import {
  getDraconicLineageState,
  resolveElementalAffinityEligibility,
} from "../data/draconicAncestry";
import { resolveDragonbornLineageState } from "../data/dragonbornAncestries";

export const useCharacterSheetDerived = (sheet: CharacterSheet) => {
  const acResult = calculateArmorClass(buildCharacterAcStateFromSheet(sheet));
  const ac = acResult.total;
  const acBreakdown = getArmorClassBreakdownRows(acResult);
  const dexMod = getModifier(sheet.abilities.dexterity);
  const initiative = computeInitiative(dexMod);
  const profBonus = getProficiencyBonus(sheet.level);
  const passivePerception = computePassivePerception(sheet);

  const spellAbilityScore = sheet.spellcasting
    ? sheet.abilities[sheet.spellcasting.ability]
    : sheet.abilities.intelligence;
  const spellSaveDC = sheet.spellcasting ? computeSpellSaveDC(sheet.level, spellAbilityScore) : null;
  const spellAttack = sheet.spellcasting ? computeSpellAttack(sheet.level, spellAbilityScore) : null;
  const draconicLineage = getDraconicLineageState({
    classId: sheet.class,
    subclass: sheet.subclass,
    level: sheet.level,
    subclassConfig: sheet.subclassConfig,
  });
  const elementalAffinity = resolveElementalAffinityEligibility({
    classId: sheet.class,
    subclass: sheet.subclass,
    level: sheet.level,
    subclassConfig: sheet.subclassConfig,
    spellDamageType: draconicLineage.damageType,
    charismaScore: sheet.abilities.charisma,
  });
  const dragonbornLineage = resolveDragonbornLineageState({
    raceId: sheet.race,
    raceConfig: sheet.raceConfig,
  });
  const resistances = [...new Set([
    ...dragonbornLineage.resistances,
    ...draconicLineage.resistances,
  ])];

  const hpPercent = sheet.maxHP > 0 ? (sheet.currentHP / sheet.maxHP) * 100 : 0;
  const hpColor =
    hpPercent > 50 ? "bg-emerald-500" : hpPercent > 25 ? "bg-amber-500" : "bg-rose-500";
  const hpTextColor =
    hpPercent > 50 ? "text-emerald-400" : hpPercent > 25 ? "text-amber-400" : "text-rose-400";

  return {
    ac,
    acBreakdown,
    hpColor,
    hpPercent,
    hpTextColor,
    initiative,
    passivePerception,
    profBonus,
    dragonbornAncestry: dragonbornLineage.ancestry,
    dragonbornAncestryLabel: dragonbornLineage.ancestryLabel,
    dragonbornDamageType: dragonbornLineage.damageType,
    dragonbornResistanceType: dragonbornLineage.resistanceType,
    dragonbornBreathWeaponShape: dragonbornLineage.breathWeaponShape,
    dragonbornBreathWeaponSaveType: dragonbornLineage.breathWeaponSaveType,
    dragonbornBreathWeaponAreaSize: dragonbornLineage.breathWeaponAreaSize,
    draconicAncestry: draconicLineage.ancestry,
    draconicAncestryLabel: draconicLineage.ancestryLabel,
    draconicDamageType: draconicLineage.damageType,
    draconicResistanceType: draconicLineage.resistanceType,
    hasElementalAffinity: draconicLineage.hasElementalAffinity,
    elementalAffinityDamageType: elementalAffinity.damageType,
    elementalAffinityBonus: elementalAffinity.bonus,
    resistances,
    spellAttack,
    spellSaveDC,
  };
};
