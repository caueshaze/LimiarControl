import { describe, it, expect } from "vitest";
import {
  getEdgeBetweenCells,
  isEdgeBlocked,
  isEdgeBlockingVision,
  isEdgeBlockingEffect,
  getEdgeCover,
  isInsideMap,
  validateMovement,
  hasLineOfSight,
  hasLineOfEffect,
  evaluateCover
} from "@limiarmap/tactical-engine";
import type { EdgeObstacle } from "@limiarmap/shared-contracts";

describe("Edge Obstacles - Grid State Helpers", () => {
  const mockGridState = {
    map: {
      id: "test-map",
      name: "Test Map",
      gridWidth: 20,
      gridHeight: 14,
      terrainVersion: 1,
      gridCalibration: {
        x: 0,
        y: 0,
        width: 1,
        height: 1
      }
    },
    obstacles: [],
    edgeObstacles: [],
    tokens: []
  };

  describe("getEdgeBetweenCells", () => {
    it("returns edge for East movement", () => {
      const edgeObstacles: EdgeObstacle[] = [
        {
          id: "edge-1",
          battleMapId: "test-map",
          x: 5,
          y: 5,
          direction: "E",
          blocksMovement: true,
          blocksVision: false,
          blocksEffect: false,
          cover: "none"
        }
      ];

      const gridStateWithEdge = { ...mockGridState, edgeObstacles };
      const edge = getEdgeBetweenCells(gridStateWithEdge, { x: 5, y: 5 }, { x: 6, y: 5 });
      expect(edge).toBeDefined();
      expect(edge?.id).toBe("edge-1");
      expect(edge?.direction).toBe("E");
    });

    it("returns edge for West movement", () => {
      const edgeObstacles: EdgeObstacle[] = [
        {
          id: "edge-1",
          battleMapId: "test-map",
          x: 6,
          y: 5,
          direction: "W",
          blocksMovement: true,
          blocksVision: false,
          blocksEffect: false,
          cover: "none"
        }
      ];

      const gridStateWithEdge = { ...mockGridState, edgeObstacles };
      const edge = getEdgeBetweenCells(gridStateWithEdge, { x: 6, y: 5 }, { x: 5, y: 5 });
      expect(edge).toBeDefined();
      expect(edge?.id).toBe("edge-1");
      expect(edge?.direction).toBe("W");
    });

    it("returns edge for North movement", () => {
      const edgeObstacles: EdgeObstacle[] = [
        {
          id: "edge-1",
          battleMapId: "test-map",
          x: 5,
          y: 6,
          direction: "N",
          blocksMovement: true,
          blocksVision: false,
          blocksEffect: false,
          cover: "none"
        }
      ];

      const gridStateWithEdge = { ...mockGridState, edgeObstacles };
      const edge = getEdgeBetweenCells(gridStateWithEdge, { x: 5, y: 6 }, { x: 5, y: 5 });
      expect(edge).toBeDefined();
      expect(edge?.id).toBe("edge-1");
      expect(edge?.direction).toBe("N");
    });

    it("returns edge for South movement", () => {
      const edgeObstacles: EdgeObstacle[] = [
        {
          id: "edge-1",
          battleMapId: "test-map",
          x: 5,
          y: 5,
          direction: "S",
          blocksMovement: true,
          blocksVision: false,
          blocksEffect: false,
          cover: "none"
        }
      ];

      const gridStateWithEdge = { ...mockGridState, edgeObstacles };
      const edge = getEdgeBetweenCells(gridStateWithEdge, { x: 5, y: 5 }, { x: 5, y: 6 });
      expect(edge).toBeDefined();
      expect(edge?.id).toBe("edge-1");
      expect(edge?.direction).toBe("S");
    });

    it("returns undefined for non-adjacent cells", () => {
      const edge = getEdgeBetweenCells(mockGridState, { x: 5, y: 5 }, { x: 7, y: 5 });
      expect(edge).toBeUndefined();
    });

    it("returns undefined for diagonal movement", () => {
      const edge = getEdgeBetweenCells(mockGridState, { x: 5, y: 5 }, { x: 6, y: 6 });
      expect(edge).toBeUndefined();
    });
  });

  describe("isEdgeBlocked", () => {
    it("returns true when edge blocks movement", () => {
      const edgeObstacles: EdgeObstacle[] = [
        {
          id: "edge-1",
          battleMapId: "test-map",
          x: 5,
          y: 5,
          direction: "E",
          blocksMovement: true,
          blocksVision: false,
          blocksEffect: false,
          cover: "none"
        }
      ];

      const gridStateWithEdge = { ...mockGridState, edgeObstacles };
      expect(isEdgeBlocked(gridStateWithEdge, { x: 5, y: 5 }, { x: 6, y: 5 })).toBe(true);
    });

    it("returns false when edge does not block movement", () => {
      const edgeObstacles: EdgeObstacle[] = [
        {
          id: "edge-1",
          battleMapId: "test-map",
          x: 5,
          y: 5,
          direction: "E",
          blocksMovement: false,
          blocksVision: false,
          blocksEffect: true,
          cover: "half"
        }
      ];

      const gridStateWithEdge = { ...mockGridState, edgeObstacles };
      expect(isEdgeBlocked(gridStateWithEdge, { x: 5, y: 5 }, { x: 6, y: 5 })).toBe(false);
    });

    it("returns false when no edge exists", () => {
      expect(isEdgeBlocked(mockGridState, { x: 5, y: 5 }, { x: 6, y: 5 })).toBe(false);
    });
  });

  describe("isEdgeBlockingVision", () => {
    it("returns true when edge blocks vision", () => {
      const edgeObstacles: EdgeObstacle[] = [
        {
          id: "edge-1",
          battleMapId: "test-map",
          x: 5,
          y: 5,
          direction: "E",
          blocksMovement: false,
          blocksVision: true,
          blocksEffect: false,
          cover: "none"
        }
      ];

      const gridStateWithEdge = { ...mockGridState, edgeObstacles };
      expect(isEdgeBlockingVision(gridStateWithEdge, { x: 5, y: 5 }, { x: 6, y: 5 })).toBe(true);
    });

    it("returns false when edge does not block vision", () => {
      const edgeObstacles: EdgeObstacle[] = [
        {
          id: "edge-1",
          battleMapId: "test-map",
          x: 5,
          y: 5,
          direction: "E",
          blocksMovement: true,
          blocksVision: false,
          blocksEffect: true,
          cover: "none"
        }
      ];

      const gridStateWithEdge = { ...mockGridState, edgeObstacles };
      expect(isEdgeBlockingVision(gridStateWithEdge, { x: 5, y: 5 }, { x: 6, y: 5 })).toBe(false);
    });

    it("returns false when no edge exists", () => {
      expect(isEdgeBlockingVision(mockGridState, { x: 5, y: 5 }, { x: 6, y: 5 })).toBe(false);
    });
  });

  describe("isEdgeBlockingEffect", () => {
    it("returns true when edge blocks effect", () => {
      const edgeObstacles: EdgeObstacle[] = [
        {
          id: "edge-1",
          battleMapId: "test-map",
          x: 5,
          y: 5,
          direction: "E",
          blocksMovement: false,
          blocksVision: false,
          blocksEffect: true,
          cover: "none"
        }
      ];

      const gridStateWithEdge = { ...mockGridState, edgeObstacles };
      expect(isEdgeBlockingEffect(gridStateWithEdge, { x: 5, y: 5 }, { x: 6, y: 5 })).toBe(true);
    });

    it("returns false when edge does not block effect", () => {
      const edgeObstacles: EdgeObstacle[] = [
        {
          id: "edge-1",
          battleMapId: "test-map",
          x: 5,
          y: 5,
          direction: "E",
          blocksMovement: true,
          blocksVision: true,
          blocksEffect: false,
          cover: "none"
        }
      ];

      const gridStateWithEdge = { ...mockGridState, edgeObstacles };
      expect(isEdgeBlockingEffect(gridStateWithEdge, { x: 5, y: 5 }, { x: 6, y: 5 })).toBe(false);
    });

    it("returns false when no edge exists", () => {
      expect(isEdgeBlockingEffect(mockGridState, { x: 5, y: 5 }, { x: 6, y: 5 })).toBe(false);
    });
  });

  describe("getEdgeCover", () => {
    it("returns half cover when edge provides half cover", () => {
      const edgeObstacles: EdgeObstacle[] = [
        {
          id: "edge-1",
          battleMapId: "test-map",
          x: 5,
          y: 5,
          direction: "E",
          blocksMovement: false,
          blocksVision: false,
          blocksEffect: false,
          cover: "half"
        }
      ];

      const gridStateWithEdge = { ...mockGridState, edgeObstacles };
      expect(getEdgeCover(gridStateWithEdge, { x: 5, y: 5 }, { x: 6, y: 5 })).toBe("half");
    });

    it("returns three_quarters cover when edge provides three-quarters cover", () => {
      const edgeObstacles: EdgeObstacle[] = [
        {
          id: "edge-1",
          battleMapId: "test-map",
          x: 5,
          y: 5,
          direction: "E",
          blocksMovement: false,
          blocksVision: false,
          blocksEffect: false,
          cover: "threeQuarters"
        }
      ];

      const gridStateWithEdge = { ...mockGridState, edgeObstacles };
      expect(getEdgeCover(gridStateWithEdge, { x: 5, y: 5 }, { x: 6, y: 5 })).toBe("threeQuarters");
    });

    it("returns none when edge provides no cover", () => {
      const edgeObstacles: EdgeObstacle[] = [
        {
          id: "edge-1",
          battleMapId: "test-map",
          x: 5,
          y: 5,
          direction: "E",
          blocksMovement: true,
          blocksVision: false,
          blocksEffect: false,
          cover: "none"
        }
      ];

      const gridStateWithEdge = { ...mockGridState, edgeObstacles };
      expect(getEdgeCover(gridStateWithEdge, { x: 5, y: 5 }, { x: 6, y: 5 })).toBe("none");
    });

    it("returns none when no edge exists", () => {
      expect(getEdgeCover(mockGridState, { x: 5, y: 5 }, { x: 6, y: 5 })).toBe("none");
    });
  });
});

