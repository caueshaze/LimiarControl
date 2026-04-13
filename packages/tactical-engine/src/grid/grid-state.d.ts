import type { BattleMap, Coordinate, Obstacle, Token } from "@limiarmap/shared-contracts";
export interface GridState {
    map: BattleMap;
    obstacles: Obstacle[];
    tokens: Token[];
}
export declare function isInsideMap(gridState: GridState, coordinate: Coordinate): boolean;
export declare function isBlockedCell(gridState: GridState, coordinate: Coordinate): boolean;
export declare function findOccupyingToken(gridState: GridState, coordinate: Coordinate): Token | undefined;
