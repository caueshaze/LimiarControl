import { describe, expect, it } from "vitest";
import { parseCreatureSize } from "./parseCreatureSize";

describe("parseCreatureSize", () => {
  it("parses lowercase 'large' → Large", () => {
    expect(parseCreatureSize("large")).toBe("Large");
  });
  it("parses uppercase 'LARGE' → Large", () => {
    expect(parseCreatureSize("LARGE")).toBe("Large");
  });
  it("parses exact 'Large' → Large", () => {
    expect(parseCreatureSize("Large")).toBe("Large");
  });
  it("parses 'medium' → Medium", () => {
    expect(parseCreatureSize("medium")).toBe("Medium");
  });
  it("returns undefined for invalid string", () => {
    expect(parseCreatureSize("colossal")).toBeUndefined();
  });
  it("returns undefined for empty string", () => {
    expect(parseCreatureSize("")).toBeUndefined();
  });
  it("returns undefined for null/undefined", () => {
    expect(parseCreatureSize(null)).toBeUndefined();
    expect(parseCreatureSize(undefined)).toBeUndefined();
  });
});