describe("Edge Obstacles - Movement Validation", () => {
  const mockGridState = {
    map: {
      id: "test-map",
      name: "Test Map",
      gridWidth: 20,
      gridHeight: 14,
      terrainVersion: 1,
      gridCalibration: {
        x: 0,
        y: 0,
        width: 1,
        height: 1
      }
    },
    obstacles: [],
    edgeObstacles: [],
    tokens: []
  };

  const mockToken = {
    id: "token-1",
    battleMapId: "test-map",
    label: "Test Token",
    kind: "playerCharacter" as const,
    controllerType: "player" as const,
    controllerId: "player-1",
    position: { x: 5, y: 5 },
    movementSpeedCells: 6,
    movementBudget: 30
  };

  it("rejects movement when edge blocks movement", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-1",
        battleMapId: "test-map",
        x: 5,
        y: 5,
        direction: "E",
        blocksMovement: true,
        blocksVision: false,
        blocksEffect: false,
        cover: "none"
      }
    ];

    const gridStateWithEdge = { ...mockGridState, edgeObstacles };
    const result = validateMovement(gridStateWithEdge, mockToken, [{ x: 6, y: 5 }]);
    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("blocked_path");
  });

  it("allows movement when edge does not block movement", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-1",
        battleMapId: "test-map",
        x: 5,
        y: 5,
        direction: "E",
        blocksMovement: false,
        blocksVision: true,
        blocksEffect: true,
        cover: "half"
      }
    ];

    const gridStateWithEdge = { ...mockGridState, edgeObstacles };
    const result = validateMovement(gridStateWithEdge, mockToken, [{ x: 6, y: 5 }]);
    expect(result.accepted).toBe(true);
  });

  it("allows movement when no edge exists", () => {
    const result = validateMovement(mockGridState, mockToken, [{ x: 6, y: 5 }]);
    expect(result.accepted).toBe(true);
  });

  it("rejects movement when multiple edges block path", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-1",
        battleMapId: "test-map",
        x: 5,
        y: 5,
        direction: "E",
        blocksMovement: true,
        blocksVision: false,
        blocksEffect: false,
        cover: "none"
      },
      {
        id: "edge-2",
        battleMapId: "test-map",
        x: 6,
        y: 5,
        direction: "S",
        blocksMovement: true,
        blocksVision: false,
        blocksEffect: false,
        cover: "none"
      }
    ];

    const gridStateWithEdge = { ...mockGridState, edgeObstacles };
    const result = validateMovement(gridStateWithEdge, mockToken, [{ x: 6, y: 6 }]);
    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("blocked_path");
  });
});

