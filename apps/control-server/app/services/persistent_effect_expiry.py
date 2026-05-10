from __future__ import annotations


def prune_expired_persisted_effects(
    effects: list[dict],
    game_time_seconds: int,
) -> list[dict]:
    remaining: list[dict] = []
    for effect in effects:
        if not isinstance(effect, dict):
            remaining.append(effect)
            continue
        if effect.get("duration_type") != "timed":
            remaining.append(effect)
            continue
        expires_at = effect.get("expires_at_game_time_seconds")
        if not isinstance(expires_at, int):
            continue
        if expires_at <= game_time_seconds:
            continue
        remaining.append(effect)
    return remaining


def prune_expired_persisted_effects_from_state(
    state_json: dict | None,
    game_time_seconds: int,
) -> dict:
    data = dict(state_json or {})
    effects = data.get("active_spell_effects")
    if not isinstance(effects, list):
        return data

    remaining = prune_expired_persisted_effects(effects, game_time_seconds)
    if remaining:
        data["active_spell_effects"] = remaining
    else:
        data.pop("active_spell_effects", None)
    return data
