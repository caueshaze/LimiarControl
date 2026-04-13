from typing import Optional
from shared_contracts import CombatState


def can_token_act(combat_state: CombatState, combatant_id: Optional[str] = None) -> bool:
    if combat_state.status != "active":
        return True
    return combat_state.active_combatant_id == combatant_id
