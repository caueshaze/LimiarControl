import { describe, expect, it } from "vitest";
import {
  applyEncumbranceMovementPenalty,
  computeAbilityScoreTotal,
  computeCarryingCapacity,
  computeCarryingCapacityMultiplier,
  computeCarryingCapacityMultiplierSources,
  computeEncumbranceTier,
  computePassiveSkillBonus,
  computePassiveSkillBonusSources,
  computeProjectedEncumbranceTier,
  computeTotalWeight,
  declarativeEffectGroupKey,
  LB_TO_KG,
} from "./calculations";
import type { ActiveEffect } from "../../../shared/api/combatRepo";
import {
  computeBaseAbilitiesForPointAccounting,
  computeBaseAbilityScoreTotal,
} from "./abilityScoreAccounting";
import { ABILITY_SCORE_POOL } from "../constants";
import type { AbilityName } from "../model/characterSheet.types";

// Standard Array: 15+14+13+12+10+8 = 72
const BASE_ABILITIES: Record<AbilityName, number> = {
  strength: 15,
  dexterity: 14,
  constitution: 13,
  intelligence: 12,
  wisdom: 10,
  charisma: 8,
};

describe("computeBaseAbilitiesForPointAccounting", () => {
  it("returns abilities unchanged when no race or class bonuses", () => {
    const result = computeBaseAbilitiesForPointAccounting(
      BASE_ABILITIES,
      null,
      null,
      "",
      1,
    );
    expect(result).toEqual(BASE_ABILITIES);
  });

  it("handles raceConfig = undefined without throwing", () => {
    const result = computeBaseAbilitiesForPointAccounting(
      BASE_ABILITIES,
      null,
      undefined,
      "",
      1,
    );
    expect(result).toEqual(BASE_ABILITIES);
  });

  it("strips race bonuses per attribute — hill-dwarf: constitution −2, wisdom −1, others unchanged", () => {
    const abilitiesWithRace: Record<AbilityName, number> = {
      ...BASE_ABILITIES,
      constitution: BASE_ABILITIES.constitution + 2,
      wisdom: BASE_ABILITIES.wisdom + 1,
    };
    const result = computeBaseAbilitiesForPointAccounting(
      abilitiesWithRace,
      "hill-dwarf",
      null,
      "",
      1,
    );
    expect(result.strength).toBe(BASE_ABILITIES.strength);
    expect(result.dexterity).toBe(BASE_ABILITIES.dexterity);
    expect(result.constitution).toBe(BASE_ABILITIES.constitution);
    expect(result.intelligence).toBe(BASE_ABILITIES.intelligence);
    expect(result.wisdom).toBe(BASE_ABILITIES.wisdom);
    expect(result.charisma).toBe(BASE_ABILITIES.charisma);
  });

  it("strips Guardian level-4 class bonus per attribute — dexterity −2, others unchanged", () => {
    const abilitiesWithClass: Record<AbilityName, number> = {
      ...BASE_ABILITIES,
      dexterity: BASE_ABILITIES.dexterity + 2,
    };
    const result = computeBaseAbilitiesForPointAccounting(
      abilitiesWithClass,
      null,
      null,
      "Guardian",
      4,
    );
    expect(result.dexterity).toBe(BASE_ABILITIES.dexterity);
    expect(result.strength).toBe(BASE_ABILITIES.strength);
    expect(result.constitution).toBe(BASE_ABILITIES.constitution);
  });

  it("Guardian below level 4 — class bonus not yet active, dexterity unchanged", () => {
    const abilitiesAtLevel3: Record<AbilityName, number> = { ...BASE_ABILITIES };
    const result = computeBaseAbilitiesForPointAccounting(
      abilitiesAtLevel3,
      null,
      null,
      "Guardian",
      3,
    );
    expect(result.dexterity).toBe(BASE_ABILITIES.dexterity);
  });

  it("strips both race and class bonuses together — each attribute correct", () => {
    const abilitiesWithBoth: Record<AbilityName, number> = {
      ...BASE_ABILITIES,
      dexterity: BASE_ABILITIES.dexterity + 2,
      constitution: BASE_ABILITIES.constitution + 2,
      wisdom: BASE_ABILITIES.wisdom + 1,
    };
    const result = computeBaseAbilitiesForPointAccounting(
      abilitiesWithBoth,
      "hill-dwarf",
      null,
      "Guardian",
      4,
    );
    expect(result).toEqual(BASE_ABILITIES);
  });
});

