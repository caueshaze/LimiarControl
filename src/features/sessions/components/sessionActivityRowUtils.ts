import type { ActivityEvent, RollResolvedActivityEvent } from "../../../shared/api/sessionsRepo";
import type { LocaleKey } from "../../../shared/i18n";

export const ROLL_MODE_KEYS: Record<string, LocaleKey> = {
  advantage: "rolls.advantage",
  disadvantage: "rolls.disadvantage",
  normal: "sessionActivity.rollModeNormal",
};

export const ROLL_ABILITY_KEYS: Record<string, LocaleKey> = {
  charisma: "rolls.ability.charisma",
  constitution: "rolls.ability.constitution",
  dexterity: "rolls.ability.dexterity",
  intelligence: "rolls.ability.intelligence",
  strength: "rolls.ability.strength",
  wisdom: "rolls.ability.wisdom",
};

export const ROLL_SKILL_KEYS: Record<string, LocaleKey> = {
  acrobatics: "rolls.skill.acrobatics",
  animalHandling: "rolls.skill.animalHandling",
  arcana: "rolls.skill.arcana",
  athletics: "rolls.skill.athletics",
  deception: "rolls.skill.deception",
  history: "rolls.skill.history",
  insight: "rolls.skill.insight",
  intimidation: "rolls.skill.intimidation",
  investigation: "rolls.skill.investigation",
  medicine: "rolls.skill.medicine",
  nature: "rolls.skill.nature",
  perception: "rolls.skill.perception",
  performance: "rolls.skill.performance",
  persuasion: "rolls.skill.persuasion",
  religion: "rolls.skill.religion",
  sleightOfHand: "rolls.skill.sleightOfHand",
  stealth: "rolls.skill.stealth",
  survival: "rolls.skill.survival",
};

export function formatEntityDisplayName(event: Extract<ActivityEvent, { type: "entity" }>): string {
  return event.label ? `${event.entityName} (${event.label})` : event.entityName;
}

export function formatCurrentHp(event: Extract<ActivityEvent, { type: "entity" }>): string | null {
  if (event.currentHp == null) {
    return null;
  }
  if (event.maxHp != null) {
    return `${event.currentHp}/${event.maxHp}`;
  }
  return String(event.currentHp);
}

export function localizeMappedValue(
  value: string | null | undefined,
  keyMap: Record<string, LocaleKey>,
  translate: (key: LocaleKey) => string,
): string | null {
  if (!value) {
    return null;
  }
  const key = keyMap[value];
  return key ? translate(key) : value;
}

export function localizeRollMode(
  mode: string | null | undefined,
  translate: (key: LocaleKey) => string,
): string | null {
  return localizeMappedValue(mode, ROLL_MODE_KEYS, translate);
}

export function localizeRollContext(
  ability: string | null | undefined,
  skill: string | null | undefined,
  translate: (key: LocaleKey) => string,
): string | null {
  return (
    localizeMappedValue(ability, ROLL_ABILITY_KEYS, translate)
    ?? localizeMappedValue(skill, ROLL_SKILL_KEYS, translate)
  );
}

export function formatSignedModifier(value: number): string {
  if (value < 0) {
    return `- ${Math.abs(value)}`;
  }
  return `+ ${value}`;
}

export function formatResolvedRollBreakdown(
  event: RollResolvedActivityEvent,
  rollDetailLabel: string,
): string {
  const displayRolls =
    event.advantageMode === "normal"
      ? [event.selectedRoll]
      : event.rolls.length > 0
        ? event.rolls
        : [event.selectedRoll];

  const rollsText =
    event.advantageMode === "normal"
      ? String(displayRolls[0] ?? event.selectedRoll)
      : `[${displayRolls.join(", ")}] → ${event.selectedRoll}`;

  return `${rollDetailLabel} ${rollsText} ${formatSignedModifier(event.modifierUsed)}`;
}
