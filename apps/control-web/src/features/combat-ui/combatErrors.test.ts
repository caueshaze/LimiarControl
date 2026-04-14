import { describe, expect, it } from "vitest";
import { isMissingDistanceError, toPlayerFriendlyError } from "./combatErrors";

describe("isMissingDistanceError", () => {
  it("detects the exact backend phrase", () => {
    expect(
      isMissingDistanceError(
        "Target distance not configured for non-map combat. GM must set combat distances first.",
      ),
    ).toBe(true);
  });

  it("is case-insensitive", () => {
    expect(isMissingDistanceError("DISTANCE NOT CONFIGURED")).toBe(true);
  });

  it("returns false for unrelated errors", () => {
    expect(isMissingDistanceError("Resource limit exceeded")).toBe(false);
    expect(isMissingDistanceError("Target is out of range")).toBe(false);
    expect(isMissingDistanceError("")).toBe(false);
  });
});

describe("toPlayerFriendlyError", () => {
  it("returns a human-readable message for missing-distance errors", () => {
    const result = toPlayerFriendlyError(
      "Target distance not configured for non-map combat. GM must set combat distances first.",
    );
    expect(result).toBe(
      "Distância não configurada — aguarde o GM definir as distâncias antes de agir.",
    );
  });

  it("passes through unrelated error messages unchanged", () => {
    const msg = "Resource limit exceeded for this action.";
    expect(toPlayerFriendlyError(msg)).toBe(msg);
  });

  it("passes through empty string unchanged", () => {
    expect(toPlayerFriendlyError("")).toBe("");
  });
});