describe("computeBaseAbilityScoreTotal", () => {
  it("valid character — base sums 72, race +3 → usedPoints 72, remaining 0", () => {
    const abilitiesWithRace: Record<AbilityName, number> = {
      ...BASE_ABILITIES,
      constitution: BASE_ABILITIES.constitution + 2,
      wisdom: BASE_ABILITIES.wisdom + 1,
    };
    const usedPoints = computeBaseAbilityScoreTotal(
      abilitiesWithRace,
      "hill-dwarf",
      null,
      "",
      1,
    );
    expect(usedPoints).toBe(ABILITY_SCORE_POOL);
    expect(ABILITY_SCORE_POOL - usedPoints).toBe(0);
  });

  it("valid character — base sums 70, race +3 → usedPoints 70, remaining 2", () => {
    const lowBase: Record<AbilityName, number> = {
      ...BASE_ABILITIES,
      charisma: 6, // 8 → 6: total drops by 2 → 70
    };
    const abilitiesWithRace: Record<AbilityName, number> = {
      ...lowBase,
      constitution: lowBase.constitution + 2,
      wisdom: lowBase.wisdom + 1,
    };
    const usedPoints = computeBaseAbilityScoreTotal(
      abilitiesWithRace,
      "hill-dwarf",
      null,
      "",
      1,
    );
    expect(usedPoints).toBe(70);
    expect(ABILITY_SCORE_POOL - usedPoints).toBe(2);
  });

  it("valid character — Guardian lv4 +2 DEX does not inflate used points", () => {
    const abilitiesWithClass: Record<AbilityName, number> = {
      ...BASE_ABILITIES,
      dexterity: BASE_ABILITIES.dexterity + 2,
    };
    const usedPoints = computeBaseAbilityScoreTotal(
      abilitiesWithClass,
      null,
      null,
      "Guardian",
      4,
    );
    expect(usedPoints).toBe(ABILITY_SCORE_POOL);
  });

  it("invalid character — base exceeds 72 → remaining is negative", () => {
    const overLimit: Record<AbilityName, number> = {
      ...BASE_ABILITIES,
      charisma: 12, // 8 → 12: total goes from 72 to 76
    };
    const usedPoints = computeBaseAbilityScoreTotal(
      overLimit,
      null,
      null,
      "",
      1,
    );
    expect(usedPoints).toBeGreaterThan(ABILITY_SCORE_POOL);
    expect(ABILITY_SCORE_POOL - usedPoints).toBeLessThan(0);
  });

  it("no race or class — same result as computeAbilityScoreTotal", () => {
    const usedPoints = computeBaseAbilityScoreTotal(
      BASE_ABILITIES,
      null,
      null,
      "",
      1,
    );
    expect(usedPoints).toBe(computeAbilityScoreTotal(BASE_ABILITIES));
  });
});

const makePassiveSkillBonusEffect = (
  skill: string,
  bonus: number,
  overrides: Partial<ActiveEffect> = {},
): ActiveEffect => ({
  id: `effect-${skill}-${bonus}`,
  kind: "spell_effect",
  duration_type: "manual",
  created_at: "2026-05-01T00:00:00Z",
  display_label: "Enhance Ability",
  metadata: {
    source_spell_name: "Enhance Ability",
    declarative_effect: {
      type: "passive_skill_bonus",
      params: { skill, bonus },
    },
  },
  ...overrides,
});

