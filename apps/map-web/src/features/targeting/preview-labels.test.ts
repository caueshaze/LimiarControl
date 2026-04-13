import { describe, expect, it } from "vitest";
import {
  CANONICAL_FAILURE_REASONS,
  getFailureLabel,
  getPrimaryFailureLabel,
} from "./preview-labels";

describe("getFailureLabel", () => {
  it("maps every canonical failure reason to a non-empty PT-BR string", () => {
    for (const reason of CANONICAL_FAILURE_REASONS) {
      const label = getFailureLabel(reason);
      expect(label.length).toBeGreaterThan(0);
      // Must not fall back to the raw code (all known codes must have labels)
      expect(label).not.toBe(reason);
    }
  });

  it("returns the raw code for unknown reasons (safe fallback)", () => {
    expect(getFailureLabel("some_future_reason")).toBe("some_future_reason");
  });

  it("maps target_out_of_reach", () => {
    expect(getFailureLabel("target_out_of_reach")).toBe("Fora do alcance");
  });

  it("maps no_line_of_sight", () => {
    expect(getFailureLabel("no_line_of_sight")).toBe("Sem linha de visão");
  });

  it("maps no_line_of_effect", () => {
    expect(getFailureLabel("no_line_of_effect")).toBe("Bloqueado");
  });

  it("maps not_visible", () => {
    expect(getFailureLabel("not_visible")).toBe("Não visível");
  });

  it("maps target_not_found", () => {
    expect(getFailureLabel("target_not_found")).toBe("Alvo não encontrado");
  });
});

describe("getPrimaryFailureLabel", () => {
  it("returns null for an empty reasons list (valid target)", () => {
    expect(getPrimaryFailureLabel([])).toBeNull();
  });

  it("returns the label of the first reason", () => {
    expect(
      getPrimaryFailureLabel(["target_out_of_reach", "no_line_of_sight"])
    ).toBe("Fora do alcance");
  });

  it("returns the label for a single reason", () => {
    expect(getPrimaryFailureLabel(["not_visible"])).toBe("Não visível");
  });

  it("falls back gracefully for an unknown first reason", () => {
    expect(getPrimaryFailureLabel(["unknown_reason"])).toBe("unknown_reason");
  });
});

describe("CANONICAL_FAILURE_REASONS", () => {
  it("contains at least the core tactical reasons", () => {
    const expected = [
      "target_not_found",
      "target_out_of_reach",
      "no_line_of_sight",
      "no_line_of_effect",
      "not_visible",
    ];
    for (const r of expected) {
      expect(CANONICAL_FAILURE_REASONS).toContain(r);
    }
  });

  it("is frozen (no accidental mutation)", () => {
    expect(Object.isFrozen(CANONICAL_FAILURE_REASONS)).toBe(true);
  });
});
