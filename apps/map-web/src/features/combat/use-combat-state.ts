import { useEncounterSnapshot } from "../../services/session-store";

export function getCombatState() {
  return useEncounterSnapshot()?.combatState;
}
