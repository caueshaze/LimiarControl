import { randomUUID } from "node:crypto";
import type { InitiativeEntry, TokenSyncEntry } from "@limiarmap/shared-contracts";
import type { InMemoryEncounterRepository } from "../encounters/encounter-repository";
import type { BroadcastAdapter } from "../realtime/broadcast";
import { broadcastAuthoritativeEvent } from "../realtime/broadcast";

const LOG_PREFIX = "[integration]";

/**
 * Manages combat lifecycle and initiative order on behalf of LimiarControl.
 *
 * Responsibilities:
 *  - Start / end combat (including restart after a completed encounter)
 *  - Set or replace initiative order (mid-combat safe)
 *  - Sync token metadata (combatantId, speed, controller)
 *
 * Every mutating method:
 *  1. Guards against duplicate actionIds (idempotency)
 *  2. Updates the repository
 *  3. Broadcasts a typed Centrifugo event to all connected web clients
 */
export class InitiativeService {
  constructor(
    private readonly repository: InMemoryEncounterRepository,
    private readonly broadcaster?: BroadcastAdapter
  ) {}

  // -------------------------------------------------------------------------
  // Combat lifecycle
  // -------------------------------------------------------------------------

  startCombat(sessionId: string, actionId: string, combatants: InitiativeEntry[]) {
    const encounter = this.repository.requireEncounter(sessionId);

    if (encounter.actionTracker.has(actionId)) {
      console.info(`${LOG_PREFIX} startCombat duplicate_action session=${sessionId} actionId=${actionId}`);
      return { accepted: false, reason: "duplicate_action" } as const;
    }

    // Allow restart from "inactive" or "completed" — reject only if already active
    if (encounter.combatState.status === "active") {
      console.warn(`${LOG_PREFIX} startCombat combat_already_active session=${sessionId}`);
      return { accepted: false, reason: "combat_already_active" } as const;
    }

    const initiativeOrder = sortByScore(combatants);
    const activeCombatantId = initiativeOrder[0] ?? null;

    encounter.actionTracker.record(actionId);
    this.repository.updateCombatState(sessionId, {
      ...encounter.combatState,
      status: "active",
      roundNumber: 1,
      turnIndex: 0,
      activeCombatantId,
      initiativeOrder,
      version: encounter.combatState.version + 1
    });

    if (activeCombatantId) {
      resetBudgetForCombatant(this.repository, sessionId, activeCombatantId);
    }

    const updated = this.repository.requireEncounter(sessionId);
    console.info(
      `${LOG_PREFIX} startCombat accepted session=${sessionId} ` +
        `activeCombatantId=${activeCombatantId} order=[${initiativeOrder.join(",")}] ` +
        `version=${updated.combatState.version}`
    );

    broadcastAuthoritativeEvent(this.broadcaster, "combat.started", {
      eventId: randomUUID(),
      eventType: "combat.started",
      encounterId: sessionId,
      version: updated.combatState.version,
      actionId,
      payload: {
        roundNumber: updated.combatState.roundNumber,
        turnIndex: updated.combatState.turnIndex,
        activeCombatantId: updated.combatState.activeCombatantId,
        initiativeOrder: updated.combatState.initiativeOrder
      },
      replaySafe: true
    });

    return { accepted: true, encounter: updated } as const;
  }

  endCombat(sessionId: string, actionId: string) {
    const encounter = this.repository.requireEncounter(sessionId);

    if (encounter.actionTracker.has(actionId)) {
      console.info(`${LOG_PREFIX} endCombat duplicate_action session=${sessionId} actionId=${actionId}`);
      return { accepted: false, reason: "duplicate_action" } as const;
    }

    encounter.actionTracker.record(actionId);
    this.repository.updateCombatState(sessionId, {
      ...encounter.combatState,
      status: "completed",
      activeCombatantId: null,
      version: encounter.combatState.version + 1
    });

    const updated = this.repository.requireEncounter(sessionId);
    console.info(
      `${LOG_PREFIX} endCombat accepted session=${sessionId} ` +
        `round=${updated.combatState.roundNumber} version=${updated.combatState.version}`
    );

    broadcastAuthoritativeEvent(this.broadcaster, "combat.ended", {
      eventId: randomUUID(),
      eventType: "combat.ended",
      encounterId: sessionId,
      version: updated.combatState.version,
      actionId,
      payload: { roundNumber: updated.combatState.roundNumber },
      replaySafe: true
    });

    return { accepted: true, encounter: updated } as const;
  }

