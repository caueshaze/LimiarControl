from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SpellTargetingSemantics:
    selection_type: str
    origin_type: str
    target_anchor: str
    attack_type: str
    range_kind: str
    effect_timing: str

    def to_dict(self) -> dict[str, str]:
        return {
            "selection_type": self.selection_type,
            "origin_type": self.origin_type,
            "target_anchor": self.target_anchor,
            "attack_type": self.attack_type,
            "range_kind": self.range_kind,
            "effect_timing": self.effect_timing,
        }


_EXPLICIT_OVERRIDES: dict[str, SpellTargetingSemantics] = {
    "fire_bolt": SpellTargetingSemantics("creature_or_object", "caster", "selected_target", "ranged_spell", "distance", "immediate"),
    "eldritch_blast": SpellTargetingSemantics("creature", "caster", "selected_target", "ranged_spell", "distance", "immediate"),
    "thorn_whip": SpellTargetingSemantics("creature", "caster", "selected_target", "melee_spell", "distance", "immediate"),
    "fireball": SpellTargetingSemantics("point", "selected_point", "selected_point", "none", "distance", "immediate"),
    "fog_cloud": SpellTargetingSemantics("point", "selected_point", "selected_point", "none", "distance", "persistent"),
    "spike_growth": SpellTargetingSemantics("point", "selected_point", "selected_point", "none", "distance", "persistent"),
    "burning_hands": SpellTargetingSemantics("direction", "caster", "caster", "none", "self", "immediate"),
    "thunderwave": SpellTargetingSemantics("direction", "caster", "caster", "none", "self", "immediate"),
    "cure_wounds": SpellTargetingSemantics("creature", "caster", "selected_target", "none", "touch", "immediate"),
    "healing_word": SpellTargetingSemantics("creature", "caster", "selected_target", "none", "distance", "immediate"),
    "sacred_flame": SpellTargetingSemantics("creature", "caster", "selected_target", "none", "distance", "immediate"),
    "magic_missile": SpellTargetingSemantics("creature", "caster", "selected_target", "none", "distance", "immediate"),
    "shield": SpellTargetingSemantics("none", "caster", "caster", "none", "self", "triggered"),
    "detect_magic": SpellTargetingSemantics("self", "caster", "caster", "none", "self", "persistent"),
    "hunters_mark": SpellTargetingSemantics("creature", "caster", "selected_target", "none", "distance", "persistent"),
    "hex": SpellTargetingSemantics("creature", "caster", "selected_target", "none", "distance", "persistent"),
    "ensnaring_strike": SpellTargetingSemantics("none", "caster", "trigger_target", "none", "self", "triggered"),
    "hail_of_thorns": SpellTargetingSemantics("none", "caster", "trigger_target", "none", "self", "triggered"),
    "light": SpellTargetingSemantics("object", "caster", "selected_target", "none", "touch", "persistent"),
    "guidance": SpellTargetingSemantics("creature", "caster", "selected_target", "none", "touch", "persistent"),
    "longstrider": SpellTargetingSemantics("creature", "caster", "selected_target", "none", "touch", "persistent"),
    "goodberry": SpellTargetingSemantics("none", "caster", "caster", "none", "self", "immediate"),
    "spiritual_weapon": SpellTargetingSemantics("point", "caster", "selected_point", "melee_spell", "distance", "persistent"),
    "mage_hand": SpellTargetingSemantics("point", "caster", "selected_point", "none", "distance", "persistent"),
    "speak_with_animals": SpellTargetingSemantics("self", "caster", "caster", "none", "self", "persistent"),
    "pass_without_trace": SpellTargetingSemantics("self", "caster", "caster", "none", "self", "persistent"),
    "disguise_self": SpellTargetingSemantics("self", "caster", "caster", "none", "self", "persistent"),
    "minor_illusion": SpellTargetingSemantics("point", "selected_point", "selected_point", "none", "distance", "persistent"),
    "floating_disk": SpellTargetingSemantics("point", "selected_point", "selected_point", "none", "distance", "persistent"),
}


def _read(source: Mapping[str, Any] | object, *names: str) -> Any:
    if isinstance(source, Mapping):
        for name in names:
            value = source.get(name)
            if value is not None:
                return value
        return None
    for name in names:
        value = getattr(source, name, None)
        if value is not None:
            return value
    return None


def _norm(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    return text or None


def _explicit_semantics(source: Mapping[str, Any] | object) -> SpellTargetingSemantics | None:
    selection_type = _norm(_read(source, "selection_type", "selectionType"))
    origin_type = _norm(_read(source, "origin_type", "originType"))
    target_anchor = _norm(_read(source, "target_anchor", "targetAnchor"))
    attack_type = _norm(_read(source, "attack_type", "attackType"))
    range_kind = _norm(_read(source, "range_kind", "rangeKind"))
    effect_timing = _norm(_read(source, "effect_timing", "effectTiming"))
    if all((selection_type, origin_type, target_anchor, attack_type, range_kind, effect_timing)):
        return SpellTargetingSemantics(
            selection_type=selection_type or "creature",
            origin_type=origin_type or "caster",
            target_anchor=target_anchor or "selected_target",
            attack_type=attack_type or "none",
            range_kind=range_kind or "distance",
            effect_timing=effect_timing or "immediate",
        )
    return None


def _legacy_backfill(source: Mapping[str, Any] | object) -> SpellTargetingSemantics:
    target_type = _norm(_read(source, "target_type", "targetType"))
    area_shape = _norm(_read(source, "area_shape", "areaShape"))
    range_meters = _read(source, "range_meters", "rangeMeters")

    if target_type == "self":
        return SpellTargetingSemantics("self", "caster", "caster", "none", "self", "immediate")
    if target_type == "touch":
        return SpellTargetingSemantics("creature", "caster", "selected_target", "none", "touch", "immediate")
    if target_type == "ranged" and area_shape in {"sphere", "cube", "cylinder"}:
        return SpellTargetingSemantics("point", "selected_point", "selected_point", "none", "distance", "immediate")
    if target_type == "ranged" and area_shape == "cone" and range_meters == 0:
        return SpellTargetingSemantics("direction", "caster", "caster", "none", "self", "immediate")
    if target_type == "ranged":
        return SpellTargetingSemantics("creature", "caster", "selected_target", "none", "distance", "immediate")
    return SpellTargetingSemantics("creature", "caster", "selected_target", "none", "distance", "immediate")


def resolve_spell_targeting_semantics(
    source: Mapping[str, Any] | object,
    *,
    apply_overrides: bool = True,
) -> SpellTargetingSemantics:
    canonical_key = _norm(_read(source, "canonical_key", "canonicalKey", "spell_canonical_key", "spellCanonicalKey"))
    if apply_overrides and canonical_key in _EXPLICIT_OVERRIDES:
        return _EXPLICIT_OVERRIDES[canonical_key]
    return _explicit_semantics(source) or _legacy_backfill(source)


def explicit_spell_targeting_overrides() -> dict[str, SpellTargetingSemantics]:
    return dict(_EXPLICIT_OVERRIDES)
