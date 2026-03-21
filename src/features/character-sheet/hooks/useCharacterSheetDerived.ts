import {
  computeAC,
  computeACBreakdown,
  computeInitiative,
  computePassivePerception,
  computeSpellAttack,
  computeSpellSaveDC,
  getModifier,
  getProficiencyBonus,
} from "../utils/calculations";
import type { CharacterSheet } from "../model/characterSheet.types";

export const useCharacterSheetDerived = (sheet: CharacterSheet) => {
  const dexMod = getModifier(sheet.abilities.dexterity);
  const ac = computeAC(sheet.equippedArmor, sheet.equippedShield, dexMod, sheet.miscACBonus);
  const acBreakdown = computeACBreakdown(
    sheet.equippedArmor,
    sheet.equippedShield,
    dexMod,
    sheet.miscACBonus,
  );
  const initiative = computeInitiative(dexMod);
  const profBonus = getProficiencyBonus(sheet.level);
  const passivePerception = computePassivePerception(sheet);

  const spellAbilityScore = sheet.spellcasting
    ? sheet.abilities[sheet.spellcasting.ability]
    : sheet.abilities.intelligence;
  const spellSaveDC = sheet.spellcasting ? computeSpellSaveDC(sheet.level, spellAbilityScore) : null;
  const spellAttack = sheet.spellcasting ? computeSpellAttack(sheet.level, spellAbilityScore) : null;

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
    spellAttack,
    spellSaveDC,
  };
};