  // -------------------------------------------------------------------------
  // Initiative management
  // -------------------------------------------------------------------------

  /**
   * Replace the full initiative order.
   * When the current active combatant is still in the new list their position
   * is preserved; otherwise the first combatant in the new order becomes active.
   */
  setInitiative(sessionId: string, actionId: string, combatants: InitiativeEntry[]) {
    const encounter = this.repository.requireEncounter(sessionId);

    if (encounter.actionTracker.has(actionId)) {
      console.info(`${LOG_PREFIX} setInitiative duplicate_action session=${sessionId} actionId=${actionId}`);
      return { accepted: false, reason: "duplicate_action" } as const;
    }

    const initiativeOrder = sortByScore(combatants);
    const currentActive = encounter.combatState.activeCombatantId;
    const indexInNew = currentActive ? initiativeOrder.indexOf(currentActive) : -1;
    const turnIndex = indexInNew >= 0 ? indexInNew : 0;
    const activeCombatantId = initiativeOrder[turnIndex] ?? null;

    encounter.actionTracker.record(actionId);
    this.repository.updateCombatState(sessionId, {
      ...encounter.combatState,
      initiativeOrder,
      turnIndex,
      activeCombatantId,
      version: encounter.combatState.version + 1
    });

    const updated = this.repository.requireEncounter(sessionId);
    console.info(
      `${LOG_PREFIX} setInitiative accepted session=${sessionId} ` +
        `activeCombatantId=${activeCombatantId} order=[${initiativeOrder.join(",")}] ` +
        `version=${updated.combatState.version}`
    );

    broadcastAuthoritativeEvent(this.broadcaster, "initiative.updated", {
      eventId: randomUUID(),
      eventType: "initiative.updated",
      encounterId: sessionId,
      version: updated.combatState.version,
      actionId,
      payload: {
        initiativeOrder: updated.combatState.initiativeOrder,
        activeCombatantId: updated.combatState.activeCombatantId,
        turnIndex: updated.combatState.turnIndex
      },
      replaySafe: true
    });

    return { accepted: true, encounter: updated } as const;
  }

  // -------------------------------------------------------------------------
  // Token sync
  // -------------------------------------------------------------------------

  /**
   * Patch token metadata controlled by LimiarControl (combatantId, speed,
   * controller info). Unknown tokenIds cause an early rejection so the caller
   * knows exactly which ID failed.
   */
  syncTokens(sessionId: string, tokens: TokenSyncEntry[]) {
    const encounter = this.repository.requireEncounter(sessionId);

    for (const update of tokens) {
      if (!encounter.tokens.find((t) => t.id === update.tokenId)) {
        console.warn(
          `${LOG_PREFIX} syncTokens unknown_token session=${sessionId} tokenId=${update.tokenId}`
        );
        return { accepted: false, reason: "unknown_token", tokenId: update.tokenId } as const;
      }
    }

    this.repository.syncTokens(sessionId, tokens);
    const updated = this.repository.requireEncounter(sessionId);

    const linkedCount = tokens.filter((t) => t.combatantId !== undefined).length;
    console.info(
      `${LOG_PREFIX} syncTokens accepted session=${sessionId} ` +
        `updatedTokens=${tokens.length} linkedCombatants=${linkedCount} ` +
        `version=${updated.combatState.version}`
    );

    broadcastAuthoritativeEvent(this.broadcaster, "tokens.synced", {
      eventId: randomUUID(),
      eventType: "tokens.synced",
      encounterId: sessionId,
      version: updated.combatState.version,
      payload: { tokens: updated.tokens },
      replaySafe: true
    });

    return { accepted: true, encounter: updated } as const;
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function sortByScore(combatants: InitiativeEntry[]): string[] {
  return [...combatants]
    .sort((a, b) => b.initiativeScore - a.initiativeScore)
    .map((c) => c.combatantId);
}

function resetBudgetForCombatant(
  repository: InMemoryEncounterRepository,
  sessionId: string,
  combatantId: string
): void {
  const token = repository
    .requireEncounter(sessionId)
    .tokens.find((t) => t.combatantId === combatantId);
  if (token) {
    repository.resetTokenBudget(sessionId, token.id);
  }
}