describe("computePassiveSkillBonus", () => {
  it("retorna 0 sem efeitos ativos", () => {
    expect(computePassiveSkillBonus([], "perception")).toBe(0);
  });

  it("soma bônus de um único efeito matching", () => {
    const effects = [makePassiveSkillBonusEffect("perception", 5)];
    expect(computePassiveSkillBonus(effects, "perception")).toBe(5);
  });

  it("não conta efeito de skill diferente", () => {
    const effects = [makePassiveSkillBonusEffect("stealth", 3)];
    expect(computePassiveSkillBonus(effects, "perception")).toBe(0);
  });

  it("empilha efeitos de grupos declarativos diferentes", () => {
    const effects = [
      makePassiveSkillBonusEffect("perception", 5, {
        metadata: {
          source_spell_name: "Owl's Wisdom",
          declarative_effect_group_id: "group-a",
          declarative_effect: {
            type: "passive_skill_bonus",
            params: { skill: "perception", bonus: 5 },
          },
        },
      }),
      makePassiveSkillBonusEffect("perception", 3, {
        metadata: {
          source_spell_name: "Guidance",
          declarative_effect_group_id: "group-b",
          declarative_effect: {
            type: "passive_skill_bonus",
            params: { skill: "perception", bonus: 3 },
          },
        },
      }),
    ];
    expect(computePassiveSkillBonus(effects, "perception")).toBe(8);
  });

  it("deduplica efeitos do mesmo grupo declarativo pegando o maior bônus", () => {
    const effects = [
      makePassiveSkillBonusEffect("perception", 5, {
        id: "effect-dup-a",
        metadata: {
          source_spell_name: "Owl's Wisdom",
          declarative_effect_group_id: "same-group",
          declarative_effect: {
            type: "passive_skill_bonus",
            params: { skill: "perception", bonus: 5 },
          },
        },
      }),
      makePassiveSkillBonusEffect("perception", 7, {
        id: "effect-dup-b",
        metadata: {
          source_spell_name: "Owl's Wisdom",
          declarative_effect_group_id: "same-group",
          declarative_effect: {
            type: "passive_skill_bonus",
            params: { skill: "perception", bonus: 7 },
          },
        },
      }),
    ];
    expect(computePassiveSkillBonus(effects, "perception")).toBe(7);
  });

  it("deduplica por chave composta quando não há group_id", () => {
    const effects = [
      makePassiveSkillBonusEffect("perception", 5, {
        metadata: {
          source_spell_key: "owls_wisdom",
          source_spell_name: "Owl's Wisdom",
          declarative_effect: {
            type: "passive_skill_bonus",
            params: { skill: "perception", bonus: 5 },
          },
        },
      }),
      makePassiveSkillBonusEffect("perception", 5, {
        metadata: {
          source_spell_key: "owls_wisdom",
          source_spell_name: "Owl's Wisdom",
          declarative_effect: {
            type: "passive_skill_bonus",
            params: { skill: "perception", bonus: 5 },
          },
        },
      }),
    ];
    expect(computePassiveSkillBonus(effects, "perception")).toBe(5);
  });

  it("não deduplica efeitos sem metadata de agrupamento — cada efeito é grupo único", () => {
    const effects = [
      makePassiveSkillBonusEffect("perception", 3, { id: "uniq-a" }),
      makePassiveSkillBonusEffect("perception", 2, { id: "uniq-b" }),
    ];
    expect(computePassiveSkillBonus(effects, "perception")).toBe(5);
  });

  it("ignora efeito sem declarative_effect", () => {
    const effects: ActiveEffect[] = [
      {
        id: "no-declarative",
        kind: "spell_effect",
        duration_type: "manual",
        created_at: "2026-05-01T00:00:00Z",
        metadata: { source_spell_name: "Something" },
      },
    ];
    expect(computePassiveSkillBonus(effects, "perception")).toBe(0);
  });

  it("ignora efeito com metadata nula", () => {
    const effects: ActiveEffect[] = [
      {
        id: "null-meta",
        kind: "spell_effect",
        duration_type: "manual",
        created_at: "2026-05-01T00:00:00Z",
        metadata: null,
      },
    ];
    expect(computePassiveSkillBonus(effects, "perception")).toBe(0);
  });

  it("usa display_label com fallback para source_spell_name e default", () => {
    const withDisplayLabel = makePassiveSkillBonusEffect("perception", 5, {
      display_label: "Owl's Wisdom",
    });
    const withSpellName: ActiveEffect = {
      id: "no-label",
      kind: "spell_effect",
      duration_type: "manual",
      created_at: "2026-05-01T00:00:00Z",
      display_label: null,
      metadata: {
        source_spell_name: "Enhance Ability",
        declarative_effect: {
          type: "passive_skill_bonus",
          params: { skill: "perception", bonus: 3 },
        },
      },
    };
    const withNoLabel: ActiveEffect = {
      id: "no-label-no-name",
      kind: "spell_effect",
      duration_type: "manual",
      created_at: "2026-05-01T00:00:00Z",
      display_label: null,
      metadata: {
        declarative_effect: {
          type: "passive_skill_bonus",
          params: { skill: "perception", bonus: 2 },
        },
      },
    };

    const sources = computePassiveSkillBonusSources(
      [withDisplayLabel, withSpellName, withNoLabel],
      "perception",
    );

    expect(sources[0].label).toBe("Owl's Wisdom");
    expect(sources[1].label).toBe("Enhance Ability");
    expect(sources[2].label).toBe("Passive skill bonus");
    expect(sources.map((s) => s.value)).toEqual([5, 3, 2]);
  });
});

