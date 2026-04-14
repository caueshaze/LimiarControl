import { describe, expect, it } from "vitest";
import { getDistanceBetween } from "./GmDistancesPanel";

describe("getDistanceBetween", () => {
  it("returns the distance when stored in forward direction", () => {
    const distances = { "ref-a": { "ref-b": 9 } };
    expect(getDistanceBetween(distances, "ref-a", "ref-b")).toBe(9);
  });

  it("returns the distance when stored in reverse direction", () => {
    const distances = { "ref-b": { "ref-a": 3 } };
    expect(getDistanceBetween(distances, "ref-a", "ref-b")).toBe(3);
  });

  it("returns null when the pair has no configured distance", () => {
    const distances = { "ref-a": { "ref-c": 5 } };
    expect(getDistanceBetween(distances, "ref-a", "ref-b")).toBeNull();
  });

  it("returns null when localDistances is empty", () => {
    expect(getDistanceBetween({}, "ref-a", "ref-b")).toBeNull();
  });

  it("returns 0 when distance is explicitly 0", () => {
    const distances = { "ref-a": { "ref-b": 0 } };
    expect(getDistanceBetween(distances, "ref-a", "ref-b")).toBe(0);
  });
});
