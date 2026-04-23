from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

_MISSING = object()


@dataclass(frozen=True)
class TargetingRequirements:
    """Final LoS/LoE requirements used by the targeting pipeline.

    target* flags apply to creature/entity targeting.
    point* flags apply to point-anchor targeting such as AoE origin selection.
    """

    requires_target_sight: bool = False
    requires_target_effect: bool = False
    requires_point_sight: bool = False
    requires_point_effect: bool = False


def _normalize_lookup(value: object) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def _read_optional_value(source: Mapping[str, Any] | object, *names: str) -> object:
    if isinstance(source, Mapping):
        for name in names:
            if name in source:
                value = source[name]
                if value is not None:
                    return value
        return _MISSING

    for name in names:
        value = getattr(source, name, _MISSING)
        if value is not _MISSING and value is not None:
            return value
    return _MISSING


def _read_optional_bool(
    source: Mapping[str, Any] | object, *names: str
) -> bool | object:
    value = _read_optional_value(source, *names)
    return value if isinstance(value, bool) else _MISSING


def _resolve_flag(
    source: Mapping[str, Any] | object,
    *,
    names: tuple[str, ...],
    fallback: bool,
) -> bool:
    explicit = _read_optional_bool(source, *names)
    if isinstance(explicit, bool):
        return explicit
    return fallback


def resolve_weapon_targeting_requirements(
    *,
    requires_target_sight: bool | None = None,
    requires_target_effect: bool | None = None,
    requires_point_sight: bool | None = None,
    requires_point_effect: bool | None = None,
) -> TargetingRequirements:
    """Weapon attacks use explicit family rules in the current combat model.

    All supported weapon attacks currently require sight and effect to the
    creature target. Point targeting is not used for weapons yet.
    """

    return TargetingRequirements(
        requires_target_sight=True
        if requires_target_sight is None
        else requires_target_sight,
        requires_target_effect=True
        if requires_target_effect is None
        else requires_target_effect,
        requires_point_sight=False
        if requires_point_sight is None
        else requires_point_sight,
        requires_point_effect=False
        if requires_point_effect is None
        else requires_point_effect,
    )


def resolve_spell_targeting_requirements(
    source: Mapping[str, Any] | object,
    *,
    spell_mode: object | None = None,
) -> TargetingRequirements:
    """Resolve final targeting requirements from spell metadata.

    Explicit metadata on the spell record is authoritative when present.

    Legacy compatibility path (retained for pre-migration-0051 records):
    - All base spells in the seed catalog carry explicit fields (migration 0051).
    - Campaign spells created after migration 0051 also carry explicit fields.
    - The fallback heuristics below apply only to campaign spells that were
      created before 0051 and have never been updated since.  They must not be
      extended.  When the intent also carries pre-resolved requirements from
      spell_context, those values are forwarded through and override the
      heuristic defaults.
    """

    target_type = _normalize_lookup(
        _read_optional_value(source, "target_type", "targetType")
    )
    normalized_spell_mode = _normalize_lookup(
        spell_mode
        if spell_mode is not None
        else _read_optional_value(source, "spell_mode", "spellMode")
    )

    return TargetingRequirements(
        requires_target_sight=_resolve_flag(
            source,
            names=("requires_target_sight", "requiresTargetSight"),
            fallback=target_type == "ranged" or normalized_spell_mode == "spell_attack",
        ),
        requires_target_effect=_resolve_flag(
            source,
            names=("requires_target_effect", "requiresTargetEffect"),
            fallback=target_type != "self" or normalized_spell_mode != "utility",
        ),
        requires_point_sight=_resolve_flag(
            source,
            names=("requires_point_sight", "requiresPointSight"),
            fallback=False,
        ),
        requires_point_effect=_resolve_flag(
            source,
            names=("requires_point_effect", "requiresPointEffect"),
            fallback=True,
        ),
    )
