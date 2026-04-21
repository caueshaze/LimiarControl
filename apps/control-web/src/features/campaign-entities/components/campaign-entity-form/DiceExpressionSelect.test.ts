import { describe, expect, it } from "vitest";

import { buildDiceExpression, parseDiceExpression } from "./DiceExpressionSelect";

describe("DiceExpressionSelect helpers", () => {
  it("keeps incomplete dice selections out of the submitted expression", () => {
    expect(buildDiceExpression({ count: "1", sides: "" })).toBe("");
    expect(buildDiceExpression({ count: "", sides: "6" })).toBe("");
  });

  it("builds a valid dice expression once both controls are selected", () => {
    expect(buildDiceExpression({ count: "2", sides: "8" })).toBe("2d8");
  });

  it("parses existing dice expressions back into select values", () => {
    expect(parseDiceExpression("3d10")).toEqual({ count: "3", sides: "10" });
    expect(parseDiceExpression("d6")).toEqual({ count: "1", sides: "6" });
  });
});