const makeCarryingCapacityEffect = (
  multiplier: number,
  overrides: Partial<ActiveEffect> = {},
): ActiveEffect => ({
  id: `effect-carry-${multiplier}`,
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
  ...overrides,
});

describe("computeCarryingCapacity", () => {
  it("STR 10 → base 68 kg, push/drag/lift 136 kg", () => {
    const result = computeCarryingCapacity(10, []);
    expect(result.baseCarryingCapacityKg).toBe(Math.round(10 * 15 * LB_TO_KG));
    expect(result.carryingCapacityKg).toBe(result.baseCarryingCapacityKg);
    expect(result.pushDragLiftKg).toBe(result.baseCarryingCapacityKg * 2);
    expect(result.multiplier).toBe(1.0);
  });

  it("STR 16 → base 109 kg, push/drag/lift 218 kg", () => {
    const result = computeCarryingCapacity(16, []);
    expect(result.baseCarryingCapacityKg).toBe(Math.round(16 * 15 * LB_TO_KG));
    expect(result.carryingCapacityKg).toBe(result.baseCarryingCapacityKg);
    expect(result.pushDragLiftKg).toBe(result.baseCarryingCapacityKg * 2);
  });

  it("STR 16 + Bull's Strength (×2) → 218 kg carrying", () => {
    const effects = [makeCarryingCapacityEffect(2)];
    const result = computeCarryingCapacity(16, effects);
    expect(result.carryingCapacityKg).toBe(Math.round(16 * 15 * LB_TO_KG * 2));
    expect(result.pushDragLiftKg).toBe(Math.round(16 * 15 * LB_TO_KG * 4));
    expect(result.multiplier).toBe(2);
  });

  it("dois efeitos ×2 → continua 218 kg (não 436)", () => {
    const effects = [
      makeCarryingCapacityEffect(2, {
        id: "effect-carry-dup-a",
        metadata: {
          source_spell_name: "Enhance Ability",
          declarative_effect_group_id: "same-group",
          declarative_effect: { type: "carrying_capacity_multiplier", params: { multiplier: 2 } },
        },
      }),
      makeCarryingCapacityEffect(2, {
        id: "effect-carry-dup-b",
        metadata: {
          source_spell_name: "Enhance Ability",
          declarative_effect_group_id: "same-group",
          declarative_effect: { type: "carrying_capacity_multiplier", params: { multiplier: 2 } },
        },
      }),
    ];
    const result = computeCarryingCapacity(16, effects);
    expect(result.multiplier).toBe(2);
    expect(result.carryingCapacityKg).toBe(Math.round(16 * 15 * LB_TO_KG * 2));
  });

  it("efeito ×3 vs ×2 → usa ×3 (max, não sum)", () => {
    const effects = [
      makeCarryingCapacityEffect(2, {
        id: "effect-carry-x2",
        metadata: {
          source_spell_name: "Enhance Ability",
          declarative_effect_group_id: "group-x2",
          declarative_effect: { type: "carrying_capacity_multiplier", params: { multiplier: 2 } },
        },
      }),
      makeCarryingCapacityEffect(3, {
        id: "effect-carry-x3",
        metadata: {
          source_spell_name: "Another Spell",
          declarative_effect_group_id: "group-x3",
          declarative_effect: { type: "carrying_capacity_multiplier", params: { multiplier: 3 } },
        },
      }),
    ];
    const result = computeCarryingCapacity(16, effects);
    expect(result.multiplier).toBe(3);
  });

  it("pushDragLiftKg não acumula erro de arredondamento", () => {
    const effects = [makeCarryingCapacityEffect(3)];
    const result = computeCarryingCapacity(7, effects);
    const baseKg = 7 * 15 * LB_TO_KG * 3;
    expect(result.pushDragLiftKg).toBe(Math.round(baseKg * 2));
    expect(result.carryingCapacityKg).toBe(Math.round(baseKg));
  });

  it("sem active_effects → multiplier 1.0, valores base", () => {
    const result = computeCarryingCapacity(10, []);
    expect(result.multiplier).toBe(1.0);
    expect(result.carryingCapacityKg).toBe(result.baseCarryingCapacityKg);
    expect(result.sources).toEqual([]);
  });

  it("ignora efeito sem declarative_effect", () => {
    const effects: ActiveEffect[] = [
      {
        id: "no-declarative",
        kind: "spell_effect",
        duration_type: "manual",
        created_at: "2026-05-01T00:00:00Z",
        metadata: { source_spell_name: "Something" },
      },
    ];
    expect(computeCarryingCapacityMultiplier(effects)).toBe(1.0);
  });

  it("ignora efeito com metadata nula", () => {
    const effects: ActiveEffect[] = [
      {
        id: "null-meta",
        kind: "spell_effect",
        duration_type: "manual",
        created_at: "2026-05-01T00:00:00Z",
        metadata: null,
      },
    ];
    expect(computeCarryingCapacityMultiplier(effects)).toBe(1.0);
  });

  it("usa display_label com fallback para source_spell_name e default", () => {
    const withDisplayLabel = makeCarryingCapacityEffect(2, {
      id: "eff-label-1",
      display_label: "Força do Touro",
      metadata: {
        source_spell_name: "Força do Touro",
        declarative_effect_group_id: "group-a",
        declarative_effect: {
          type: "carrying_capacity_multiplier",
          params: { multiplier: 2 },
        },
      },
    });
    const withSpellName: ActiveEffect = {
      id: "eff-label-2",
      kind: "spell_effect",
      duration_type: "manual",
      created_at: "2026-05-01T00:00:00Z",
      display_label: null,
      metadata: {
        source_spell_name: "Enhance Ability",
        declarative_effect_group_id: "group-b",
        declarative_effect: {
          type: "carrying_capacity_multiplier",
          params: { multiplier: 2 },
        },
      },
    };
    const withNoLabel: ActiveEffect = {
      id: "eff-label-3",
      kind: "spell_effect",
      duration_type: "manual",
      created_at: "2026-05-01T00:00:00Z",
      display_label: null,
      metadata: {
        declarative_effect_group_id: "group-c",
        declarative_effect: {
          type: "carrying_capacity_multiplier",
          params: { multiplier: 2 },
        },
      },
    };

    const sources = computeCarryingCapacityMultiplierSources(
      [withDisplayLabel, withSpellName, withNoLabel],
    );

    expect(sources[0].label).toBe("Força do Touro");
    expect(sources[1].label).toBe("Enhance Ability");
    expect(sources[2].label).toBe("Carrying capacity bonus");
  });

  it("STR 0 → 0 kg", () => {
    const result = computeCarryingCapacity(0, []);
    expect(result.carryingCapacityKg).toBe(0);
    expect(result.pushDragLiftKg).toBe(0);
  });
});

