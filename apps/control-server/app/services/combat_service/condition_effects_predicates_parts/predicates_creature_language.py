from __future__ import annotations

from .predicates_constants import PROTECTION_FROM_EVIL_AND_GOOD_CREATURE_TYPES


def _extract_languages(participant: dict) -> set[str]:
    raw = participant.get("languages") or (participant.get("metadata") or {}).get("languages")
    if isinstance(raw, list):
        return {str(lang).strip().lower() for lang in raw if lang}
    if isinstance(raw, str):
        return {raw.strip().lower()}
    return set()


def is_undead_participant(participant: dict) -> bool:
    raw = (
        participant.get("creature_type")
        or participant.get("creatureType")
        or (participant.get("metadata") or {}).get("creature_type")
        or (participant.get("metadata") or {}).get("creatureType")
    )
    return str(raw or "").strip().lower() == "undead"


def get_participant_creature_type(participant: dict) -> str | None:
    raw = (
        participant.get("creature_type")
        or participant.get("creatureType")
        or (participant.get("metadata") or {}).get("creature_type")
        or (participant.get("metadata") or {}).get("creatureType")
    )
    normalized = str(raw or "").strip().lower()
    return normalized or None


def is_protection_from_evil_and_good_type(participant: dict) -> bool:
    return get_participant_creature_type(participant) in PROTECTION_FROM_EVIL_AND_GOOD_CREATURE_TYPES


def has_condition_immunity_from_source(
    participant: dict,
    condition_type: str,
    source_participant: dict | None = None,
) -> bool:
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata") or {}
        if not metadata.get("condition_immunity"):
            continue
        immune_conditions = metadata.get("immune_conditions") or []
        if condition_type not in immune_conditions:
            continue
        source_creature_types = metadata.get("immune_conditions_from_creature_types")
        if isinstance(source_creature_types, list) and source_creature_types:
            if source_participant is None:
                continue
            source_type = get_participant_creature_type(source_participant)
            if source_type not in {str(t).lower() for t in source_creature_types}:
                continue
        return True
    return False


def target_cannot_understand_command(caster: dict, target: dict) -> bool:
    meta = target.get("metadata") or {}
    if meta.get("cannot_understand_command") is True:
        return True
    if meta.get("understands_languages") is False:
        return True
    caster_langs = _extract_languages(caster)
    target_langs = _extract_languages(target)
    if caster_langs and target_langs:
        return not bool(caster_langs & target_langs)
    return False


_TRUESIGHT_KEYS = frozenset({"truesightMeters", "truesight_meters", "truesight"})
_BLINDSIGHT_KEYS = frozenset({"blindsightMeters", "blindsight_meters", "blindsight"})


def _has_sight_bypass_sense(senses: dict) -> bool:
    return any(senses.get(k) for k in _TRUESIGHT_KEYS | _BLINDSIGHT_KEYS)


def attacker_ignores_incoming_attack_disadvantage_from_sight(attacker: dict) -> bool:
    senses = attacker.get("senses") or {}
    if isinstance(senses, dict):
        if _has_sight_bypass_sense(senses):
            return True
    elif isinstance(senses, list):
        for s in senses:
            if isinstance(s, dict) and s.get("type") in ("truesight", "blindsight"):
                return True
    meta_senses = (attacker.get("metadata") or {}).get("senses") or {}
    if isinstance(meta_senses, dict) and _has_sight_bypass_sense(meta_senses):
        return True
    if attacker.get("does_not_rely_on_sight") is True:
        return True
    return False
