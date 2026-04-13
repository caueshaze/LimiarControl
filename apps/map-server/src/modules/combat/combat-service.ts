import { advanceCombat } from "@limiarmap/tactical-engine";
import type { InMemoryEncounterRepository } from "../encounters/encounter-repository";

export class CombatService {
  constructor(private readonly repository: InMemoryEncounterRepository) {}

  advance(sessionId: string, actionId: string, requestedBy: string) {
    const encounter = this.repository.requireEncounter(sessionId);
    if (requestedBy !== "limiarControl") {
      return { accepted: false, rejectionReason: "unauthorized_action", encounter };
    }

    if (encounter.actionTracker.has(actionId)) {
      return { accepted: false, rejectionReason: "duplicate_action", encounter };
    }

    encounter.actionTracker.record(actionId);
    encounter.combatState = advanceCombat(encounter.combatState);
    this.repository.updateCombatState(sessionId, encounter.combatState);

    const newActiveCombatantId = encounter.combatState.activeCombatantId;
    if (newActiveCombatantId) {
      const activeToken = this.repository
        .requireEncounter(sessionId)
        .tokens.find((t) => t.combatantId === newActiveCombatantId);
      if (activeToken) {
        this.repository.resetTokenBudget(sessionId, activeToken.id);
      }
    }

    return { accepted: true, encounter: this.repository.requireEncounter(sessionId) };
  }
}