describe("computeEncumbranceTier", () => {
  it("STR 10, 20 kg → normal", () => {
    const result = computeEncumbranceTier({ strengthScore: 10, totalWeightKg: 20 });
    expect(result.tier).toBe("normal");
    expect(result.normalMaxKg).toBe(Math.round(50 * LB_TO_KG));
    expect(result.encumberedMaxKg).toBe(Math.round(100 * LB_TO_KG));
    expect(result.heavilyEncumberedMaxKg).toBe(Math.round(150 * LB_TO_KG));
  });

  it("STR 10, 25 kg → encumbered", () => {
    const result = computeEncumbranceTier({ strengthScore: 10, totalWeightKg: 25 });
    expect(result.tier).toBe("encumbered");
  });

  it("STR 10, 50 kg → heavily_encumbered", () => {
    const result = computeEncumbranceTier({ strengthScore: 10, totalWeightKg: 50 });
    expect(result.tier).toBe("heavily_encumbered");
  });

  it("STR 10, 70 kg → overloaded", () => {
    const result = computeEncumbranceTier({ strengthScore: 10, totalWeightKg: 70 });
    expect(result.tier).toBe("overloaded");
  });

  it("STR 16, limite exato normal → normal", () => {
    const thresholdKg = 16 * 5 * LB_TO_KG;
    const result = computeEncumbranceTier({ strengthScore: 16, totalWeightKg: thresholdKg });
    expect(result.tier).toBe("normal");
  });

  it("STR 16, acima do limite normal → encumbered", () => {
    const thresholdKg = 16 * 5 * LB_TO_KG + 0.01;
    const result = computeEncumbranceTier({ strengthScore: 16, totalWeightKg: thresholdKg });
    expect(result.tier).toBe("encumbered");
  });

  it("STR 0, qualquer peso → overloaded (thresholds zerados)", () => {
    const result = computeEncumbranceTier({ strengthScore: 0, totalWeightKg: 100 });
    expect(result.tier).toBe("overloaded");
    expect(result.normalMaxKg).toBe(0);
    expect(result.encumberedMaxKg).toBe(0);
    expect(result.heavilyEncumberedMaxKg).toBe(0);
  });

  it("STR 0, 0 kg → normal (sem carga)", () => {
    const result = computeEncumbranceTier({ strengthScore: 0, totalWeightKg: 0 });
    expect(result.tier).toBe("normal");
  });

  it("multiplicadores de carrying capacity não afetam thresholds", () => {
    const normalMaxLb = 10 * 5;
    const thresholdKg = normalMaxLb * LB_TO_KG;
    const justBelow = computeEncumbranceTier({ strengthScore: 10, totalWeightKg: thresholdKg });
    expect(justBelow.tier).toBe("normal");
    const justAbove = computeEncumbranceTier({ strengthScore: 10, totalWeightKg: thresholdKg + 0.01 });
    expect(justAbove.tier).toBe("encumbered");
  });
});

