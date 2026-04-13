export function canTokenAct(combatState, combatantId) {
    if (combatState.status !== "active") {
        return true;
    }
    return combatState.activeCombatantId === combatantId;
}
