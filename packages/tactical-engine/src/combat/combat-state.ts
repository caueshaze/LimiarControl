import type { CombatState } from "@limiarmap/shared-contracts";

export function canTokenAct(combatState: CombatState, combatantId?: string): boolean {
  if (combatState.status !== "active") {
    return true;
  }

  return combatState.activeCombatantId === combatantId;
}
