import { describe, expect, it } from "vitest";

import {
  getCombatSpellAutomation,
  isCombatSpellActionCostAvailable,
  resolveCombatSpellActionCost,
  spellModeNeedsDamageType,
  spellModeNeedsEffectInputs,
  spellModeNeedsSaveAbility
} from "./spellAutomation";

describe("combat spell automation metadata", () => {
  it("marks special-handler spells correctly", () => {
    expect(getCombatSpellAutomation("hunters_mark")).toEqual({
      automationMode: "special_handler",
      defaultSpellMode: "utility",
      requiresEffectInputs: false,
      requiresMap: false,
      handlerKey: "_cast_hunters_mark_automation"
    });
    expect(getCombatSpellAutomation("goodberry")).toEqual({
      automationMode: "special_handler",
      defaultSpellMode: "utility",
      requiresEffectInputs: false,
      requiresMap: false,
      handlerKey: "_cast_goodberry_automation"
    });
    expect(getCombatSpellAutomation("animal_friendship")).toEqual({
      automationMode: "special_handler",
      defaultSpellMode: "saving_throw",
      requiresEffectInputs: false,
      requiresMap: false,
      handlerKey: "_cast_animal_friendship_automation"
    });
  });

  it("magic_missile is no longer in the frontend registry", () => {
    expect(getCombatSpellAutomation("magic_missile")).toBeNull();
  });

  it("unknown spells return null", () => {
    expect(getCombatSpellAutomation("nonexistent_spell")).toBeNull();
    expect(getCombatSpellAutomation(null)).toBeNull();
    expect(getCombatSpellAutomation(undefined)).toBeNull();
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
        reaction_used: false
      })
    ).toBe(false);
    expect(
      isCombatSpellActionCostAvailable("action", {
        action_used: false,
        bonus_action_used: true,
        reaction_used: true
      })
    ).toBe(true);
    expect(
      isCombatSpellActionCostAvailable("reaction", {
        action_used: true,
        bonus_action_used: true,
        reaction_used: true
      })
    ).toBe(false);
  });
});
