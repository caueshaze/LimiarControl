import { describe, expect, it } from "vitest";
import type { CampaignMapConfig } from "../../../entities/campaign";
import {
  buildEdgeObstacleMap,
  buildObstacleMap,
  formatHoveredCell,
  getHoveredCellEdgePresets,
  getHoveredCellObstaclePreset,
  serializeEdgeObstacleMap,
  summarizeEdgeObstacleMap,
  serializeObstacleMap,
  summarizeObstacleMap,
} from "./utils";

describe("CampaignMapConfig utils", () => {
  it("prefers semantic obstacles over legacy blocked cells", () => {
    const config: CampaignMapConfig = {
      id: "map-1",
      createdAt: "2026-01-01T00:00:00.000Z",
      obstacles: [
        {
          x: 2,
          y: 3,
          blocksMovement: false,
          blocksEffect: true,
          blocksVision: false,
          cover: "none",
          clipsDiagonalMovement: false,
          movementCostMultiplier: 1,
        },
      ],
      blockedCells: [{ x: 9, y: 9 }],
    };

    const obstacleMap = buildObstacleMap(config);

    expect(obstacleMap.get("2:3")).toBe("spell_blocker");
    expect(obstacleMap.has("9:9")).toBe(false);
  });

  it("serializes obstacle maps using the canonical preset semantics", () => {
    const obstacleMap = new Map([
      ["1:2", "blocked_path"],
      ["4:5", "difficult_terrain"],
    ] as const);

    const obstacles = serializeObstacleMap(obstacleMap);

    expect(obstacles).toEqual([
      {
        x: 1,
        y: 2,
        blocksMovement: true,
        blocksEffect: false,
        blocksVision: false,
        cover: "none",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1,
      },
      {
        x: 4,
        y: 5,
        blocksMovement: false,
        blocksEffect: false,
        blocksVision: false,
        cover: "none",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 2,
      },
    ]);
  });

  it("serializes edge obstacle maps using the canonical preset semantics", () => {
    const edgeObstacleMap = new Map([
      ["1:2:E", "edge_barrier"],
      ["4:5:N", "edge_cover_half"],
    ] as const);

    const edgeObstacles = serializeEdgeObstacleMap(edgeObstacleMap);

    expect(edgeObstacles).toEqual([
      {
        x: 1,
        y: 2,
        direction: "E",
        blocksMovement: true,
        blocksVision: false,
        blocksEffect: false,
        cover: "none",
      },
      {
        x: 4,
        y: 5,
        direction: "N",
        blocksMovement: false,
        blocksVision: false,
        blocksEffect: false,
        cover: "half",
      },
    ]);
  });

  it("summarizes counts per preset", () => {
    const obstacleMap = new Map([
      ["0:0", "solid_wall"],
      ["0:1", "solid_wall"],
      ["1:0", "spell_blocker"],
    ] as const);

    const summary = summarizeObstacleMap(obstacleMap);

    expect(summary.find((entry) => entry.id === "solid_wall")?.count).toBe(2);
    expect(summary.find((entry) => entry.id === "spell_blocker")?.count).toBe(1);
    expect(summary.find((entry) => entry.id === "blocked_path")?.count).toBe(0);
  });

  it("builds and summarizes edge obstacle maps", () => {
    const config: CampaignMapConfig = {
      id: "map-edge-1",
      createdAt: "2026-01-01T00:00:00.000Z",
      edgeObstacles: [
        {
          x: 3,
          y: 4,
          direction: "E",
          blocksMovement: true,
          blocksVision: true,
          blocksEffect: true,
          cover: "full",
        },
      ],
    };

    const edgeObstacleMap = buildEdgeObstacleMap(config);
    const summary = summarizeEdgeObstacleMap(edgeObstacleMap);

    expect(edgeObstacleMap.get("3:4:E")).toBe("edge_wall");
    expect(summary.find((entry) => entry.id === "edge_wall")?.count).toBe(1);
    expect(
      summary.find((entry) => entry.id === "edge_effect_blocker")?.count,
    ).toBe(0);
  });

  it("formats and resolves hovered cells for inspection", () => {
    const obstacleMap = new Map([["5:7", "transparent_barrier"]] as const);
    const edgeObstacleMap = new Map([
      ["5:7:E", "edge_wall"],
      ["5:7:N", "edge_cover_half"],
    ] as const);

    expect(
      formatHoveredCell(
        { column: 6, row: 8 },
        { columnLabel: "Col", rowLabel: "Row" },
      ),
    ).toBe("Col 6 • Row 8");
    expect(
      getHoveredCellObstaclePreset(obstacleMap, { column: 6, row: 8 }),
    ).toBe("transparent_barrier");
    expect(
      getHoveredCellEdgePresets(edgeObstacleMap, { column: 6, row: 8 }),
    ).toEqual([
      { direction: "N", presetId: "edge_cover_half" },
      { direction: "E", presetId: "edge_wall" },
    ]);
    expect(getHoveredCellObstaclePreset(obstacleMap, null)).toBeNull();
  });
});
