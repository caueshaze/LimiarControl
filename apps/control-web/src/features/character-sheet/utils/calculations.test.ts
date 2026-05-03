import { describe, expect, it } from "vitest";
import { computeAbilityScoreTotal, computePassiveSkillBonus, computePassiveSkillBonusSources } from "./calculations";
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
