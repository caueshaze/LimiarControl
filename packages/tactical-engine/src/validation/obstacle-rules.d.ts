import type { Coordinate, Obstacle, ObstacleCover } from "@limiarmap/shared-contracts";
export declare function blocksEffect(obstacles: Obstacle[], coordinate: Coordinate): boolean;
export declare function blocksVision(obstacles: Obstacle[], coordinate: Coordinate): boolean;
export declare function clipsDiagonalMovement(obstacles: Obstacle[], coordinate: Coordinate): boolean;
export declare function getMovementCostMultiplier(obstacles: Obstacle[], coordinate: Coordinate): number;
export declare const COVER_RANK: Record<ObstacleCover, number>;
export declare function getHighestCover(obstacles: Obstacle[], coordinate: Coordinate): ObstacleCover;
