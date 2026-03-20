import { describe, expect, it } from "vitest";
import {
  getItemPropertyLabels,
  normalizeItemProperties,
  parseItemPropertiesInput,
} from "./itemProperties";

describe("itemProperties", () => {
  it("normalizes PT and EN aliases into canonical slugs", () => {
    expect(parseItemPropertiesInput("Leve, versatile, Arremesso")).toEqual({
      ok: true,
      value: ["light", "versatile", "thrown"],
      invalid: [],
    });
  });

  it("deduplicates normalized values", () => {
    expect(normalizeItemProperties(["leve", "light", "Leve"])).toEqual({
      ok: true,
      value: ["light"],
      invalid: [],
    });
  });

  it("keeps invalid tokens out of the saved payload", () => {
    expect(parseItemPropertiesInput("Light, desconhecida, Versatil")).toEqual({
      ok: false,
      value: ["light", "versatile"],
      invalid: ["desconhecida"],
    });
  });

  it("returns localized labels for canonical values", () => {
    expect(getItemPropertyLabels(["light", "two_handed"], "pt")).toEqual([
      "Leve",
      "Duas maos",
    ]);
  });
});
