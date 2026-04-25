import { describe, expect, it, vi } from "vitest";
import { battleMapStore } from "../features/battle-map/battle-map-store";
import { applyEmbeddedMapContext, isEmbeddedMapContextMessage } from "./embedded-map-bridge";

vi.mock("./centrifugo-client", () => ({
  reconnectAs: vi.fn(),
}));

describe("embedded map area effects", () => {
  it("accepts active area effects in embedded map context messages", () => {
    const message = {
      type: "limiar-control:map-context",
      payload: {
        sessionId: "session-123",
        selectionMode: "none",
        previewCells: [],
        activeAreaEffects: [
          {
            id: "area_effect:1",
            sourceSpellName: "Fog Cloud",
            casterParticipantId: "p1",
            originPoint: { x: 10, y: 10 },
            anchorCell: { x: 10, y: 10 },
            areaShape: "sphere",
            sizeMeters: 6,
            affectedCells: [{ x: 10, y: 10 }],
            effectKind: "obscurement",
          },
        ],
      },
    };

    expect(isEmbeddedMapContextMessage(message)).toBe(true);
  });

  it("stores active area effects separately from preview cells", () => {
    battleMapStore.clearEmbeddedInteraction();

    applyEmbeddedMapContext({
      sessionId: "session-123",
      selectionMode: "select-cell",
      previewCells: [{ x: 1, y: 1 }],
      activeAreaEffects: [
        {
          id: "area_effect:1",
          sourceSpellCanonicalKey: "spike_growth",
          sourceSpellName: "Spike Growth",
          casterParticipantId: "p1",
          originPoint: { x: 10, y: 10 },
          anchorCell: { x: 10, y: 10 },
          areaShape: "sphere",
          sizeMeters: 6,
          radiusMeters: 6,
          affectedCells: [{ x: 10, y: 10 }],
          effectKind: "hazard",
          terrainEffect: "difficult_terrain",
        },
      ],
    });

    const state = battleMapStore.getState();
    expect(state.embeddedPreview).toEqual([{ x: 1, y: 1 }]);
    expect(state.embeddedActiveAreaEffects).toHaveLength(1);
    expect(state.embeddedActiveAreaEffects[0]?.sourceSpellName).toBe("Spike Growth");
  });
});
