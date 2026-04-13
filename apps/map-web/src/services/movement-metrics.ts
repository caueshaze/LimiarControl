import { METERS_PER_CELL } from "@limiarmap/shared-contracts";

const PATH_COST_UNITS_PER_CELL = 5;
const metersFormatter = new Intl.NumberFormat("pt-BR", {
  maximumFractionDigits: 1,
});

export function pathCostUnitsToMeters(pathCostUnits: number): number {
  return (pathCostUnits / PATH_COST_UNITS_PER_CELL) * METERS_PER_CELL;
}

export function movementSpeedCellsToMeters(movementSpeedCells: number): number {
  return movementSpeedCells * METERS_PER_CELL;
}

export function formatMeters(value: number): string {
  const rounded = Math.max(0, Math.round(value * 10) / 10);
  return metersFormatter.format(rounded);
}

export function formatPathCostUnitsAsMeters(pathCostUnits: number): string {
  return formatMeters(pathCostUnitsToMeters(pathCostUnits));
}

export function formatMovementSpeedCellsAsMeters(movementSpeedCells: number): string {
  return formatMeters(movementSpeedCellsToMeters(movementSpeedCells));
}
