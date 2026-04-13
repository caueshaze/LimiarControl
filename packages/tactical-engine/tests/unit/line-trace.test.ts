import { describe, expect, it } from "vitest";
import { traceLine } from "../../src";

describe("line trace", () => {
  it("returns intermediate cells for straight lines", () => {
    expect(traceLine({ x: 0, y: 0 }, { x: 3, y: 0 })).toEqual([
      { x: 1, y: 0 },
      { x: 2, y: 0 }
    ]);
  });

  it("uses diagonal corner steps when the ray crosses exact corners", () => {
    expect(traceLine({ x: 0, y: 0 }, { x: 3, y: 3 })).toEqual([
      { x: 1, y: 1 },
      { x: 2, y: 2 }
    ]);
  });

  it("uses supercover cells for shallow diagonals", () => {
    expect(traceLine({ x: 0, y: 0 }, { x: 3, y: 1 })).toEqual([
      { x: 1, y: 0 },
      { x: 2, y: 1 }
    ]);
  });

  it("returns no cells when origin and target are the same", () => {
    expect(traceLine({ x: 4, y: 4 }, { x: 4, y: 4 })).toEqual([]);
  });
});
