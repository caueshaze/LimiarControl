import { nextEncounterVersion } from "../validation/versioning";
export function advanceCombat(combatState) {
    if (combatState.status !== "active" || combatState.initiativeOrder.length === 0) {
        return combatState;
    }
    const nextTurnIndex = (combatState.turnIndex + 1) % combatState.initiativeOrder.length;
    const wrapped = nextTurnIndex === 0;
    return {
        ...combatState,
        turnIndex: nextTurnIndex,
        roundNumber: wrapped ? combatState.roundNumber + 1 : combatState.roundNumber,
        activeCombatantId: combatState.initiativeOrder[nextTurnIndex] ?? null,
        version: nextEncounterVersion(combatState.version)
    };
}
