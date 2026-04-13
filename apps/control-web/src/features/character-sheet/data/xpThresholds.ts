/** D&D 5e XP thresholds per level (PHB p.15). */
export const XP_THRESHOLDS: Record<number, number> = {
  1: 0,
  2: 300,
  3: 900,
  4: 2700,
  5: 6500,
  6: 14000,
  7: 23000,
  8: 34000,
  9: 48000,
  10: 64000,
  11: 85000,
  12: 100000,
  13: 120000,
  14: 140000,
  15: 165000,
  16: 195000,
  17: 225000,
  18: 265000,
  19: 305000,
  20: 355000,
};

export const MAX_LEVEL = 20;

/** Returns XP needed to reach the next level, or null if already at max. */
export const getXpForNextLevel = (currentLevel: number): number | null =>
  currentLevel >= MAX_LEVEL ? null : XP_THRESHOLDS[currentLevel + 1] ?? null;

/** Returns true if the character has enough XP to level up. */
export const canLevelUp = (currentLevel: number, xp: number): boolean => {
  const threshold = getXpForNextLevel(currentLevel);
  return threshold !== null && xp >= threshold;
};
