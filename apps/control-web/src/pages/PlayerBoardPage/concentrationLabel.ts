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

export const getConcentrationReplacementNotice = (
  previous: ActiveConcentration | null | undefined,
  next: ActiveConcentration | null | undefined,
): { previousLabel: string | null; nextLabel: string | null } | null => {
  if (!next) return null;
  if (!previous) return null;

  const prevGroup = previous.concentrationGroup ?? null;
  const nextGroup = next.concentrationGroup ?? null;

  if (prevGroup && nextGroup && prevGroup === nextGroup) return null;

  if (!prevGroup && !nextGroup) {
    const prevLabel = formatActiveConcentrationLabel(previous);
    const nextLabel = formatActiveConcentrationLabel(next);
    if (prevLabel === nextLabel) return null;
  }

  return {
    previousLabel: formatActiveConcentrationLabel(previous),
    nextLabel: formatActiveConcentrationLabel(next),
  };
};


