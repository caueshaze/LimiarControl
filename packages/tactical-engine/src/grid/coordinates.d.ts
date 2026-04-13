import type { Coordinate } from "@limiarmap/shared-contracts";
export declare function coordinateKey({ x, y }: Coordinate): string;
export declare function isSameCoordinate(a: Coordinate, b: Coordinate): boolean;
export declare function chebyshevDistance(a: Coordinate, b: Coordinate): number;
export declare function manhattanDistance(a: Coordinate, b: Coordinate): number;
