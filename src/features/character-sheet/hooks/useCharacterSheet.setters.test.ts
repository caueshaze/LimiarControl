import { describe, expect, it } from "vitest";
import { INITIAL_SHEET } from "../model/initialSheet";
import { buildCreationSetAbility } from "./useCharacterSheet.setters";

describe("buildCreationSetAbility", () => {
  it("keeps regular creation locked to the standard array", () => {
    const setAbility = buildCreationSetAbility("creation", null);
    const next = setAbility(INITIAL_SHEET, "strength", 16);

    expect(next.abilities.strength).toBe(INITIAL_SHEET.abilities.strength);
  });

  it("allows freeform base ability editing in GM creation drafts", () => {
    const setAbility = buildCreationSetAbility("creation", null, {
      allowCreationEditing: true,
    });
    const next = setAbility(
      {
        ...INITIAL_SHEET,
        class: "guardian",
        race: "human",
      },
      "strength",
      16,
    );

    expect(next.abilities.strength).toBe(17);
  });
});
