type BonusSource = { label: string; value: number };

const formatSignedBonus = (value: number): string =>
  value >= 0 ? `+${value}` : `${value}`;

export const formatPassiveBonusBreakdown = (
  baseValue: number,
  sources: BonusSource[],
): string => {
  if (!sources.length) return "";
  const parts = sources.map((s) => `${s.label} ${formatSignedBonus(s.value)}`);
  return `Base ${baseValue} + ${parts.join(" + ")}`;
};
