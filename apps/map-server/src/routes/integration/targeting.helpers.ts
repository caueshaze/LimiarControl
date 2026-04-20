import {
  chebyshevDistance,
  resolveCone,
  resolveCube,
  resolveLine,
  resolveSphere,
} from "@limiarmap/tactical-engine";
import type { BattleMap, CombatState, Coordinate, EdgeObstacle, Obstacle, Token } from "@limiarmap/shared-contracts";

type Reply = {
  status(code: number): { send(payload: unknown): unknown };
};

type EncounterLike = {
  battleMap: BattleMap;
  combatState: CombatState;
  edgeObstacles: EdgeObstacle[];
  obstacles: Obstacle[];
  tokens: Token[];
};

type AreaTargetShape = "sphere" | "cone" | "line" | "cube";

export function err(reply: Reply, status: number, reason: string, message: string) {
  return reply.status(status).send({ message, reason });
}

export function buildAreaRejection(
  encounter: EncounterLike,
  sessionId: string,
  actionId: string,
  shape: AreaTargetShape,
  reason: string,
  sourceTokenId: string | null,
) {
  return {
    isValid: false,
    reason,
    sessionId,
    actionId,
    version: encounter.combatState.version,
    shape,
    sourceTokenId,
    affectedCells: [],
    affectedTokenIds: [],
    affectedCombatantIds: [],
  };
}

export function isCellInsideMap(encounter: EncounterLike, cell: Coordinate) {
  return (
    cell.x >= 0 &&
    cell.y >= 0 &&
    cell.x < encounter.battleMap.gridWidth &&
    cell.y < encounter.battleMap.gridHeight
  );
}

export function resolveAreaTargeting(encounter: EncounterLike, params: {
  anchorCell: Coordinate;
  originCell: Coordinate;
  rangeCells: number | null;
  shape: AreaTargetShape;
  sizeCells: number;
}) {
  const { anchorCell, originCell, rangeCells, shape, sizeCells } = params;
  const effectiveRange = rangeCells ?? Math.max(chebyshevDistance(originCell, anchorCell), 1);
  const affectedCells =
    shape === "cone"
      ? resolveCone(originCell, anchorCell, sizeCells, encounter.obstacles, encounter.edgeObstacles)
      : shape === "line"
        ? resolveLine(originCell, anchorCell, effectiveRange, encounter.obstacles, encounter.edgeObstacles)
        : shape === "cube"
          ? resolveCube(anchorCell, sizeCells, encounter.obstacles, encounter.edgeObstacles)
          : resolveSphere(anchorCell, sizeCells, encounter.obstacles, encounter.edgeObstacles);
  const affectedCellKeySet = new Set(affectedCells.map((cell) => `${cell.x}:${cell.y}`));
  const affectedTokens = encounter.tokens.filter((token) =>
    affectedCellKeySet.has(`${token.position.x}:${token.position.y}`),
  );
  const affectedCombatantIds = [
    ...new Set(
      affectedTokens
        .map((token) => token.combatantId)
        .filter((combatantId): combatantId is string => typeof combatantId === "string" && combatantId.length > 0),
    ),
  ];

  return {
    affectedCells,
    affectedCombatantIds,
    affectedTokenIds: affectedTokens.map((token) => token.id),
  };
}