describe("Edge Obstacles - Line of Sight", () => {
  const mockObstacles = [];

  it("blocks line of sight when edge blocks vision", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-1",
        battleMapId: "test-map",
        x: 5,
        y: 5,
        direction: "E",
        blocksMovement: false,
        blocksVision: true,
        blocksEffect: false,
        cover: "none"
      }
    ];

    expect(hasLineOfSight(mockObstacles, { x: 4, y: 5 }, { x: 7, y: 5 }, edgeObstacles)).toBe(false);
  });

  it("allows line of sight when edge does not block vision", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-1",
        battleMapId: "test-map",
        x: 5,
        y: 5,
        direction: "E",
        blocksMovement: true,
        blocksVision: false,
        blocksEffect: true,
        cover: "none"
      }
    ];

    expect(hasLineOfSight(mockObstacles, { x: 4, y: 5 }, { x: 7, y: 5 }, edgeObstacles)).toBe(true);
  });

  it("allows line of sight when no edges exist", () => {
    expect(hasLineOfSight(mockObstacles, { x: 4, y: 5 }, { x: 7, y: 5 })).toBe(true);
  });

  it("blocks line of sight for vertical lines", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-1",
        battleMapId: "test-map",
        x: 5,
        y: 5,
        direction: "S",
        blocksMovement: false,
        blocksVision: true,
        blocksEffect: false,
        cover: "none"
      }
    ];

    expect(hasLineOfSight(mockObstacles, { x: 5, y: 4 }, { x: 5, y: 7 }, edgeObstacles)).toBe(false);
  });

  it("blocks line of sight across an adjacent blocked edge", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-adjacent-los",
        battleMapId: "test-map",
        x: 4,
        y: 4,
        direction: "E",
        blocksMovement: true,
        blocksVision: true,
        blocksEffect: false,
        cover: "full"
      }
    ];

    expect(hasLineOfSight(mockObstacles, { x: 4, y: 4 }, { x: 5, y: 4 }, edgeObstacles)).toBe(false);
  });
});

