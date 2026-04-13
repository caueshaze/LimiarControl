import type { LocaleKey } from "../../../shared/i18n";
import type { AbilityName } from "../model/characterSheet.types";

const ABILITY_LOCALE_KEYS: Record<AbilityName, LocaleKey> = {
  strength: "sheet.abilities.strength",
  dexterity: "sheet.abilities.dexterity",
  constitution: "sheet.abilities.constitution",
  intelligence: "sheet.abilities.intelligence",
  wisdom: "sheet.abilities.wisdom",
  charisma: "sheet.abilities.charisma",
};

export const getAbilityLabel = (
  ability: AbilityName,
  t: (key: LocaleKey) => string,
): string => t(ABILITY_LOCALE_KEYS[ability]);
