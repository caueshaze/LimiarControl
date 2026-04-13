import type { Coordinate, TargetingTemplate } from "@limiarmap/shared-contracts";
export interface TargetingResolutionResult extends TargetingTemplate {
    affectedCells: Coordinate[];
}