describe("Edge Obstacles - Line of Effect", () => {
  const mockObstacles = [];

  it("blocks line of effect when edge blocks effects", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-1",
        battleMapId: "test-map",
        x: 5,
        y: 5,
        direction: "E",
        blocksMovement: false,
        blocksVision: false,
        blocksEffect: true,
        cover: "none"
      }
    ];

    expect(hasLineOfEffect(mockObstacles, { x: 4, y: 5 }, { x: 7, y: 5 }, edgeObstacles)).toBe(false);
  });

  it("allows line of effect when edge does not block effects", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-1",
        battleMapId: "test-map",
        x: 5,
        y: 5,
        direction: "E",
        blocksMovement: true,
        blocksVision: true,
        blocksEffect: false,
        cover: "none"
      }
    ];

    expect(hasLineOfEffect(mockObstacles, { x: 4, y: 5 }, { x: 7, y: 5 }, edgeObstacles)).toBe(true);
  });

  it("allows line of effect when no edges exist", () => {
    expect(hasLineOfEffect(mockObstacles, { x: 4, y: 5 }, { x: 7, y: 5 })).toBe(true);
  });

  it("supports transparent barriers (vision OK, effect blocked)", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-1",
        battleMapId: "test-map",
        x: 5,
        y: 5,
        direction: "E",
        blocksMovement: false,
        blocksVision: false,
        blocksEffect: true,
        cover: "none"
      }
    ];

    expect(hasLineOfSight(mockObstacles, { x: 4, y: 5 }, { x: 7, y: 5 }, edgeObstacles)).toBe(true);
    expect(hasLineOfEffect(mockObstacles, { x: 4, y: 5 }, { x: 7, y: 5 }, edgeObstacles)).toBe(false);
  });

  it("blocks line of effect across an adjacent blocked edge", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-adjacent-loe",
        battleMapId: "test-map",
        x: 4,
        y: 4,
        direction: "E",
        blocksMovement: false,
        blocksVision: false,
        blocksEffect: true,
        cover: "none"
      }
    ];

    expect(hasLineOfEffect(mockObstacles, { x: 4, y: 4 }, { x: 5, y: 4 }, edgeObstacles)).toBe(false);
  });
});

