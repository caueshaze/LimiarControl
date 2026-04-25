import type {
  EncounterSnapshotResponse,
  IntegrationStateResponse
} from "@limiarmap/shared-contracts";
import type { EncounterState } from "./encounter-repository";

export function toEncounterSnapshot(
  encounter: EncounterState
): EncounterSnapshotResponse {
  return {
    sessionId: encounter.sessionId,
    battleMap: encounter.battleMap,
    combatState: encounter.combatState,
    tokens: encounter.tokens,
    obstacles: encounter.obstacles,
    edgeObstacles: encounter.edgeObstacles,
    activeAreaEffects: encounter.activeAreaEffects
  };
}

/**
 * Integration-specific snapshot with `version` promoted to the top level.
 * External consumers (LimiarControl) should use this instead of the standard
 * snapshot so they can detect state drift without parsing nested combatState.
 */
export function toIntegrationSnapshot(
  encounter: EncounterState
): IntegrationStateResponse {
  return {
    sessionId: encounter.sessionId,
    version: encounter.combatState.version,
    battleMap: encounter.battleMap,
    combatState: encounter.combatState,
    tokens: encounter.tokens,
    obstacles: encounter.obstacles,
    edgeObstacles: encounter.edgeObstacles,
    activeAreaEffects: encounter.activeAreaEffects
  };
}
