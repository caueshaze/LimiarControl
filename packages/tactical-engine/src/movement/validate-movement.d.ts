import type { CombatState, Coordinate, Token } from "@limiarmap/shared-contracts";
import { type GridState } from "../grid/grid-state";
export interface MovementValidationResult {
    accepted: boolean;
    pathCostUnits: number;
    rejectionReason?: string;
}
export interface MovementPathResult extends MovementValidationResult {
    path: Coordinate[];
}
export declare function findReachableCells(gridState: GridState, token: Token, combatState?: CombatState): Coordinate[];
export declare function validateMovement(gridState: GridState, token: Token, path: Coordinate[], combatState?: CombatState): MovementValidationResult;
export declare function findMovementPath(gridState: GridState, token: Token, destination: Coordinate, combatState?: CombatState): MovementPathResult;
