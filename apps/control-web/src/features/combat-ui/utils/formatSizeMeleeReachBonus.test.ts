import { describe, expect, it } from "vitest";
import {
  formatMetersCompact,
  formatSizeMeleeReachBonusSource,
  getSizeMeleeReachBonusMeters,
} from "./formatSizeMeleeReachBonus";

const mockT = (key: string) => {
  const map: Record<string, string> = {
    "playerBoard.creatureSize.Tiny": "Diminuto",
    "playerBoard.creatureSize.Small": "Pequeno",
    "playerBoard.creatureSize.Medium": "Médio",
    "playerBoard.creatureSize.Large": "Grande",
    "playerBoard.creatureSize.Huge": "Enorme",
    "playerBoard.creatureSize.Gargantuan": "Colossal",
    "combatUi.meleeReachSizePrefix": "Tamanho",
  };
  return map[key] ?? key;
};

describe("getSizeMeleeReachBonusMeters", () => {
  it("Tiny → 0", () => {
    expect(getSizeMeleeReachBonusMeters("Tiny")).toBe(0);
  });
  it("Medium → 0", () => {
    expect(getSizeMeleeReachBonusMeters("Medium")).toBe(0);
  });
  it("Large → 1.5", () => {
    expect(getSizeMeleeReachBonusMeters("Large")).toBe(1.5);
  });
  it("Huge → 3", () => {
    expect(getSizeMeleeReachBonusMeters("Huge")).toBe(3);
  });
  it("Gargantuan → 4.5", () => {
    expect(getSizeMeleeReachBonusMeters("Gargantuan")).toBe(4.5);
  });
});

describe("formatMetersCompact", () => {
  it("1.5 → 1,5m", () => {
    expect(formatMetersCompact(1.5)).toBe("1,5m");
  });
  it("3 → 3m", () => {
    expect(formatMetersCompact(3)).toBe("3m");
  });
  it("3.0 → 3m (sem decimal)", () => {
    expect(formatMetersCompact(3.0)).toBe("3m");
  });
  it("4.5 → 4,5m", () => {
    expect(formatMetersCompact(4.5)).toBe("4,5m");
  });
  it("evita artefato de ponto flutuante", () => {
    expect(formatMetersCompact(1.5000000000000002)).toBe("1,5m");
  });
});

describe("formatSizeMeleeReachBonusSource", () => {
  it("Medium → null", () => {
    expect(formatSizeMeleeReachBonusSource("Medium", mockT)).toBeNull();
  });
  it("Small → null", () => {
    expect(formatSizeMeleeReachBonusSource("Small", mockT)).toBeNull();
  });
  it("Tiny → null", () => {
    expect(formatSizeMeleeReachBonusSource("Tiny", mockT)).toBeNull();
  });
  it("Large → Tamanho Grande +1,5m", () => {
    const result = formatSizeMeleeReachBonusSource("Large", mockT);
    expect(result).toEqual({ label: "Tamanho Grande +1,5m", bonusMeters: 1.5 });
  });
  it("Huge → Tamanho Enorme +3m", () => {
    const result = formatSizeMeleeReachBonusSource("Huge", mockT);
    expect(result).toEqual({ label: "Tamanho Enorme +3m", bonusMeters: 3 });
  });
  it("Gargantuan → Tamanho Colossal +4,5m", () => {
    const result = formatSizeMeleeReachBonusSource("Gargantuan", mockT);
    expect(result).toEqual({ label: "Tamanho Colossal +4,5m", bonusMeters: 4.5 });
  });
  it("undefined → null", () => {
    expect(formatSizeMeleeReachBonusSource(undefined, mockT)).toBeNull();
  });
});