describe("applyEncumbranceMovementPenalty", () => {
  it("normal → sem alteração", () => {
    expect(applyEncumbranceMovementPenalty(9, "normal")).toBe(9);
  });

  it("encumbered → -3", () => {
    expect(applyEncumbranceMovementPenalty(9, "encumbered")).toBe(6);
  });

  it("heavily_encumbered → -6", () => {
    expect(applyEncumbranceMovementPenalty(9, "heavily_encumbered")).toBe(3);
  });

  it("overloaded → 0", () => {
    expect(applyEncumbranceMovementPenalty(9, "overloaded")).toBe(0);
  });

  it("nunca negativo", () => {
    expect(applyEncumbranceMovementPenalty(2, "heavily_encumbered")).toBe(0);
    expect(applyEncumbranceMovementPenalty(1, "encumbered")).toBe(0);
  });

  it("speed 0 → 0 em qualquer tier", () => {
    expect(applyEncumbranceMovementPenalty(0, "normal")).toBe(0);
    expect(applyEncumbranceMovementPenalty(0, "encumbered")).toBe(0);
    expect(applyEncumbranceMovementPenalty(0, "heavily_encumbered")).toBe(0);
    expect(applyEncumbranceMovementPenalty(0, "overloaded")).toBe(0);
  });

  it("anões (8m) encumbered → 5m", () => {
    expect(applyEncumbranceMovementPenalty(8, "encumbered")).toBe(5);
  });

  it("wood elf (11m) heavily_encumbered → 5m", () => {
    expect(applyEncumbranceMovementPenalty(11, "heavily_encumbered")).toBe(5);
  });
});

