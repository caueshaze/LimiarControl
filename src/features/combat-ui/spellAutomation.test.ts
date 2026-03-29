import { describe, expect, it } from "vitest";

import {
  getCombatSpellAutomation,
  isCombatSpellActionCostAvailable,
  resolveCombatSpellActionCost,
  spellModeNeedsDamageType,
  spellModeNeedsEffectInputs,
  spellModeNeedsSaveAbility,
} from "./spellAutomation";

describe("combat spell automation metadata", () => {
  it("marks utility guardian spells correctly", () => {
    expect(getCombatSpellAutomation("hunters_mark")).toEqual({
      defaultMode: "utility",
      requiresEffectInputs: false,
    });
    expect(getCombatSpellAutomation("goodberry")).toEqual({
      defaultMode: "utility",
      requiresEffectInputs: false,
    });
    expect(getCombatSpellAutomation("magic_missile")).toEqual({
      defaultMode: "direct_damage",
      requiresEffectInputs: false,
    });
    expect(getCombatSpellAutomation("animal_friendship")).toEqual({
      defaultMode: "saving_throw",
      requiresEffectInputs: false,
    });
  });

  it("derives input requirements from spell mode", () => {
    expect(spellModeNeedsEffectInputs("utility")).toBe(false);
    expect(spellModeNeedsDamageType("utility")).toBe(false);
    expect(spellModeNeedsSaveAbility("utility")).toBe(false);
    expect(spellModeNeedsSaveAbility("saving_throw")).toBe(true);
  });

  it("maps combat spell action costs from casting time", () => {
    expect(resolveCombatSpellActionCost("action")).toBe("action");
    expect(resolveCombatSpellActionCost("bonus_action")).toBe("bonus_action");
    expect(resolveCombatSpellActionCost("reaction")).toBe("reaction");
    expect(resolveCombatSpellActionCost(null)).toBe("action");
    expect(resolveCombatSpellActionCost("10 minutes")).toBeNull();
  });

  it("checks turn resource availability for the spell action cost", () => {
    expect(
      isCombatSpellActionCostAvailable("bonus_action", {
        action_used: false,
        bonus_action_used: true,
        reaction_used: false,
      }),
    ).toBe(false);
    expect(
      isCombatSpellActionCostAvailable("action", {
        action_used: false,
        bonus_action_used: true,
        reaction_used: true,
      }),
    ).toBe(true);
    expect(
      isCombatSpellActionCostAvailable("reaction", {
        action_used: true,
        bonus_action_used: true,
        reaction_used: true,
      }),
    ).toBe(false);
  });
});
