import { describe, expect, it } from "vitest";
import { formatPassiveBonusBreakdown } from "./passiveSkillBonusDisplay";

describe("formatPassiveBonusBreakdown", () => {
  it("returns empty string for empty sources", () => {
    expect(formatPassiveBonusBreakdown(12, [])).toBe("");
  });

  it("formats a single source", () => {
    const sources = [{ label: "Sabedoria da Coruja", value: 5, groupKey: "a" }];
    expect(formatPassiveBonusBreakdown(12, sources)).toBe(
      "Base 12 + Sabedoria da Coruja +5",
    );
  });

  it("formats multiple sources", () => {
    const sources = [
      { label: "Sabedoria da Coruja", value: 5, groupKey: "a" },
      { label: "Item X", value: 2, groupKey: "b" },
    ];
    expect(formatPassiveBonusBreakdown(12, sources)).toBe(
      "Base 12 + Sabedoria da Coruja +5 + Item X +2",
    );
  });

  it("handles negative bonus values", () => {
    const sources = [{ label: "Maldição", value: -3, groupKey: "c" }];
    expect(formatPassiveBonusBreakdown(15, sources)).toBe(
      "Base 15 + Maldição -3",
    );
  });
});
