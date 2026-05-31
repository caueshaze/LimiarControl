from __future__ import annotations

from app.models.combat import CombatState


class CombatEffectsCoreMixin:
    _DEFAULT_TURN_RESOURCES = {
        "action_used": False,
        "bonus_action_used": False,
        "reaction_used": False,
        "colossus_slayer_used": False,
        # Set when a Compelled Duel target passes its Wisdom save to move beyond
        # 9m; reset at turn start so the save is required again each turn.
        "compelled_duel_movement_free": False,
        "crown_of_madness_forced_attack_pending": False,
        "crown_of_madness_forced_attack_resolved": False,
        "crown_of_madness_forced_attack_skipped": False,
    }

    @classmethod
    def _get_participant_effects(cls, participant: dict) -> list[dict]:
        effects = participant.get("active_effects")
        return effects if isinstance(effects, list) else []

    @classmethod
    def _set_participant_effects(cls, participant: dict, effects: list[dict]) -> None:
        participant["active_effects"] = effects

    @classmethod
    def _sum_numeric_effects(cls, participant: dict, kind: str) -> int:
        total = 0
        for effect in cls._get_participant_effects(participant):
            if effect.get("kind") == kind and isinstance(effect.get("numeric_value"), int):
                total += effect["numeric_value"]
        return total

    @classmethod
    def _has_effect_kind(cls, participant: dict, kind: str) -> bool:
        return any(effect.get("kind") == kind for effect in cls._get_participant_effects(participant))

    @classmethod
    def _consume_first_effect(cls, participant: dict, kind: str) -> dict | None:
        effects = cls._get_participant_effects(participant)
        for index, effect in enumerate(effects):
            if effect.get("kind") == kind:
                removed = effects.pop(index)
                cls._set_participant_effects(participant, effects)
                return removed
        return None

    @classmethod
    def _consume_effect_ids(cls, participant: dict, effect_ids: list[str]) -> list[dict]:
        if not effect_ids:
            return []
        wanted = {eid for eid in effect_ids if isinstance(eid, str) and eid}
        if not wanted:
            return []
        effects = cls._get_participant_effects(participant)
        if not effects:
            return []
        removed: list[dict] = []
        kept: list[dict] = []
        for effect in effects:
            effect_id = effect.get("id")
            if isinstance(effect_id, str) and effect_id in wanted:
                removed.append(effect)
            else:
                kept.append(effect)
        if removed:
            cls._set_participant_effects(participant, kept)
        return removed

    @classmethod
    def _get_turn_resources(cls, participant: dict) -> dict:
        resources = participant.get("turn_resources")
        return resources if isinstance(resources, dict) else dict(cls._DEFAULT_TURN_RESOURCES)

    @classmethod
    def _reset_turn_resources(cls, participant: dict) -> None:
        participant["turn_resources"] = dict(cls._DEFAULT_TURN_RESOURCES)
        participant.pop("reaction_request", None)

    @classmethod
    def get_all_effects(cls, state: CombatState) -> list[dict]:
        result = []
        for participant in state.participants:
            for effect in cls._get_participant_effects(participant):
                result.append({**effect, "target_participant_id": participant["id"], "target_display_name": participant.get("display_name", "")})
        return result

    @classmethod
    async def _expire_effects_for_participant(
        cls,
        session_id: str,
        state: CombatState,
        participant_id: str,
        trigger: str,
    ) -> list[dict]:
        expired: list[dict] = []
        for participant in state.participants:
            effects = cls._get_participant_effects(participant)
            if not effects:
                continue
            keep: list[dict] = []
            for effect in effects:
                if effect.get("expires_on") == trigger and effect.get("expires_at_participant_id") == participant_id:
                    _meta = effect.get("metadata") or {}
                    if (
                        effect.get("duration_type") == "until_turn_end"
                        and _meta.get("source_spell_key") == "true_strike"
                        and _meta.get("available_from_next_turn") is True
                    ):
                        keep.append(effect)
                        continue
                    if effect.get("duration_type") == "rounds":
                        remaining = effect.get("remaining_rounds")
                        if isinstance(remaining, int) and remaining > 1:
                            effect["remaining_rounds"] = remaining - 1
                            keep.append(effect)
                            continue
                    expired.append({**effect, "target_participant_id": participant["id"], "target_display_name": participant.get("display_name", "")})
                else:
                    keep.append(effect)
            cls._set_participant_effects(participant, keep)
        return expired

    @classmethod
    def _effect_label(cls, effect: dict) -> str:
        display_label = effect.get("display_label")
        if isinstance(display_label, str) and display_label.strip():
            return display_label.strip()
        kind = effect.get("kind", "effect")
        if kind == "condition":
            return effect.get("condition_type") or "condition"
        value = effect.get("numeric_value")
        if isinstance(value, int):
            sign = "+" if value >= 0 else ""
            return f"{kind} ({sign}{value})"
        return kind
