from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True)
class SpellEffectBuildContext:
    spell_key: str
    spell_name: str
    game_time_seconds: int
    duration_seconds: int
    concentration: bool
    concentration_group: str | None
    source_participant_id: str | None
    owner_participant_id: str | None
    created_by_participant_id: str | None
    context_origin: str
    caster_user_id: str | None = None
    target_user_id: str | None = None
    selected_variant_key: str | None = None
    selected_variant_label: str | None = None
    created_out_of_combat: bool = False
    extra_metadata: dict = field(default_factory=dict)


def _build_base_metadata(ctx: SpellEffectBuildContext) -> dict:
    metadata: dict = {
        "source_spell_key": ctx.spell_key,
        "source_spell_name": ctx.spell_name,
        "selected_variant_key": ctx.selected_variant_key,
        "selected_variant_label": ctx.selected_variant_label,
        "context_origin": ctx.context_origin,
        "concentration": ctx.concentration,
        "concentration_group": ctx.concentration_group,
        "source_participant_id": ctx.source_participant_id,
        "owner_participant_id": ctx.owner_participant_id,
        "created_by_participant_id": ctx.created_by_participant_id,
        "mechanical": True,
        "utility": ctx.spell_key,
    }
    if ctx.caster_user_id is not None:
        metadata["caster_player_user_id"] = ctx.caster_user_id
    if ctx.target_user_id is not None:
        metadata["target_player_user_id"] = ctx.target_user_id
    if ctx.created_out_of_combat:
        metadata["created_out_of_combat"] = True
    metadata.update(ctx.extra_metadata or {})
    return metadata


def _build_timed_spell_effect_base(
    ctx: SpellEffectBuildContext,
    *,
    metadata: dict,
) -> dict:
    return {
        "id": str(uuid4()),
        "source_participant_id": ctx.source_participant_id,
        "kind": "spell_effect",
        "condition_type": None,
        "numeric_value": None,
        "duration_type": "timed",
        "remaining_rounds": None,
        "expires_on": None,
        "expires_at_participant_id": None,
        "created_at_game_time_seconds": ctx.game_time_seconds,
        "expires_at_game_time_seconds": ctx.game_time_seconds + ctx.duration_seconds,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata,
        "display_label": ctx.spell_name,
    }


def build_barkskin_effect(ctx: SpellEffectBuildContext) -> dict:
    metadata = _build_base_metadata(ctx)
    metadata.update(
        {
            "defense_modifier": True,
            "armor_class_floor": 16,
            "ac_floor": 16,
            "sets_minimum_ac": True,
            "stacks_as_floor": True,
            "is_flat_bonus": False,
            "duration_seconds": ctx.duration_seconds,
        }
    )
    return _build_timed_spell_effect_base(ctx, metadata=metadata)


def build_blur_effect(ctx: SpellEffectBuildContext) -> dict:
    metadata = _build_base_metadata(ctx)
    metadata.update(
        {
            "defense_modifier": True,
            "illusion_defense": True,
            "attack_disadvantage_against_target": True,
            "applies_to_attack_rolls_against_owner": True,
            "grants_ac_bonus": False,
            "armor_class_bonus": 0,
            "grants_resistance": False,
            "duration_seconds": ctx.duration_seconds,
            "declarative_effect": {
                "type": "attack_disadvantage_against_target",
                "params": {
                    "mode": "disadvantage",
                    "roll_types": ["attack"],
                    "source": "blur",
                    "requires_attacker_sight": True,
                    "ignored_by_senses": ["blindsight", "truesight"],
                    "consume_on_apply": False,
                },
            },
        }
    )
    return _build_timed_spell_effect_base(ctx, metadata=metadata)


def build_protection_from_evil_and_good_effect(ctx: SpellEffectBuildContext) -> dict:
    protected_types = sorted(
        {"aberration", "celestial", "elemental", "fey", "fiend", "undead"}
    )
    immune_conditions = sorted({"charmed", "frightened"})
    metadata = _build_base_metadata(ctx)
    metadata.update(
        {
            "defense_modifier": True,
            "abjuration_protection": True,
            "protected_creature_types": protected_types,
            "attack_disadvantage_against_target": True,
            "condition_immunity": True,
            "immune_conditions": immune_conditions,
            "immune_conditions_from_creature_types": protected_types,
            "saving_throw_advantage_against_creature_types": True,
            "saving_throw_advantage_creature_types": protected_types,
            "grants_ac_bonus": False,
            "armor_class_bonus": 0,
            "grants_resistance": False,
            "requires_concentration": True,
            "duration_seconds": ctx.duration_seconds,
            "declarative_save_effect": {
                "type": "saving_throw_advantage_against_creature_types",
                "params": {
                    "mode": "advantage",
                    "source": "protection_from_evil_and_good",
                    "source_creature_types": protected_types,
                    "roll_types": ["saving_throw"],
                    "consume_on_apply": False,
                },
            },
            "declarative_effect": {
                "type": "attack_disadvantage_against_target",
                "params": {
                    "mode": "disadvantage",
                    "roll_types": ["attack"],
                    "source": "protection_from_evil_and_good",
                    "requires_attacker_creature_type": protected_types,
                    "consume_on_apply": False,
                },
            },
        }
    )
    return _build_timed_spell_effect_base(ctx, metadata=metadata)
