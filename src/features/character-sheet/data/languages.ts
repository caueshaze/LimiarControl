/**
 * Standard D&D 5e languages from the Player's Handbook.
 *
 * Standard languages are available to all races/backgrounds.
 * Exotic languages require specific racial or campaign context.
 */

export type LanguageTier = "standard" | "exotic";

export type DndLanguage = {
  id: string;
  name: string;
  tier: LanguageTier;
};

export const LANGUAGES: DndLanguage[] = [
  // Standard (PHB p.123)
  { id: "common", name: "Comum", tier: "standard" },
  { id: "dwarvish", name: "Anão", tier: "standard" },
  { id: "elvish", name: "Élfico", tier: "standard" },
  { id: "giant", name: "Gigante", tier: "standard" },
  { id: "gnomish", name: "Gnomo", tier: "standard" },
  { id: "goblin", name: "Goblin", tier: "standard" },
  { id: "halfling", name: "Halfling", tier: "standard" },
  { id: "orc", name: "Orc", tier: "standard" },
  // Exotic (PHB p.123)
  { id: "abyssal", name: "Abissal", tier: "exotic" },
  { id: "celestial", name: "Celestial", tier: "exotic" },
  { id: "draconic", name: "Dracônico", tier: "exotic" },
  { id: "deep-speech", name: "Dialeto Subterrâneo", tier: "exotic" },
  { id: "infernal", name: "Infernal", tier: "exotic" },
  { id: "primordial", name: "Primordial", tier: "exotic" },
  { id: "sylvan", name: "Silvestre", tier: "exotic" },
  { id: "undercommon", name: "Subcomum", tier: "exotic" },
];

/** Sentinel value used in race/background language arrays to indicate a player choice slot. */
export const LANGUAGE_CHOICE_SLOT = "__LANGUAGE_CHOICE__";

/**
 * Given a race/background language array, returns the fixed languages
 * and the number of choice slots.
 */
export const splitLanguageSlots = (
  languages: string[],
): { fixed: string[]; choiceCount: number } => {
  const fixed: string[] = [];
  let choiceCount = 0;

  for (const lang of languages) {
    if (lang === LANGUAGE_CHOICE_SLOT) {
      choiceCount++;
    } else {
      fixed.push(lang);
    }
  }

  return { fixed, choiceCount };
};

/**
 * Returns all language names that are available for selection,
 * excluding languages the character already knows.
 */
export const getAvailableLanguages = (alreadyKnown: string[]): DndLanguage[] => {
  const knownSet = new Set(alreadyKnown.map((l) => l.toLowerCase()));
  return LANGUAGES.filter((lang) => !knownSet.has(lang.name.toLowerCase()));
};
