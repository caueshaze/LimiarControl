import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { INITIAL_SHEET } from "../../features/character-sheet/model/initialSheet";
import { usePlayerBoardSummary } from "./usePlayerBoardSummary";
import type { ActiveEffect } from "../../shared/api/combatRepo";
import type { PlayerBoardStatusSummary } from "./playerBoard.types";

vi.mock("../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    locale: "pt-BR",
    t: (key: string) => key,
  }),
}));

const makePassivePerceptionEffect = (
  bonus: number,
  label = "Owl's Wisdom",
): ActiveEffect => ({
  id: `effect-${label}-${bonus}`,
  kind: "spell_effect",
  duration_type: "rounds",
  created_at: "2026-05-02T00:00:00Z",
  display_label: label,
  metadata: {
    declarative_effect: {
      type: "passive_skill_bonus",
      params: {
        skill: "perception",
        bonus,
      },
    },
  },
});

const renderSummary = (activeEffects: ActiveEffect[] = []): PlayerBoardStatusSummary | null => {
  let captured: PlayerBoardStatusSummary | null = null;

  const Probe = () => {
    const summary = usePlayerBoardSummary({
      activeSession: { status: "ACTIVE" },
      activeEffects,
      effectiveCampaignId: "campaign-1",
      inventory: [],
      itemsById: {},
      playerSheet: INITIAL_SHEET,
      selectedCampaignName: "Campanha",
      t: (key) => key,
    });

    captured = summary.playerStatus;
    return null;
  };

  renderToStaticMarkup(<Probe />);
  return captured;
};

describe("usePlayerBoardSummary", () => {
  it("aplica bônus passivo de percepção ao resumo do player board", () => {
    const playerStatus = renderSummary([makePassivePerceptionEffect(5)]);

    expect(playerStatus?.passivePerception).toBe(15);
    expect(playerStatus?.passivePerceptionBonus).toBe(5);
    expect(playerStatus?.passivePerceptionBonusSources).toEqual([
      { label: "Owl's Wisdom", value: 5 },
    ]);
  });

  it("mantém percepção passiva base quando activeEffects está ausente", () => {
    const playerStatus = renderSummary();

    expect(playerStatus?.passivePerception).toBe(10);
    expect(playerStatus?.passivePerceptionBonus).toBe(0);
    expect(playerStatus?.passivePerceptionBonusSources).toEqual([]);
  });
});
