import { integrationSpatialEventEnvelopeSchema } from "@limiarmap/shared-contracts";
import { battleMapStore } from "../features/battle-map/battle-map-store";
import { sessionStore } from "./session-store";

function updateSnapshot(
  updater: (
    snapshot: NonNullable<ReturnType<typeof sessionStore.getSnapshot>>
  ) => ReturnType<typeof sessionStore.getSnapshot>
): void {
  const snapshot = sessionStore.getSnapshot();
  if (!snapshot) {
    return;
  }
  const nextSnapshot = updater(snapshot);
  if (nextSnapshot) {
    sessionStore.setSnapshot(nextSnapshot);
  }
}

export function handleRealtimePublication(data: unknown): void {
  const parsed = integrationSpatialEventEnvelopeSchema.safeParse(data);
  if (!parsed.success) {
    return;
  }

  const event = parsed.data;
  switch (event.eventType) {
    case "movement.applied": {
      const tokenId =
        typeof event.payload.tokenId === "string"
          ? event.payload.tokenId
          : null;
      const positionRaw = event.payload.position;
      const position =
        positionRaw !== null &&
        positionRaw !== undefined &&
        typeof positionRaw === "object" &&
        "x" in positionRaw &&
        "y" in positionRaw &&
        typeof (positionRaw as Record<string, unknown>)["x"] === "number" &&
        typeof (positionRaw as Record<string, unknown>)["y"] === "number"
          ? (positionRaw as { x: number; y: number })
          : null;
      const remainingBudget =
        typeof event.payload.remainingBudget === "number"
          ? event.payload.remainingBudget
          : null;
      if (!tokenId || !position || remainingBudget === null) {
        return;
      }
      updateSnapshot((snapshot) => ({
        ...snapshot,
        combatState: { ...snapshot.combatState, version: event.version },
        tokens: snapshot.tokens.map((token) =>
          token.id === tokenId
            ? {
                ...token,
                position,
                movementBudget: remainingBudget
              }
            : token
        )
      }));
      battleMapStore.clearTokenMovementRejection(tokenId);
      battleMapStore.setMovementPreview([]);
      battleMapStore.setMessage(undefined);
      return;
    }
    case "tokens.synced": {
      const tokens = Array.isArray(event.payload.tokens)
        ? event.payload.tokens
        : null;
      if (!tokens) {
        return;
      }
      updateSnapshot((snapshot) => ({
        ...snapshot,
        combatState: { ...snapshot.combatState, version: event.version },
        tokens: tokens as typeof snapshot.tokens
      }));
      return;
    }
    case "combat.started": {
      const payload = event.payload;
      if (
        !Array.isArray(payload.initiativeOrder) ||
        typeof payload.roundNumber !== "number" ||
        typeof payload.turnIndex !== "number"
      ) {
        return;
      }
      updateSnapshot((snapshot) => ({
        ...snapshot,
        combatState: {
          ...snapshot.combatState,
          status: "active",
          version: event.version,
          roundNumber: payload.roundNumber as number,
          turnIndex: payload.turnIndex as number,
          activeCombatantId:
            typeof payload.activeCombatantId === "string" ||
            payload.activeCombatantId === null
              ? (payload.activeCombatantId as string | null)
              : snapshot.combatState.activeCombatantId,
          initiativeOrder: (payload.initiativeOrder as unknown[]).filter(
            (value): value is string => typeof value === "string"
          )
        }
      }));
      return;
    }
    case "combat.advanced": {
      const payload = event.payload;
      if (
        typeof payload.roundNumber !== "number" ||
        typeof payload.turnIndex !== "number"
      ) {
        return;
      }
      updateSnapshot((snapshot) => ({
        ...snapshot,
        combatState: {
          ...snapshot.combatState,
          version: event.version,
          roundNumber: payload.roundNumber as number,
          turnIndex: payload.turnIndex as number,
          activeCombatantId:
            typeof payload.activeCombatantId === "string" ||
            payload.activeCombatantId === null
              ? (payload.activeCombatantId as string | null)
              : snapshot.combatState.activeCombatantId
        }
      }));
      return;
    }
    case "combat.ended": {
      const roundNumber =
        typeof event.payload.roundNumber === "number"
          ? event.payload.roundNumber
          : null;
      if (roundNumber === null) {
        return;
      }
      updateSnapshot((snapshot) => ({
        ...snapshot,
        combatState: {
          ...snapshot.combatState,
          status: "completed",
          version: event.version,
          roundNumber,
          activeCombatantId: null
        }
      }));
      return;
    }
    case "initiative.updated": {
      const payload = event.payload;
      if (
        !Array.isArray(payload.initiativeOrder) ||
        typeof payload.turnIndex !== "number"
      ) {
        return;
      }
      updateSnapshot((snapshot) => ({
        ...snapshot,
        combatState: {
          ...snapshot.combatState,
          version: event.version,
          initiativeOrder: (payload.initiativeOrder as unknown[]).filter(
            (value): value is string => typeof value === "string"
          ),
          turnIndex: payload.turnIndex as number,
          activeCombatantId:
            typeof payload.activeCombatantId === "string" ||
            payload.activeCombatantId === null
              ? (payload.activeCombatantId as string | null)
              : snapshot.combatState.activeCombatantId
        }
      }));
      return;
    }
    case "targeting.resolved": {
      const affectedCells = Array.isArray(event.payload.affectedCells)
        ? event.payload.affectedCells
        : [];
      battleMapStore.setTargetingPreview(affectedCells);
      battleMapStore.setMessage(undefined);
      return;
    }
    case "grid.calibration.updated": {
      const payload = event.payload;
      if (
        typeof payload.gridWidth !== "number" ||
        typeof payload.gridHeight !== "number" ||
        !payload.gridCalibration ||
        typeof payload.gridCalibration !== "object"
      ) {
        return;
      }
      updateSnapshot((snapshot) => ({
        ...snapshot,
        battleMap: {
          ...snapshot.battleMap,
          gridCalibration:
            payload.gridCalibration as typeof snapshot.battleMap.gridCalibration,
          gridWidth: payload.gridWidth as number,
          gridHeight: payload.gridHeight as number
        },
        combatState: { ...snapshot.combatState, version: event.version }
      }));
      if (battleMapStore.completeGridCalibrationUpdate(event.actionId)) {
        battleMapStore.setMessage(undefined);
      }
      return;
    }
    case "obstacles.updated": {
      const obstacles = Array.isArray(event.payload.obstacles)
        ? event.payload.obstacles
        : null;
      if (!obstacles) {
        return;
      }
      updateSnapshot((snapshot) => ({
        ...snapshot,
        obstacles: obstacles as typeof snapshot.obstacles,
        combatState: { ...snapshot.combatState, version: event.version }
      }));
      if (battleMapStore.completeObstaclePaintUpdate(event.actionId)) {
        battleMapStore.setMessage(undefined);
      }
      return;
    }
    case "edge_obstacles.updated": {
      const edgeObstacles = Array.isArray(event.payload.edgeObstacles)
        ? event.payload.edgeObstacles
        : null;
      if (!edgeObstacles) return;
      updateSnapshot((snapshot) => ({
        ...snapshot,
        edgeObstacles: edgeObstacles as typeof snapshot.edgeObstacles,
        combatState: { ...snapshot.combatState, version: event.version }
      }));
      if (battleMapStore.completeEdgePaintUpdate(event.actionId)) {
        battleMapStore.setMessage(undefined);
      }
      return;
    }
    case "elevation.updated": {
      const cellElevations = Array.isArray(event.payload.cellElevations)
        ? event.payload.cellElevations
        : null;
      if (!cellElevations) return;
      updateSnapshot((snapshot) => ({
        ...snapshot,
        cellElevations: cellElevations as typeof snapshot.cellElevations,
        combatState: { ...snapshot.combatState, version: event.version }
      }));
      if (battleMapStore.completeElevationPaintUpdate(event.actionId)) {
        battleMapStore.setMessage(undefined);
      }
      return;
    }
    case "action.rejected": {
      battleMapStore.setMovementPreview([]);
      battleMapStore.setTargetingPreview([]);
      battleMapStore.failGridCalibrationUpdate(event.actionId);
      battleMapStore.failObstaclePaintUpdate(event.actionId);
      battleMapStore.failEdgePaintUpdate(event.actionId);
      battleMapStore.failElevationPaintUpdate(event.actionId);
      const reason =
        typeof event.payload.reason === "string"
          ? event.payload.reason
          : "unknown";
      const message =
        typeof event.payload.message === "string"
          ? event.payload.message
          : typeof (event.payload as { details?: unknown }).details === "string"
            ? (event.payload as { details: string }).details
            : "Action rejected";
      const tokenId =
        typeof (event.payload as { tokenId?: unknown }).tokenId === "string"
          ? (event.payload as { tokenId: string }).tokenId
          : undefined;
      const pathCostUnits =
        typeof (event.payload as { pathCostUnits?: unknown }).pathCostUnits ===
        "number"
          ? (event.payload as { pathCostUnits: number }).pathCostUnits
          : undefined;
      const movementBudget =
        typeof (event.payload as { movementBudget?: unknown })
          .movementBudget === "number"
          ? (event.payload as { movementBudget: number }).movementBudget
          : undefined;
      const exceededBy =
        typeof (event.payload as { exceededBy?: unknown }).exceededBy ===
        "number"
          ? (event.payload as { exceededBy: number }).exceededBy
          : undefined;
      if (tokenId) {
        battleMapStore.setTokenMovementRejection({
          tokenId,
          reason,
          message,
          pathCostUnits,
          movementBudget,
          exceededBy
        });
      }
      battleMapStore.setMessage(message);
      return;
    }
    default:
      return;
  }
}
