"""Spell automation metadata — single authoritative source.

This module computes combat-facing spell metadata from:
  1. Catalog fields (resolution_type, area_shape, saving_throw, damage_dice, etc.)
  2. The special-handler registry in spell_automation.py

Frontend and backend both consume this module's output.  Frontend must
NOT maintain a second behavioral registry; any remaining frontend-side
data should be presentation-only (icons, labels, i18n).

Authority model:
  - CampaignSpell is the mechanical source of truth during campaign play.
  - BaseSpell is the fallback when no campaign override exists.
  - character_sheet.spellcasting.spells[] stores selection state
    (known / prepared / learned), NOT mechanical authority.
  - At cast time, _get_spell_catalog_entry_for_session() resolves the
    authoritative catalog entry.  _resolve_player_spell_context() then
    builds the full spell context from that catalog entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .spell_automation import SpellAutomationSpec
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


# Spell execution pipeline classification.
SpellAutomationMode = Literal[
    "generic_direct",
    "generic_area",
    "special_handler",
]


@dataclass(frozen=True)
class SpellAutomationMetadata:
    automation_mode: SpellAutomationMode
    default_spell_mode: str | None
    requires_effect_inputs: bool
    requires_map: bool
    handler_key: str | None

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "automationMode": self.automation_mode,
            "defaultSpellMode": self.default_spell_mode,
            "requiresEffectInputs": self.requires_effect_inputs,
            "requiresMap": self.requires_map,
            "handlerKey": self.handler_key,
        }


_RESOLUTION_TYPE_TO_SPELL_MODE: dict[str, str] = {
    "damage": "direct_damage",
    "spell_attack": "spell_attack",
    "saving_throw": "saving_throw",
    "heal": "heal",
    "automatic": "direct_damage",
    "utility": "utility",
    "buff": "utility",
    "control": "saving_throw",
    "debuff": "saving_throw",
}

_AREA_SHAPES = frozenset({"cone", "cube", "sphere", "line", "cylinder"})


def _normalize_lookup(value: object) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def resolve_spell_automation_metadata(
    *,
    canonical_key: str | None = None,
    resolution_type: str | None = None,
    area_shape: str | None = None,
    saving_throw: str | None = None,
    damage_dice: str | None = None,
    heal_dice: str | None = None,
    attack_type: str | None = None,
    effect_timing: str | None = None,
    automation_registry: dict[str, SpellAutomationSpec] | None = None,
) -> SpellAutomationMetadata:
    """Compute automation metadata from catalog fields and the handler registry.

    This is the single authoritative function for deriving spell automation
    metadata.  Both backend pipelines and API serialization call this.
    """
    normalized_key = _normalize_lookup(canonical_key)

    handler_spec: SpellAutomationSpec | None = None
    if automation_registry is not None and normalized_key:
        handler_spec = automation_registry.get(normalized_key)

    is_area = _normalize_lookup(area_shape) in _AREA_SHAPES

    if handler_spec is not None:
        return SpellAutomationMetadata(
            automation_mode="special_handler",
            default_spell_mode=handler_spec.default_mode,
            requires_effect_inputs=handler_spec.requires_effect_payload,
            requires_map=is_area,
            handler_key=handler_spec.handler_name or None,
        )

    if attack_type in ("melee_spell", "ranged_spell"):
        default_spell_mode = "spell_attack"
    elif effect_timing in ("persistent", "triggered"):
        default_spell_mode = "utility"
    else:
        default_spell_mode = _RESOLUTION_TYPE_TO_SPELL_MODE.get(
            resolution_type or "",
        )

    has_effect_dice = bool(
        (damage_dice and damage_dice.strip()) or (heal_dice and heal_dice.strip()),
    )
    requires_effect = (
        default_spell_mode != "utility" if default_spell_mode else has_effect_dice
    )

    return SpellAutomationMetadata(
        automation_mode="generic_area" if is_area else "generic_direct",
        default_spell_mode=default_spell_mode,
        requires_effect_inputs=requires_effect,
        requires_map=is_area,
        handler_key=None,
    )


def resolve_spell_automation_metadata_from_catalog(
    catalog_entry: Any,
    *,
    automation_registry: dict[str, SpellAutomationSpec] | None = None,
) -> SpellAutomationMetadata:
    """Convenience wrapper that reads fields from a BaseSpell/CampaignSpell model."""
    semantics = resolve_spell_targeting_semantics(catalog_entry)
    return resolve_spell_automation_metadata(
        canonical_key=getattr(catalog_entry, "canonical_key", None),
        resolution_type=getattr(catalog_entry, "resolution_type", None),
        area_shape=getattr(catalog_entry, "area_shape", None),
        saving_throw=getattr(catalog_entry, "saving_throw", None),
        damage_dice=getattr(catalog_entry, "damage_dice", None),
        heal_dice=getattr(catalog_entry, "heal_dice", None),
        attack_type=semantics.attack_type,
        effect_timing=semantics.effect_timing,
        automation_registry=automation_registry,
    )
