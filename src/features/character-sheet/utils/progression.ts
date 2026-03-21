import { MAX_LEVEL, XP_THRESHOLDS, canLevelUp, getXpForNextLevel } from "../data/xpThresholds";

export type CharacterProgressState = {
  currentLevelThreshold: number;
  nextLevelThreshold: number | null;
  progressPercent: number;
  readyToLevelUp: boolean;
  isMaxLevel: boolean;
};

export const getCurrentLevelThreshold = (currentLevel: number): number =>
  XP_THRESHOLDS[Math.min(Math.max(currentLevel, 1), MAX_LEVEL)] ?? 0;

export const getCharacterProgressState = (
  currentLevel: number,
  experiencePoints: number,
): CharacterProgressState => {
  const currentLevelThreshold = getCurrentLevelThreshold(currentLevel);
  const nextLevelThreshold = getXpForNextLevel(currentLevel);
  const isMaxLevel = nextLevelThreshold === null;

  if (isMaxLevel) {
    return {
      currentLevelThreshold,
      nextLevelThreshold,
      progressPercent: 100,
      readyToLevelUp: false,
      isMaxLevel: true,
    };
  }

  const span = Math.max(nextLevelThreshold - currentLevelThreshold, 1);
  const progressed = Math.min(Math.max(experiencePoints - currentLevelThreshold, 0), span);

  return {
    currentLevelThreshold,
    nextLevelThreshold,
    progressPercent: Math.round((progressed / span) * 100),
    readyToLevelUp: canLevelUp(currentLevel, experiencePoints),
    isMaxLevel: false,
  };
};
