"""
Action intent types for the pre-resolution spatial layer.

An intent represents *what the actor wants to do* before any spatial
or mechanical validation. It is produced at the beginning of an action
flow and handed to the CombatTargetingService for validation.

These types are intentionally simple dataclasses — they carry the
minimum information needed by the targeting layer to validate the
action spatially and return a TargetingResult.

Future integration with LimiarMap: the targeting service implementation
will receive these intents and may forward them (or a derived payload)
to the LimiarMap spatial authority before returning a TargetingResult.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeaponAttackIntent:
    """Intent for a weapon attack action (regular or wild-shape natural weapon).

    Fields:
        actor_ref_id        — ref_id of the attacking CombatParticipant
        actor_kind          — "player" or "entity"
        requested_target_ref_id — ref_id the actor is trying to hit
        weapon_item_id      — inventory item id (None for unarmed/wild-shape)
        weapon_canonical_key — base item canonical key, if already resolved
        is_wild_shape       — True when this is a Wild Shape natural weapon attack
    """
    session_id: str
    action_id: str
    actor_ref_id: str
    actor_kind: str
    requested_target_ref_id: str
    weapon_item_id: str | None = None
    weapon_canonical_key: str | None = None
    is_wild_shape: bool = False
    range_meters: int | float | None = None
    range_long_meters: int | float | None = None
    weapon_range_type: str | None = None
    has_reach: bool = False
    actor_effective_size: str | None = None
    # Final target-facing requirements resolved before validation.
    requires_sight: bool | None = None
    requires_effect: bool | None = None


@dataclass(frozen=True)
class SpellCastIntent:
    """Intent for a spell cast action.

    Fields:
        actor_ref_id        — ref_id of the casting CombatParticipant
        actor_kind          — "player" or "entity"
        requested_target_ref_id — ref_id the actor is targeting
        spell_canonical_key — canonical key of the spell being cast
        spell_mode          — resolved cast mode (spell_attack, saving_throw, etc.)
        target_type         — delivery type (self | touch | ranged | special)
        area_shape          — AoE shape if any (sphere | cone | cube | line | cylinder | None)
        range_meters        — spell range in meters from the catalog (None = not set)
    """
    session_id: str
    action_id: str
    actor_ref_id: str
    actor_kind: str
    requested_target_ref_id: str
    spell_canonical_key: str
    spell_mode: str
    target_type: str | None = None
    selection_type: str | None = None
    attack_type: str | None = None
    range_kind: str | None = None
    area_shape: str | None = None
    range_meters: int | None = None
    # Final target-facing requirements resolved from explicit spell metadata
    # or, for legacy records only, the temporary fallback helper.
    requires_sight: bool | None = None
    requires_effect: bool | None = None


@dataclass(frozen=True)
class AreaTargetingIntent:
    session_id: str
    action_id: str
    actor_ref_id: str
    actor_kind: str
    requested_target_ref_id: str | None
    spell_canonical_key: str
    spell_mode: str
    shape: str
    # AoE radius / dimension in meters (Control domain). Converted to cells at the map boundary.
    size_meters: int
    range_meters: int | None = None
    target_type: str | None = None
    selection_type: str | None = None
    origin_type: str | None = None
    target_anchor: str | None = None
    attack_type: str | None = None
    range_kind: str | None = None
    effect_timing: str | None = None
    area_shape: str | None = None
    origin_cell: dict[str, int] | None = None
    anchor_cell: dict[str, int] | None = None
    # Final point-facing requirements resolved from explicit spell metadata
    # or, for legacy records only, the temporary fallback helper.
    requires_sight: bool | None = None
    requires_effect: bool | None = None


# Union type for type hints that accept any action intent
ActionIntent = WeaponAttackIntent | SpellCastIntent | AreaTargetingIntent
