import { computeCarryingCapacity } from "../utils/calculations";
import type { ActiveEffect } from "../../../shared/api/combatRepo";
import type { CreatureSize } from "@limiarmap/shared-contracts";

export const useCarryingCapacity = (
  strengthScore: number,
  activeEffects?: ActiveEffect[] | null,
  effectiveSize?: CreatureSize,
) => {
  const result = computeCarryingCapacity(strengthScore, activeEffects ?? [], effectiveSize);

  return {
    baseCarryingCapacityKg: result.baseCarryingCapacityKg,
    carryingCapacityKg: result.carryingCapacityKg,
    pushDragLiftKg: result.pushDragLiftKg,
    multiplier: result.multiplier,
    sources: result.sources,
  };
};