describe("declarativeEffectGroupKey", () => {
  const makeEffect = (id = "eff-1"): ActiveEffect => ({
    id,
    kind: "spell_effect",
    duration_type: "manual",
    created_at: "2026-05-01T00:00:00Z",
  });

  it("prioriza declarative_effect_group_id", () => {
    const metadata = { declarative_effect_group_id: "group-abc" };
    const key = declarativeEffectGroupKey(metadata, makeEffect(), "passive_skill_bonus", "perception|5", 0);
    expect(key).toBe("group-abc");
  });

  it("gera composite key a partir de source_spell_key", () => {
    const metadata = { source_spell_key: "owls_wisdom", selected_variant_key: "owls_wisdom" };
    const key = declarativeEffectGroupKey(metadata, makeEffect(), "passive_skill_bonus", "perception|5", 0);
    expect(key).toBe("owls_wisdom|owls_wisdom|passive_skill_bonus|perception|5");
  });

  it("gera composite key a partir de source_spell_name como fallback", () => {
    const metadata = { source_spell_name: "Owl's Wisdom" };
    const key = declarativeEffectGroupKey(metadata, makeEffect(), "passive_skill_bonus", "perception|5", 0);
    expect(key).toBe("Owl's Wisdom||passive_skill_bonus|perception|5");
  });

  it("inclui effectType e paramsKey na composite key", () => {
    const metadata = { source_spell_key: "enhance_ability", selected_variant_key: "bulls_strength" };
    const key = declarativeEffectGroupKey(metadata, makeEffect(), "carrying_capacity_multiplier", "2", 0);
    expect(key).toBe("enhance_ability|bulls_strength|carrying_capacity_multiplier|2");
  });

  it("cai para effect.id quando não há metadata", () => {
    const key = declarativeEffectGroupKey({}, makeEffect("my-id"), "advantage_on_checks", "wisdom", 0);
    expect(key).toBe("my-id");
  });

  it("cai para __unknown_{fallbackIndex} quando não há effect.id", () => {
    const effect = { ...makeEffect(), id: undefined as unknown as string };
    const key = declarativeEffectGroupKey({}, effect, "advantage_on_checks", "wisdom", 42);
    expect(key).toBe("__unknown_42");
  });

  it("group_id vazio é tratado como ausente", () => {
    const metadata = { declarative_effect_group_id: "" };
    const key = declarativeEffectGroupKey(metadata, makeEffect(), "passive_skill_bonus", "perception|5", 0);
    expect(key).not.toBe("");
  });

  it("paramsKeys diferentes produzem grupos diferentes", () => {
    const metadata = { source_spell_key: "owls_wisdom" };
    const key1 = declarativeEffectGroupKey(metadata, makeEffect(), "passive_skill_bonus", "perception|5", 0);
    const key2 = declarativeEffectGroupKey(metadata, makeEffect(), "passive_skill_bonus", "perception|3", 0);
    expect(key1).not.toBe(key2);
  });

  it("não usa Math.random()", () => {
    const effect = { ...makeEffect(), id: undefined as unknown as string };
    const key1 = declarativeEffectGroupKey({}, effect, "test", "", 7);
    const key2 = declarativeEffectGroupKey({}, effect, "test", "", 7);
    expect(key1).toBe(key2);
    expect(key1).toBe("__unknown_7");
  });
});

const makeInventoryItem = (overrides: Partial<{
  id: string;
  name: string;
  quantity: number;
  weight: number;
  notes: string;
  canonicalKey: string | null;
}> = {}) => ({
  id: "1",
  name: "item",
  quantity: 1,
  weight: 1,
  notes: "",
  canonicalKey: null,
  ...overrides,
});

describe("computeTotalWeight — edge cases", () => {
  it("item com weight null → tratado como 0", () => {
    const items = [makeInventoryItem({ weight: null as unknown as number, quantity: 1 })];
    expect(computeTotalWeight(items)).toBe(0);
  });

  it("item com quantity 0 → 0", () => {
    const items = [makeInventoryItem({ weight: 5, quantity: 0 })];
    expect(computeTotalWeight(items)).toBe(0);
  });

  it("item com quantity negativa → tratado como 0", () => {
    const items = [makeInventoryItem({ weight: 5, quantity: -10 })];
    expect(computeTotalWeight(items)).toBe(0);
  });

  it("item com weight null E quantity negativa → 0 (não NaN)", () => {
    const items = [makeInventoryItem({ weight: null as unknown as number, quantity: -10 })];
    const result = computeTotalWeight(items);
    expect(result).toBe(0);
    expect(Number.isNaN(result)).toBe(false);
  });

  it("weight NaN → tratado como 0", () => {
    const items = [makeInventoryItem({ weight: NaN, quantity: 3 })];
    expect(computeTotalWeight(items)).toBe(0);
  });

  it("itens válidos + item inválido → soma ignora inválido", () => {
    const items = [
      makeInventoryItem({ weight: 10, quantity: 2 }),
      makeInventoryItem({ weight: null as unknown as number, quantity: 5 }),
      makeInventoryItem({ weight: 3, quantity: -1 }),
    ];
    expect(computeTotalWeight(items)).toBe(20);
  });
});

