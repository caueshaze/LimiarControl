import type {
  BattleMap,
  CombatState,
  Coordinate,
  EdgeObstacle,
  GridCalibration,
  Obstacle,
  Token
} from "@limiarmap/shared-contracts";
import { ActionIdempotencyTracker } from "@limiarmap/tactical-engine";

export interface EncounterState {
  sessionId: string;
  battleMap: BattleMap;
  battleMapSourceImageUrl?: string | null;
  tokens: Token[];
  obstacles: Obstacle[];
  edgeObstacles: EdgeObstacle[];
  combatState: CombatState;
  actionTracker: ActionIdempotencyTracker;
}

type BattleMapSeed = {
  name: string;
  gridWidth: number;
  gridHeight: number;
  gridCalibration: GridCalibration;
  imageUrl?: string;
  sourceImageUrl?: string | null;
};

const DEFAULT_BATTLE_MAP_SEED: BattleMapSeed = {
  name: "Demo Encounter",
  gridWidth: 20,
  gridHeight: 14,
  gridCalibration: {
    x: 0,
    y: 0,
    width: 1,
    height: 1
  },
  imageUrl: "/maps/map.jpg",
  sourceImageUrl: null
};

function createDemoEncounter(
  sessionId = "demo-session",
  battleMapSeed: BattleMapSeed = DEFAULT_BATTLE_MAP_SEED
): EncounterState {
  const battleMapId = sessionId === "demo-session" ? "map_1" : `map_${sessionId}`;
  const encounterId = sessionId === "demo-session" ? "enc_1" : `enc_${sessionId}`;
  const combatId = sessionId === "demo-session" ? "combat_1" : `combat_${sessionId}`;
  const battleMap: BattleMap = {
    id: battleMapId,
    name: battleMapSeed.name,
    gridWidth: battleMapSeed.gridWidth,
    gridHeight: battleMapSeed.gridHeight,
    imageUrl: battleMapSeed.imageUrl,
    terrainVersion: 1,
    gridCalibration: battleMapSeed.gridCalibration,
    activeEncounterId: encounterId
  };

  const obstacles: Obstacle[] = [
    {
      id: "obs_1",
      battleMapId: battleMap.id,
      label: "Parede demo",
      cells: [{ x: 8, y: 8 }],
      blocksMovement: true,
      blocksEffect: true,
      blocksVision: true,
      cover: "full",
      clipsDiagonalMovement: true,
      movementCostMultiplier: 1
    }
  ];

  const tokens: Token[] = [
    {
      id: "tok_player",
      battleMapId: battleMap.id,
      label: "Hero",
      kind: "playerCharacter",
      controllerType: "player",
      controllerId: "player_1",
      position: { x: 4, y: 4 },
      movementSpeedCells: 6,   // 6 cells = 9 m = ~30 ft (standard D&D character)
      movementBudget: 30,       // 6 cells × 5 path-cost units/cell
      combatantId: "cmb_1"
    },
    {
      id: "tok_enemy",
      battleMapId: battleMap.id,
      label: "Goblin",
      kind: "enemy",
      controllerType: "gm",
      controllerId: "gm_1",
      position: { x: 10, y: 10 },
      movementSpeedCells: 6,   // 6 cells = 9 m = ~30 ft
      movementBudget: 30,
      combatantId: "cmb_2"
    }
  ];

  const combatState: CombatState = {
    id: combatId,
    battleMapId: battleMap.id,
    status: sessionId === "demo-session" ? "active" : "inactive",
    roundNumber: sessionId === "demo-session" ? 1 : 0,
    turnIndex: 0,
    activeCombatantId: sessionId === "demo-session" ? "cmb_1" : null,
    initiativeOrder: sessionId === "demo-session" ? ["cmb_1", "cmb_2"] : [],
    advancedBy: "LimiarControl",
    version: sessionId === "demo-session" ? 1 : 0
  };

  return {
    sessionId,
    battleMap,
    battleMapSourceImageUrl: battleMapSeed.sourceImageUrl ?? null,
    tokens,
    obstacles,
    edgeObstacles: [], // Phase 10: Initialize empty edge obstacles for backward compatibility
    combatState,
    actionTracker: new ActionIdempotencyTracker()
  };
}

export class InMemoryEncounterRepository {
  private readonly encounters = new Map<string, EncounterState>([
    ["demo-session", createDemoEncounter()]
  ]);

  createEncounter(sessionId: string, battleMapSeed?: BattleMapSeed): EncounterState {
    const encounter = createDemoEncounter(sessionId, battleMapSeed ?? DEFAULT_BATTLE_MAP_SEED);
    this.encounters.set(sessionId, encounter);
    return encounter;
  }

  getEncounter(sessionId: string): EncounterState | undefined {
    return this.encounters.get(sessionId);
  }

  ensureEncounter(sessionId: string, battleMapSeed?: BattleMapSeed): EncounterState {
    const existing = this.getEncounter(sessionId);
    if (existing) {
      if (battleMapSeed) {
        return this.updateBattleMap(sessionId, battleMapSeed);
      }
      return existing;
    }
    return this.createEncounter(sessionId, battleMapSeed);
  }

