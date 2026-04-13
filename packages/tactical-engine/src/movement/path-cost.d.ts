import type { Coordinate } from "@limiarmap/shared-contracts";
export declare function isDiagonalStep(from: Coordinate, to: Coordinate): boolean;
export declare function stepCost(from: Coordinate, to: Coordinate, diagonalIndex: number): number;
export declare function computePathCost(path: Coordinate[]): number;
