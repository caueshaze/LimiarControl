import type { CombatState, Coordinate, Token } from "@limiarmap/shared-contracts";
import { type GridState } from "../grid/grid-state";
export interface MovementValidationResult {
    accepted: boolean;
    pathCostUnits: number;
    rejectionReason?: string;
}
export declare function validateMovement(gridState: GridState, token: Token, path: Coordinate[], combatState?: CombatState): MovementValidationResult;
