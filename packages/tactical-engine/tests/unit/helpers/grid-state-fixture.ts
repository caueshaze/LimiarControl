import type { BattleMap, Obstacle, Token } from "@limiarmap/shared-contracts";
import type { GridState } from "../../../src";

const defaultMap: BattleMap = {
  id: "map",
  name: "map",
  gridWidth: 20,
  gridHeight: 20,
  terrainVersion: 1,
  gridCalibration: { x: 0, y: 0, width: 1, height: 1 },
};

export function makeGridState(overrides: Partial<{
  tokens: Token[];
  obstacles: Obstacle[];
  map: Partial<BattleMap>;
}>): GridState {
  return {
    map: { ...defaultMap, ...overrides.map },
    obstacles: overrides.obstacles ?? [],
    tokens: overrides.tokens ?? [],
  };
}
