import { describe, expect, it } from "vitest";
import {
  buildPendingSpellPreparationSignature,
  shouldAutoOpenPendingSpellPreparation,
} from "./spellPreparationAutoOpen";

describe("spellPreparationAutoOpen", () => {
  it("uses createdAt as the preferred pending signature", () => {
    expect(
      buildPendingSpellPreparationSignature({
        source: "long_rest",
        classKey: "cleric",
        preparedLimit: 8,
        currentPreparedSpellIds: ["s2", "s1"],
        createdAt: "2026-01-01T00:00:00+00:00",
        availableDuringRest: true,
      }),
    ).toBe("createdAt:2026-01-01T00:00:00+00:00");
  });

  it("sorts prepared spell ids when falling back to a derived signature", () => {
    const first = buildPendingSpellPreparationSignature({
      source: "long_rest",
      classKey: "cleric",
      preparedLimit: 8,
      currentPreparedSpellIds: ["s2", "s1"],
      createdAt: "",
      availableDuringRest: false,
    });
    const second = buildPendingSpellPreparationSignature({
      source: "long_rest",
      classKey: "cleric",
      preparedLimit: 8,
      currentPreparedSpellIds: ["s1", "s2"],
      createdAt: "",
      availableDuringRest: false,
    });

    expect(first).toBe(second);
  });

  it("does not auto-open without a signature", () => {
    expect(
      shouldAutoOpenPendingSpellPreparation({
        pendingSignature: null,
        combatActive: false,
        autoOpenedSignatures: new Set<string>(),
      }),
    ).toBe(false);
  });

  it("does not auto-open during combat", () => {
    expect(
      shouldAutoOpenPendingSpellPreparation({
        pendingSignature: "createdAt:2026-01-01T00:00:00+00:00",
        combatActive: true,
        autoOpenedSignatures: new Set<string>(),
      }),
    ).toBe(false);
  });

  it("does not auto-open an already opened signature", () => {
    expect(
      shouldAutoOpenPendingSpellPreparation({
        pendingSignature: "createdAt:2026-01-01T00:00:00+00:00",
        combatActive: false,
        autoOpenedSignatures: new Set([
          "createdAt:2026-01-01T00:00:00+00:00",
        ]),
      }),
    ).toBe(false);
  });

  it("auto-opens a fresh signature outside combat", () => {
    expect(
      shouldAutoOpenPendingSpellPreparation({
        pendingSignature: "createdAt:2026-01-01T00:00:00+00:00",
        combatActive: false,
        autoOpenedSignatures: new Set<string>(),
      }),
    ).toBe(true);
  });
});
