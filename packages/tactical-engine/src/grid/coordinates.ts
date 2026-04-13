import type { Coordinate } from "@limiarmap/shared-contracts";

export function coordinateKey({ x, y }: Coordinate): string {
  return `${x},${y}`;
}

export function isSameCoordinate(a: Coordinate, b: Coordinate): boolean {
  return a.x === b.x && a.y === b.y;
}

export function chebyshevDistance(a: Coordinate, b: Coordinate): number {
  return Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y));
}

export function manhattanDistance(a: Coordinate, b: Coordinate): number {
  return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}
