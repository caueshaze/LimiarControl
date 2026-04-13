import { describe, expect, it } from "vitest";
import type { EncounterSnapshotResponse } from "@limiarmap/shared-contracts";
import { battleMapStore } from "../features/battle-map/battle-map-store";
import { sessionStore } from "./session-store";
import { handleRealtimePublication } from "./realtime-events";

function buildSnapshot(): EncounterSnapshotResponse {
  return {
    sessionId: "demo-session",
    battleMap: {
      id: "map-1",
      name: "Demo Map",
      imageUrl: "/maps/map.jpg",
      gridCalibration: {
        x: 0,
        y: 0,
        width: 1,
        height: 1
      },
      gridWidth: 20,
      gridHeight: 20,
      terrainVersion: 0
    },
    combatState: {
      id: "combat-1",
      battleMapId: "map-1",
      status: "active",
      roundNumber: 1,
      turnIndex: 0,
      activeCombatantId: "cmb_1",
      initiativeOrder: ["cmb_1", "cmb_2"],
      advancedBy: "LimiarControl",
      version: 1
    },
    obstacles: [],
    edgeObstacles: [],
    tokens: [
      {
        id: "tok_player",
        battleMapId: "map-1",
        label: "Player",
        kind: "playerCharacter",
        position: { x: 4, y: 4 },
        controllerId: "player_1",
        controllerType: "player",
        movementSpeedCells: 6,
        movementBudget: 30,
        combatantId: "cmb_1"
      }
    ]
  };
}

describe("map-web realtime events", () => {
  it("applies movement publications to the local snapshot", () => {
    sessionStore.setSnapshot(buildSnapshot());

    handleRealtimePublication({
      eventId: "move-1",
      eventType: "movement.applied",
      encounterId: "demo-session",
      version: 2,
      actionId: "action-1",
      payload: {
        tokenId: "tok_player",
        position: { x: 5, y: 4 },
        pathCostUnits: 5,
        remainingBudget: 25
      },
      replaySafe: true
    });

    const snapshot = sessionStore.getSnapshot();
    expect(snapshot?.combatState.version).toBe(2);
    expect(snapshot?.tokens[0]?.position).toEqual({ x: 5, y: 4 });
    expect(snapshot?.tokens[0]?.movementBudget).toBe(25);
  });

  it("surfaces rejection events using the unified message field", () => {
    sessionStore.setSnapshot(buildSnapshot());
    battleMapStore.setMovementPreview([{ x: 1, y: 1 }]);

    handleRealtimePublication({
      eventId: "reject-1",
      eventType: "action.rejected",
      encounterId: "demo-session",
      version: 2,
      actionId: "action-2",
      payload: {
        reason: "unauthorized_action",
        message: "Movement rejected"
      },
      replaySafe: true
    });

    expect(battleMapStore.getState().movementPreview).toEqual([]);
    expect(battleMapStore.getState().message).toBe("Movement rejected");
  });

  it("stores movement rejection values per token for selection details", () => {
    sessionStore.setSnapshot(buildSnapshot());

    handleRealtimePublication({
      eventId: "reject-2",
      eventType: "action.rejected",
      encounterId: "demo-session",
      version: 2,
      actionId: "action-3",
      payload: {
        reason: "movement_budget_exceeded",
        message: "Movement rejected",
        tokenId: "tok_player",
        pathCostUnits: 35,
        movementBudget: 30,
        exceededBy: 5
      },
      replaySafe: true
    });

    expect(
      battleMapStore.getState().lastMovementRejectionByTokenId.tok_player
    ).toEqual({
      tokenId: "tok_player",
      reason: "movement_budget_exceeded",
      message: "Movement rejected",
      pathCostUnits: 35,
      movementBudget: 30,
      exceededBy: 5
    });
  });

  it("applies edge_obstacles.updated events to the local snapshot", () => {
    sessionStore.setSnapshot(buildSnapshot());
    battleMapStore.markEdgePaintPending("edge-action-1");
    battleMapStore.setMessage("Aplicando borda...");

    const beforeVersion = sessionStore.getSnapshot()?.combatState.version;
    console.log("before version:", beforeVersion);
    console.log("after version:", snapshot?.combatState.version);
    console.log("after edgeObstacles:", snapshot?.edgeObstacles);
    expect(snapshot?.combatState.version).toBe(3);

    expect(snapshot?.edgeObstacles).toHaveLength(1);
    expect(snapshot?.edgeObstacles?.[0]).toMatchObject({
      x: 5,
      y: 5,
      direction: "E",
      blocksMovement: true
    });
    expect(battleMapStore.getState().pendingEdgePaintActionId).toBeUndefined();
    expect(battleMapStore.getState().message).toBeUndefined();
  });
});