  saveEncounter(encounter: EncounterState): EncounterState {
    this.encounters.set(encounter.sessionId, encounter);
    return encounter;
  }

  updateTokenMovement(
    sessionId: string,
    tokenId: string,
    position: Coordinate,
    remainingBudget: number
  ): EncounterState {
    const encounter = this.requireEncounter(sessionId);
    encounter.tokens = encounter.tokens.map((token) =>
      token.id === tokenId ? { ...token, position, movementBudget: remainingBudget } : token
    );
    return this.saveEncounter(encounter);
  }

  resetTokenBudget(sessionId: string, tokenId: string): EncounterState {
    const encounter = this.requireEncounter(sessionId);
    encounter.tokens = encounter.tokens.map((token) =>
      // movementBudget is in path-cost units (5 per cell); movementSpeedCells is in cells.
      token.id === tokenId ? { ...token, movementBudget: token.movementSpeedCells * 5 } : token
    );
    return this.saveEncounter(encounter);
  }

  updateCombatState(sessionId: string, combatState: CombatState): EncounterState {
    const encounter = this.requireEncounter(sessionId);
    encounter.combatState = combatState;
    return this.saveEncounter(encounter);
  }

  updateBattleMapGridCalibration(
    sessionId: string,
    gridCalibration: GridCalibration,
    gridWidth: number,
    gridHeight: number
  ): EncounterState {
    const encounter = this.requireEncounter(sessionId);
    encounter.battleMap = {
      ...encounter.battleMap,
      gridCalibration,
      gridWidth,
      gridHeight
    };
    return this.saveEncounter(encounter);
  }

  updateBattleMap(sessionId: string, battleMapSeed: BattleMapSeed): EncounterState {
    const encounter = this.ensureEncounter(sessionId);
    encounter.battleMap = {
      ...encounter.battleMap,
      name: battleMapSeed.name,
      gridWidth: battleMapSeed.gridWidth,
      gridHeight: battleMapSeed.gridHeight,
      imageUrl: battleMapSeed.imageUrl,
      gridCalibration: battleMapSeed.gridCalibration,
      terrainVersion: encounter.battleMap.terrainVersion + 1
    };
    encounter.battleMapSourceImageUrl = battleMapSeed.sourceImageUrl ?? null;
    return this.saveEncounter(encounter);
  }

  setObstacles(sessionId: string, obstacles: Obstacle[]): EncounterState {
    const encounter = this.requireEncounter(sessionId);
    encounter.obstacles = obstacles;
    return this.saveEncounter(encounter);
  }

  // Phase 10: Edge obstacle methods
  setEdgeObstacles(sessionId: string, edgeObstacles: EdgeObstacle[]): EncounterState {
    const encounter = this.requireEncounter(sessionId);
    encounter.edgeObstacles = edgeObstacles;
    return this.saveEncounter(encounter);
  }

  addEdgeObstacle(sessionId: string, edgeObstacle: EdgeObstacle): EncounterState {
    const encounter = this.requireEncounter(sessionId);
    // Remove existing edge at same position if any
    encounter.edgeObstacles = encounter.edgeObstacles.filter(
      (e) => !(e.x === edgeObstacle.x && e.y === edgeObstacle.y && e.direction === edgeObstacle.direction)
    );
    encounter.edgeObstacles.push(edgeObstacle);
    return this.saveEncounter(encounter);
  }

  removeEdgeObstacle(sessionId: string, edgeObstacleId: string): EncounterState {
    const encounter = this.requireEncounter(sessionId);
    encounter.edgeObstacles = encounter.edgeObstacles.filter((e) => e.id !== edgeObstacleId);
    return this.saveEncounter(encounter);
  }

  syncTokens(
    sessionId: string,
    updates: Array<{
      tokenId: string;
      combatantId?: string;
      movementSpeedCells?: number;
      label?: string;
      controllerId?: string;
      controllerType?: Token["controllerType"];
      conditions?: string[];
    }>
  ): EncounterState {
    const encounter = this.requireEncounter(sessionId);
    encounter.tokens = encounter.tokens.map((token) => {
      const update = updates.find((u) => u.tokenId === token.id);
      if (!update) return token;
      const patched = { ...token };
      if (update.combatantId !== undefined) patched.combatantId = update.combatantId;
      if (update.label !== undefined) patched.label = update.label;
      if (update.controllerId !== undefined) patched.controllerId = update.controllerId;
      if (update.controllerType !== undefined) patched.controllerType = update.controllerType;
      if (update.movementSpeedCells !== undefined) {
        patched.movementSpeedCells = update.movementSpeedCells;
        // movementBudget is in path-cost units (5 per cell)
        patched.movementBudget = update.movementSpeedCells * 5;
      }
      // conditions: always replace when provided ([] explicitly clears all)
      if (update.conditions !== undefined) patched.conditions = update.conditions;
      return patched;
    });
    return this.saveEncounter(encounter);
  }

  requireEncounter(sessionId: string): EncounterState {
    const encounter = this.getEncounter(sessionId);
    if (!encounter) {
      throw new Error(`Encounter ${sessionId} not found`);
    }

    return encounter;
  }
}
