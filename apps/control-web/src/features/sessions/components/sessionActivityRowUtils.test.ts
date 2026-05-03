import { describe, expect, it } from "vitest";
import type { RollResolvedActivityEvent } from "../../../shared/api/sessionsRepo";
import {
  formatCheckModifierSource,
  formatResolvedRollBreakdown,
  formatRollResolvedToastDescription,
} from "./sessionActivityRowUtils";

const baseEvent: RollResolvedActivityEvent = {
  type: "roll_resolved",
  actorKind: "player",
  actorName: "Player",
  advantageMode: "normal",
  displayName: "Player",
  isGmRoll: false,
  modifierUsed: 3,
  rollType: "save",
  rolls: [8, 8],
  selectedRoll: 8,
  sessionOffsetSeconds: 10,
  timestamp: "2026-03-30T22:00:00Z",
  total: 11,
  userId: "player-1",
};

describe("sessionActivityRowUtils", () => {
  it("shows a single d20 value for normal resolved rolls", () => {
    expect(
      formatResolvedRollBreakdown(baseEvent, "d20:"),
    ).toBe("d20: 8 + 3");
  });

  it("shows both d20 values for advantage or disadvantage", () => {
    expect(
      formatResolvedRollBreakdown(
        {
          ...baseEvent,
          advantageMode: "advantage",
          rolls: [8, 14],
          selectedRoll: 14,
        },
        "d20:",
      ),
    ).toBe("d20: [8, 14] → 14 + 3");
  });

  it("formats contextual advantage sources", () => {
    expect(
      formatCheckModifierSource({
        source_label: "Sabedoria da Coruja",
        modifier_type: "advantage",
        roll_type: "skill",
        skill: "perception",
        ability: "wisdom",
        against: "any",
        applied: true,
        skip_reason: null,
      }),
    ).toBe("Vantagem por Sabedoria da Coruja em perception");
  });

  it("formats contextual disadvantage sources", () => {
    expect(
      formatCheckModifierSource({
        source_label: "Carga",
        modifier_type: "disadvantage",
        roll_type: "ability",
        ability: "strength",
        against: "any",
        applied: true,
        skip_reason: null,
      }),
    ).toBe("Desvantagem por Carga em strength");
  });

  it("includes contextual advantage sources in roll resolved toast text", () => {
    expect(
      formatRollResolvedToastDescription({
        ...baseEvent,
        formula: "1d20 + 0",
        total: 14,
        success: true,
        check_modifier_sources: [
          {
            source_label: "Sabedoria da Coruja",
            modifier_type: "advantage",
            roll_type: "ability",
            ability: "wisdom",
            against: "any",
            applied: true,
            skip_reason: null,
          },
        ],
      }),
    ).toBe("1d20 + 0 = 14 ✓ · Vantagem por Sabedoria da Coruja em wisdom");
  });
});