describe("Edge Obstacles - Cover Integration", () => {
  const mockObstacles = [];

  it("returns half cover when edge provides half cover", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-1",
        battleMapId: "test-map",
        x: 5,
        y: 5,
        direction: "E",
        blocksMovement: false,
        blocksVision: false,
        blocksEffect: false,
        cover: "half"
      }
    ];

    const cover = evaluateCover(mockObstacles, { x: 4, y: 5 }, { x: 7, y: 5 }, edgeObstacles);
    expect(cover).toBe("half");
  });

  it("returns three_quarters cover when edge provides three-quarters cover", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-1",
        battleMapId: "test-map",
        x: 5,
        y: 5,
        direction: "E",
        blocksMovement: false,
        blocksVision: false,
        blocksEffect: false,
        cover: "threeQuarters"
      }
    ];

    const cover = evaluateCover(mockObstacles, { x: 4, y: 5 }, { x: 7, y: 5 }, edgeObstacles);
    expect(cover).toBe("threeQuarters");
  });

  it("returns none when edge provides no cover", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-1",
        battleMapId: "test-map",
        x: 5,
        y: 5,
        direction: "E",
        blocksMovement: true,
        blocksVision: false,
        blocksEffect: false,
        cover: "none"
      }
    ];

    const cover = evaluateCover(mockObstacles, { x: 4, y: 5 }, { x: 7, y: 5 }, edgeObstacles);
    expect(cover).toBe("none");
  });

  it("returns none when no edges exist", () => {
    const cover = evaluateCover(mockObstacles, { x: 4, y: 5 }, { x: 7, y: 5 });
    expect(cover).toBe("none");
  });

  it("aggregates multiple edge covers correctly (strongest wins)", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-1",
        battleMapId: "test-map",
        x: 5,
        y: 5,
        direction: "E",
        blocksMovement: false,
        blocksVision: false,
        blocksEffect: false,
        cover: "half"
      },
      {
        id: "edge-2",
        battleMapId: "test-map",
        x: 6,
        y: 5,
        direction: "E",
        blocksMovement: false,
        blocksVision: false,
        blocksEffect: false,
        cover: "threeQuarters"
      }
    ];

    const cover = evaluateCover(mockObstacles, { x: 4, y: 5 }, { x: 7, y: 5 }, edgeObstacles);
    expect(cover).toBe("threeQuarters");
  });

  it("includes adjacent edge cover between source and target", () => {
    const edgeObstacles: EdgeObstacle[] = [
      {
        id: "edge-adjacent-cover",
        battleMapId: "test-map",
        x: 4,
        y: 4,
        direction: "E",
        blocksMovement: false,
        blocksVision: false,
        blocksEffect: false,
        cover: "full"
      }
    ];

    const cover = evaluateCover(mockObstacles, { x: 4, y: 4 }, { x: 5, y: 4 }, edgeObstacles);
    expect(cover).toBe("full");
  });
});
