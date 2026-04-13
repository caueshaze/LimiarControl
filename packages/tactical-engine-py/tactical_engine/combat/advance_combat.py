from shared_contracts import CombatState
from ..validation.versioning import next_encounter_version


def advance_combat(combat_state: CombatState) -> CombatState:
    if combat_state.status != "active" or not combat_state.initiative_order:
        return combat_state

    next_turn_index = (combat_state.turn_index + 1) % len(combat_state.initiative_order)
    wrapped = next_turn_index == 0

    return combat_state.model_copy(
        update={
            "turn_index": next_turn_index,
            "round_number": combat_state.round_number + 1 if wrapped else combat_state.round_number,
            "active_combatant_id": combat_state.initiative_order[next_turn_index],
            "version": next_encounter_version(combat_state.version),
        }
    )
