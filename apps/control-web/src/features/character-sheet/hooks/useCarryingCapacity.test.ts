import { describe, expect, it } from "vitest";

import { useCarryingCapacity } from "./useCarryingCapacity";
import type { ActiveEffect } from "../../../shared/api/combatRepo";
import { LB_TO_KG } from "../utils/calculations";

const makeCarryEffect = (multiplier: number): ActiveEffect => ({
  id: `carry-${multiplier}`,
  kind: "spell_effect",
  duration_type: "manual",
  created_at: "2026-05-01T00:00:00Z",
  display_label: "Enhance Ability",
  metadata: {
    source_spell_name: "Enhance Ability",
    declarative_effect: {
      type: "carrying_capacity_multiplier",
      params: { multiplier },
    },
  },
});

describe("useCarryingCapacity", () => {
  it("retorna valores base sem efeitos", () => {
    const result = useCarryingCapacity(10, []);
    expect(result.carryingCapacityKg).toBe(Math.round(10 * 15 * LB_TO_KG));
    expect(result.pushDragLiftKg).toBe(Math.round(10 * 15 * LB_TO_KG * 2));
    expect(result.multiplier).toBe(1.0);
    expect(result.sources).toEqual([]);
  });

  it("retorna valores base com activeEffects null", () => {
    const result = useCarryingCapacity(10, null);
    expect(result.multiplier).toBe(1.0);
  });

  it("retorna valores base com activeEffects undefined", () => {
    const result = useCarryingCapacity(10);
    expect(result.multiplier).toBe(1.0);
  });

  it("com Bull's Strength dobra a capacidade", () => {
    const effects = [makeCarryEffect(2)];
    const result = useCarryingCapacity(16, effects);
    expect(result.carryingCapacityKg).toBe(Math.round(16 * 15 * LB_TO_KG * 2));
    expect(result.multiplier).toBe(2);
  });

  it("STR 0 retorna 0 kg", () => {
    const result = useCarryingCapacity(0, []);
    expect(result.carryingCapacityKg).toBe(0);
    expect(result.pushDragLiftKg).toBe(0);
  });
});
