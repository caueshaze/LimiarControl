import type { Coordinate, EdgeObstacle, Obstacle } from "@limiarmap/shared-contracts";
/**
 * Resolves a cylinder-shaped AoE on the 2D tactical grid.
 *
 * Cylinder height is intentionally ignored by LimiarMap: combat targeting uses
 * the cylinder's ground projection only. Its footprint is therefore the same
 * circular Chebyshev-radius approximation used by sphere, centered on the
 * selected anchor cell, including the same line-of-effect filtering.
 */
export declare function resolveCylinder(center: Coordinate, radius: number, obstacles: Obstacle[], edgeObstacles?: EdgeObstacle[]): Coordinate[];