describe("computeEncumbranceTier — hardening", () => {
  it("strengthScore NaN → thresholds 0, tier normal (0 kg)", () => {
    const r = computeEncumbranceTier({ strengthScore: NaN, totalWeightKg: 0 });
    expect(r.tier).toBe("normal");
    expect(r.normalMaxKg).toBe(0);
    expect(Number.isNaN(r.remainingKg)).toBe(false);
  });

  it("strengthScore NaN + peso → overloaded", () => {
    const r = computeEncumbranceTier({ strengthScore: NaN, totalWeightKg: 10 });
    expect(r.tier).toBe("overloaded");
    expect(r.remainingKg).toBe(0);
    expect(r.nextThresholdKg).toBeNull();
  });

  it("totalWeightKg NaN → normal, remainingKg = normalMaxKg", () => {
    const r = computeEncumbranceTier({ strengthScore: 10, totalWeightKg: NaN });
    expect(r.tier).toBe("normal");
    expect(r.remainingKg).toBe(Math.round(10 * 5 * LB_TO_KG * 10) / 10);
    expect(Number.isNaN(r.remainingKg)).toBe(false);
  });

  it("strengthScore negativa → treated as 0 → overloaded com peso", () => {
    const r = computeEncumbranceTier({ strengthScore: -5, totalWeightKg: 10 });
    expect(r.tier).toBe("overloaded");
    expect(r.normalMaxKg).toBe(0);
  });

  it("strengthScore negativa, 0 kg → normal", () => {
    const r = computeEncumbranceTier({ strengthScore: -5, totalWeightKg: 0 });
    expect(r.tier).toBe("normal");
    expect(r.normalMaxKg).toBe(0);
  });

  it("strengthScore 0, weight 0 → normal, remaining 0, threshold 0", () => {
    const r = computeEncumbranceTier({ strengthScore: 0, totalWeightKg: 0 });
    expect(r.tier).toBe("normal");
    expect(r.remainingKg).toBe(0);
    expect(r.nextThresholdKg).toBe(0);
  });

  it("ambos NaN → normal, todos os campos 0", () => {
    const r = computeEncumbranceTier({ strengthScore: NaN, totalWeightKg: NaN });
    expect(r.tier).toBe("normal");
    expect(r.normalMaxKg).toBe(0);
    expect(r.remainingKg).toBe(0);
    expect(Number.isNaN(r.remainingKg)).toBe(false);
  });

  it("strengthScore undefined → treated as 0", () => {
    const r = computeEncumbranceTier({ strengthScore: undefined as unknown as number, totalWeightKg: 5 });
    expect(r.tier).toBe("overloaded");
    expect(r.normalMaxKg).toBe(0);
  });

  it("totalWeightKg negativo → treated as 0 → normal", () => {
    const r = computeEncumbranceTier({ strengthScore: 10, totalWeightKg: -5 });
    expect(r.tier).toBe("normal");
    expect(r.remainingKg).toBe(Math.round(10 * 5 * LB_TO_KG * 10) / 10);
  });
});

describe("computeProjectedEncumbranceTier — hardening", () => {
  it("addedWeightLb null → não quebra, retorna resultado válido", () => {
    const r = computeProjectedEncumbranceTier({ strengthScore: 10, currentWeightKg: 5, addedWeightLb: null as unknown as number });
    expect(r.tier).toBe("normal");
    expect(Number.isNaN(r.remainingKg)).toBe(false);
  });

  it("addedWeightLb NaN → tratado como 0", () => {
    const r = computeProjectedEncumbranceTier({ strengthScore: 10, currentWeightKg: 5, addedWeightLb: NaN });
    expect(r.tier).toBe("normal");
  });

  it("addedWeightLb undefined → tratado como 0", () => {
    const r = computeProjectedEncumbranceTier({ strengthScore: 10, currentWeightKg: 5, addedWeightLb: undefined as unknown as number });
    expect(r.tier).toBe("normal");
  });

  it("currentWeightKg NaN → normal (safeWeight 0)", () => {
    const r = computeProjectedEncumbranceTier({ strengthScore: 10, currentWeightKg: NaN, addedWeightLb: 0 });
    expect(r.tier).toBe("normal");
    expect(Number.isNaN(r.remainingKg)).toBe(false);
  });
});
