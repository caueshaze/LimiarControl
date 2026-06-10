import { getBaseSpells, resolveSpellByAuthority, type BaseSpell } from "../../entities/dnd-base";
import type { Spell } from "../../features/character-sheet/model/characterSheet.types";
import { getCatalogSpellOptions } from "../../features/character-sheet/utils/creationSpells";
import type { Locale } from "../../shared/i18n";

export const buildSpellPreparationCatalog = (
  catalogReady: boolean,
  characterClass: string | null | undefined,
  campaignId: string | null | undefined,
): BaseSpell[] => {
  if (!catalogReady) {
    return [];
  }

  const classScopedCatalog = getCatalogSpellOptions(characterClass ?? "", campaignId);
  if (classScopedCatalog.length > 0) {
    return classScopedCatalog;
  }

  return getBaseSpells(campaignId);
};

export const resolveSpellPreparationDisplayName = (
  spellCatalog: readonly BaseSpell[],
  spell: Spell,
  locale: Locale,
): string => {
  const match = resolveSpellByAuthority(spellCatalog, spell);
  if (match) {
    return locale === "pt" ? match.namePt ?? match.name : match.name;
  }
  return spell.name;
};
