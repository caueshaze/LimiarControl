from __future__ import annotations


def should_prune_timed_effect(
    effect: dict,
    game_time_seconds: int,
) -> bool:
    if effect.get("duration_type") != "timed":
        return False
    expires_at = effect.get("expires_at_game_time_seconds")
    if not isinstance(expires_at, int):
        return True
    return expires_at <= game_time_seconds


def prune_expired_timed_effects(
    effects: list[dict],
    game_time_seconds: int,
) -> list[dict]:
    remaining: list[dict] = []
    for effect in effects:
        if not isinstance(effect, dict):
            remaining.append(effect)
            continue
        if should_prune_timed_effect(effect, game_time_seconds):
            continue
        remaining.append(effect)
    return remaining


def prune_expired_persisted_effects(
    effects: list[dict],
    game_time_seconds: int,
) -> list[dict]:
    return prune_expired_timed_effects(effects, game_time_seconds)


def prune_expired_persisted_effects_from_state(
    state_json: dict | None,
    game_time_seconds: int,
) -> dict:
    data = dict(state_json or {})
    effects = data.get("active_spell_effects")
    if not isinstance(effects, list):
        return data

    remaining = prune_expired_timed_effects(effects, game_time_seconds)
    if remaining:
        data["active_spell_effects"] = remaining
    else:
        data.pop("active_spell_effects", None)
    return data
