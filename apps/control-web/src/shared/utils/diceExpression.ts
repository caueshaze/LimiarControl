export type ParsedDiceExpression = {
  count: number;
  sides: number;
  modifier: number;
};

const DICE_EXPRESSION_RE = /^\s*(\d+)d(\d+)(?:\s*([+-])\s*(\d+))?\s*$/i;

export const parseDiceExpression = (expression?: string | null): ParsedDiceExpression | null => {
  if (!expression) return null;
  const match = DICE_EXPRESSION_RE.exec(expression.trim());
  if (!match) return null;

  const count = Number(match[1]);
  const sides = Number(match[2]);
  const sign = match[3] === "-" ? -1 : 1;
  const modifier = match[4] ? sign * Number(match[4]) : 0;

  if (!Number.isFinite(count) || !Number.isFinite(sides) || count <= 0 || sides <= 0) {
    return null;
  }

  return { count, sides, modifier };
};

export const getDamageRollCount = (
  expression?: string | null,
  isCritical = false,
): number => {
  const parsed = parseDiceExpression(expression);
  if (!parsed) return 0;
  return parsed.count * (isCritical ? 2 : 1);
};

export const getDamageRollSides = (expression?: string | null): number => {
  const parsed = parseDiceExpression(expression);
  return parsed?.sides ?? 0;
};

export const formatDamageDiceExpression = (
  expression?: string | null,
  isCritical = false,
): string | null => {
  if (!expression) return null;

  const parsed = parseDiceExpression(expression);
  if (!parsed) return expression.trim();

  const count = parsed.count * (isCritical ? 2 : 1);
  const modifier =
    parsed.modifier === 0
      ? ""
      : parsed.modifier > 0
        ? ` + ${parsed.modifier}`
        : ` - ${Math.abs(parsed.modifier)}`;

  return `${count}d${parsed.sides}${modifier}`;
};
