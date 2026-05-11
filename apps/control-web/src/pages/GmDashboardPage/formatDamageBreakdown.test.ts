import { describe, expect, it } from "vitest";
import { formatDamageBreakdown } from "./gmEntityActionRollDialog.helpers";
import type { CombatEntityActionResult, WeaponDamageBreakdown } from "../../shared/api/combatRepo";

const makeResult = (overrides: Partial<CombatEntityActionResult> = {}): CombatEntityActionResult => ({
  action_name: "Longsword",
  action_kind: "weapon_attack",
  damage: 8,
  healing: 0,
  ...overrides,
});

const makeBreakdown = (overrides: Partial<WeaponDamageBreakdown> = {}): WeaponDamageBreakdown => ({
  total_before_minimum: 8,
  minimum_applied: null,
  total: 8,
  components: [
    {
      id: "c1",
      kind: "base_weapon",
      source_key: null,
      source_label: "Longsword",
      dice: "1d8",
      rolls: [5],
      operation: "add",
      signed_total: 5,
      damage_type: "slashing",
      doubled_on_critical: false,
      minimum_total_damage: null,
    },
    {
      id: "c2",
      kind: "ability_modifier",
      source_key: null,
      source_label: "Modificador",
      dice: null,
      rolls: [],
      operation: "add",
      signed_total: 3,
      damage_type: "slashing",
      doubled_on_critical: false,
      minimum_total_damage: null,
    },
  ],
  ...overrides,
});

describe("formatDamageBreakdown", () => {
  // ------------------------------------------------------------------
  // Structured breakdown rendering
  // ------------------------------------------------------------------
  it("renders structured breakdown with base_weapon and ability_modifier", () => {
    const result = makeResult({ damage_breakdown: makeBreakdown() });
    const output = formatDamageBreakdown(result);

    expect(output).toContain("Longsword (1d8): 5");
    expect(output).toContain("Modificador: +3");
    expect(output).toContain("Total: 8");
  });

  it("renders negative component correctly", () => {
    const result = makeResult({
      damage_breakdown: makeBreakdown({
        total_before_minimum: 4,
        total: 4,
        components: [
          {
            id: "c1",
            kind: "base_weapon",
            source_key: null,
            source_label: "Longsword",
            dice: "1d8",
            rolls: [6],
            operation: "add",
            signed_total: 6,
            damage_type: "slashing",
            doubled_on_critical: false,
            minimum_total_damage: null,
          },
          {
            id: "c2",
            kind: "ability_modifier",
            source_key: null,
            source_label: "Modificador",
            dice: null,
            rolls: [],
            operation: "add",
            signed_total: 1,
            damage_type: "slashing",
            doubled_on_critical: false,
            minimum_total_damage: null,
          },
          {
            id: "c3",
            kind: "weapon_damage_modifier",
            source_key: "eff-reduce",
            source_label: "Aumentar/Reduzir — Reduzir",
            dice: "1d4",
            rolls: [3],
            operation: "subtract",
            signed_total: -3,
            damage_type: "slashing",
            doubled_on_critical: false,
            minimum_total_damage: 1,
          },
        ],
      }),
    });

    const output = formatDamageBreakdown(result);

    expect(output).toContain("Longsword (1d8): 6");
    expect(output).toContain("Modificador: +1");
    expect(output).toContain("Aumentar/Reduzir — Reduzir (1d4): -3");
    expect(output).toContain("Total: 4");
    expect(output).not.toContain("mínimo");
  });

  it("renders minimum_applied when floor is triggered", () => {
    const result = makeResult({
      damage_breakdown: makeBreakdown({
        total_before_minimum: -2,
        minimum_applied: 1,
        total: 1,
        components: [
          {
            id: "c1",
            kind: "base_weapon",
            source_key: null,
            source_label: "Dagger",
            dice: "1d4",
            rolls: [1],
            operation: "add",
            signed_total: 1,
            damage_type: "piercing",
            doubled_on_critical: false,
            minimum_total_damage: null,
          },
          {
            id: "c2",
            kind: "weapon_damage_modifier",
            source_key: "eff-reduce",
            source_label: "Reduce",
            dice: "1d4",
            rolls: [3],
            operation: "subtract",
            signed_total: -3,
            damage_type: "piercing",
            doubled_on_critical: false,
            minimum_total_damage: 1,
          },
        ],
      }),
    });

    const output = formatDamageBreakdown(result);

    expect(output).toContain("Dano mínimo aplicado: 1");
    expect(output).toContain("Total: 1");
  });

  // ------------------------------------------------------------------
  // Legacy fallback when damage_breakdown is null/undefined
  // ------------------------------------------------------------------
  it("falls back to legacy format when damage_breakdown is null", () => {
    const result = makeResult({
      damage_breakdown: null,
      damage_dice: "1d8",
      damage_rolls: [5],
      damage_bonus: 3,
      damage: 8,
      base_damage: 5,
    });

    const output = formatDamageBreakdown(result);

    // Should use the legacy format (no component lines)
    expect(output).not.toContain("Total:");
    expect(output).toContain("[5]");
    expect(output).toContain("= 8");
  });

  it("falls back to legacy format when damage_breakdown is undefined", () => {
    const result = makeResult({
      damage_dice: "1d8",
      damage_rolls: [5],
      damage_bonus: 3,
      damage: 8,
      base_damage: 5,
    });

    const output = formatDamageBreakdown(result);

    expect(output).not.toContain("Total:");
    expect(output).toContain("[5]");
  });

  // ------------------------------------------------------------------
  // Extra damage components
  // ------------------------------------------------------------------
  it("renders Hunter's Mark and Colossus Slayer components", () => {
    const result = makeResult({
      damage_breakdown: makeBreakdown({
        total_before_minimum: 19,
        total: 19,
        components: [
          {
            id: "c1",
            kind: "base_weapon",
            source_key: null,
            source_label: "Longsword",
            dice: "1d8",
            rolls: [6],
            operation: "add",
            signed_total: 6,
            damage_type: "slashing",
            doubled_on_critical: false,
            minimum_total_damage: null,
          },
          {
            id: "c2",
            kind: "ability_modifier",
            source_key: null,
            source_label: "Modificador",
            dice: null,
            rolls: [],
            operation: "add",
            signed_total: 3,
            damage_type: "slashing",
            doubled_on_critical: false,
            minimum_total_damage: null,
          },
          {
            id: "c3",
            kind: "extra_damage",
            source_key: "hunters_mark",
            source_label: "Hunter's Mark",
            dice: "1d6",
            rolls: [4],
            operation: "add",
            signed_total: 4,
            damage_type: "slashing",
            doubled_on_critical: true,
            minimum_total_damage: null,
          },
          {
            id: "c4",
            kind: "extra_damage",
            source_key: "colossus_slayer",
            source_label: "Assassino de Colossos",
            dice: "1d8",
            rolls: [6],
            operation: "add",
            signed_total: 6,
            damage_type: "slashing",
            doubled_on_critical: true,
            minimum_total_damage: null,
          },
        ],
      }),
    });

    const output = formatDamageBreakdown(result);

    expect(output).toContain("Hunter's Mark (1d6): +4");
    expect(output).toContain("Assassino de Colossos (1d8): +6");
    expect(output).toContain("Total: 19");
  });
});
