import { describe, expect, it } from "vitest";

import { MAX_LEVEL, canLevelUp, getXpForNextLevel } from "./xpThresholds";
import { getCharacterProgressState } from "../utils/progression";

describe("xpThresholds", () => {
  it("returns the correct threshold for the next level", () => {
    expect(getXpForNextLevel(1)).toBe(300);
    expect(getXpForNextLevel(2)).toBe(900);
    expect(getXpForNextLevel(19)).toBe(355000);
  });

  it("allows leveling only when the threshold is met", () => {
    expect(canLevelUp(1, 299)).toBe(false);
    expect(canLevelUp(1, 300)).toBe(true);
    expect(canLevelUp(2, 899)).toBe(false);
    expect(canLevelUp(2, 900)).toBe(true);
  });

  it("does not allow level-up past level 20", () => {
    expect(MAX_LEVEL).toBe(20);
    expect(getXpForNextLevel(20)).toBeNull();
    expect(canLevelUp(20, 999999)).toBe(false);
  });

  it("computes the progress state for the current level band", () => {
    expect(getCharacterProgressState(1, 150)).toMatchObject({
      currentLevelThreshold: 0,
      nextLevelThreshold: 300,
      progressPercent: 50,
      readyToLevelUp: false,
      isMaxLevel: false,
    });
    expect(getCharacterProgressState(20, 355000)).toMatchObject({
      nextLevelThreshold: null,
      progressPercent: 100,
      readyToLevelUp: false,
      isMaxLevel: true,
    });
  });
});
