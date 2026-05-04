import type { ActiveConcentration } from "../../entities/character";

export const formatActiveConcentrationLabel = (
  concentration: ActiveConcentration | null | undefined,
): string | null => {
  if (!concentration) return null;
  const { spellName, variantLabel, spellKey } = concentration;
  if (spellName && variantLabel) return `${spellName} \u2014 ${variantLabel}`;
  if (variantLabel) return variantLabel;
  if (spellName) return spellName;
  if (spellKey) return spellKey;
  return null;
};
