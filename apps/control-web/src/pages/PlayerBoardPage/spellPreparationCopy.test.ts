import { describe, expect, it } from "vitest";
import { getSpellPreparationCopyKeys, resolveSpellPreparationCopyMode } from "./spellPreparationCopy";

describe("spellPreparationCopy", () => {
  it("uses during-long-rest copy only when the pending spell prep is available during rest", () => {
    expect(
      resolveSpellPreparationCopyMode(
        {
          source: "long_rest",
          classKey: "cleric",
          preparedLimit: 8,
          currentPreparedSpellIds: [],
          createdAt: "2026-01-01T00:00:00+00:00",
          availableDuringRest: true,
        },
        "long_rest",
      ),
    ).toBe("during_long_rest");

    expect(
      resolveSpellPreparationCopyMode(
        {
          source: "long_rest",
          classKey: "cleric",
          preparedLimit: 8,
          currentPreparedSpellIds: [],
          createdAt: "2026-01-01T00:00:00+00:00",
          availableDuringRest: true,
        },
        "exploration",
      ),
    ).toBe("fallback");
  });

  it("falls back when the pending spell prep was created after the rest", () => {
    expect(
      resolveSpellPreparationCopyMode(
        {
          source: "long_rest",
          classKey: "cleric",
          preparedLimit: 8,
          currentPreparedSpellIds: [],
          createdAt: "2026-01-01T00:00:00+00:00",
          availableDuringRest: false,
        },
        "long_rest",
      ),
    ).toBe("fallback");
  });

  it("maps copy keys for both modes", () => {
    expect(getSpellPreparationCopyKeys("during_long_rest")).toEqual({
      title: "playerBoard.prepareSpellsDuringLongRestPrompt",
      description: "playerBoard.prepareSpellsDuringLongRestDescription",
    });
    expect(getSpellPreparationCopyKeys("fallback")).toEqual({
      title: "playerBoard.prepareSpellsPrompt",
      description: "playerBoard.prepareSpellsDescription",
    });
  });
});
