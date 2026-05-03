import { computeCarryingCapacity } from "../utils/calculations";
import type { ActiveEffect } from "../../../shared/api/combatRepo";

export const useCarryingCapacity = (
  strengthScore: number,
  activeEffects?: ActiveEffect[] | null,
) => {
  const result = computeCarryingCapacity(strengthScore, activeEffects ?? []);

  return {
    baseCarryingCapacityKg: result.baseCarryingCapacityKg,
    carryingCapacityKg: result.carryingCapacityKg,
    pushDragLiftKg: result.pushDragLiftKg,
    multiplier: result.multiplier,
    sources: result.sources,
  };
};
