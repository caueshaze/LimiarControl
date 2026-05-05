from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, Enum as SAEnum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.campaign import SystemType


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class SpellSchool(str, Enum):
    ABJURATION = "abjuration"
    CONJURATION = "conjuration"
    DIVINATION = "divination"
    ENCHANTMENT = "enchantment"
    EVOCATION = "evocation"
    ILLUSION = "illusion"
    NECROMANCY = "necromancy"
    TRANSMUTATION = "transmutation"


class CastingTimeType(str, Enum):
    ACTION = "action"
    BONUS_ACTION = "bonus_action"
    REACTION = "reaction"
    MINUTE_1 = "1_minute"
    MINUTES_10 = "10_minutes"
    HOUR_1 = "1_hour"
    HOURS_8 = "8_hours"
    HOURS_12 = "12_hours"
    HOURS_24 = "24_hours"
    SPECIAL = "special"


class TargetType(str, Enum):
    """Legacy delivery type retained for catalog backfill compatibility."""

    SELF = "self"
    TOUCH = "touch"
    RANGED = "ranged"
    SPECIAL = "special"


class AreaShape(str, Enum):
    """Area-of-effect geometry. ``None`` means single-target."""

    CONE = "cone"
    CUBE = "cube"
    SPHERE = "sphere"
    LINE = "line"
    CYLINDER = "cylinder"


class SpellSelectionType(str, Enum):
    NONE = "none"
    SELF = "self"
    CREATURE = "creature"
    OBJECT = "object"
    CREATURE_OR_OBJECT = "creature_or_object"
    POINT = "point"
    DIRECTION = "direction"


class SpellOriginType(str, Enum):
    CASTER = "caster"
    SELECTED_TARGET = "selected_target"
    SELECTED_POINT = "selected_point"


class SpellTargetAnchor(str, Enum):
    CASTER = "caster"
    SELECTED_TARGET = "selected_target"
    SELECTED_POINT = "selected_point"
    TRIGGER_TARGET = "trigger_target"


class SpellAttackType(str, Enum):
    NONE = "none"
    MELEE_SPELL = "melee_spell"
    RANGED_SPELL = "ranged_spell"


class SpellRangeKind(str, Enum):
    SELF = "self"
    TOUCH = "touch"
    DISTANCE = "distance"


class SpellEffectTiming(str, Enum):
    IMMEDIATE = "immediate"
    PERSISTENT = "persistent"
    TRIGGERED = "triggered"


class ResolutionType(str, Enum):
    DAMAGE = "damage"
    HEAL = "heal"
    BUFF = "buff"
    DEBUFF = "debuff"
    CONTROL = "control"
    UTILITY = "utility"


class UpcastMode(str, Enum):
    EXTRA_DAMAGE_DICE = "extra_damage_dice"
    EXTRA_HEAL_DICE = "extra_heal_dice"
    FLAT_BONUS = "flat_bonus"
    ADDITIONAL_EFFECT_INSTANCES = "additional_effect_instances"
    ADDITIONAL_TARGETS = "additional_targets"
    DURATION_SCALING = "duration_scaling"
    EFFECT_SCALING = "effect_scaling"
    EXTRA_EFFECT = "extra_effect"
    NONE = "none"  # legacy sentinel only


class SpellSource(str, Enum):
    ADMIN_PANEL = "admin_panel"
    SEED_JSON_BOOTSTRAP = "seed_json_bootstrap"


class BaseSpell(SQLModel, table=True):
    __tablename__ = "base_spell"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint(
            "system",
            "canonical_key",
            name="uq_base_spell_system_canonical_key",
        ),
    )

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    system: SystemType = Field(
        sa_column=Column(
            SAEnum(SystemType, name="systemtype", create_type=False),
            nullable=False,
            index=True,
        )
    )
    canonical_key: str = Field(
        sa_column=Column(String, nullable=False, index=True)
    )

    # --- Identity (editorial) ---
    name_en: str
    name_pt: Optional[str] = None
    description_en: str = Field(sa_column=Column(Text, nullable=False))
    description_pt: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    level: int = Field(
        sa_column=Column(Integer, nullable=False, index=True)
    )
    school: SpellSchool = Field(
        sa_column=Column(
            SAEnum(
                SpellSchool,
                name="spellschool",
                values_callable=_enum_values,
            ),
            nullable=False,
            index=True,
        )
    )
    classes_json: Optional[list[str]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )

    # --- Casting (mechanical) ---
    casting_time_type: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    casting_time: Optional[str] = None  # editorial text, e.g. "1 action"
    range_meters: Optional[int] = None
    range_text: Optional[str] = None  # editorial only
    target_type: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    max_targets: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    selection_type: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    origin_type: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    target_anchor: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    attack_type: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    range_kind: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    effect_timing: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    area_shape: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    radius_meters: Optional[float] = Field(
        default=None,
        sa_column=Column(Float, nullable=True),
    )  # AoE radius in meters — sphere, cylinder
    length_meters: Optional[float] = Field(
        default=None,
        sa_column=Column(Float, nullable=True),
    )  # AoE length in meters — cone, line
    side_meters: Optional[float] = Field(
        default=None,
        sa_column=Column(Float, nullable=True),
    )  # AoE side length in meters — cube
    duration: Optional[str] = None  # editorial text
    components_json: Optional[list[str]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    material_component_text: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    concentration: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
    )
    ritual: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
    )
    out_of_combat_castable: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
    )
    out_of_combat_target: str = Field(
        default="self",
        sa_column=Column(String(20), nullable=False, server_default="self"),
    )

    # --- Resolution (mechanical) ---
    resolution_type: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    saving_throw: Optional[str] = None  # enum: STR/DEX/CON/INT/WIS/CHA
    save_success_outcome: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    # Governs whether cover modifies the effective DC for this saving throw.
    # "physical" → cover applies (spatial/blast effects).
    # "none"     → cover does not apply (mental, control, etc.).
    # NULL       → fallback heuristic used during migration.
    cover_applies_to_save: Optional[str] = Field(
        default=None, sa_column=Column(String, nullable=True)
    )

    # --- Effect (mechanical) ---
    damage_dice: Optional[str] = None  # e.g. "1d8", "2d6+3"
    damage_type: Optional[str] = None  # enum: Acid/Fire/etc
    heal_dice: Optional[str] = None  # e.g. "1d8+3"
    effects_json: Optional[list[dict]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    on_end_effects_json: Optional[list[dict]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    variants_json: Optional[list[dict]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    persistent_area_json: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )

    # --- Targeting requirements (mechanical) ---
    requires_target_sight: Optional[bool] = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
    )
    requires_target_effect: Optional[bool] = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
    )
    requires_point_sight: Optional[bool] = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
    )
    requires_point_effect: Optional[bool] = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
    )

    # --- Upcast (mechanical) ---
    upcast_json: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    upcast_mode: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    upcast_value: Optional[str] = None  # e.g. "1d8" for add_dice
    cantrip_scaling_json: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )

    # --- Metadata ---
    source: Optional[str] = None
    source_ref: Optional[str] = None
    is_srd: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default="true"),
    )


class BaseSpellAlias(SQLModel, table=True):
    __tablename__ = "base_spell_alias"  # type: ignore[assignment]

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    base_spell_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("base_spell.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    alias: str = Field(
        sa_column=Column(String, nullable=False, index=True)
    )
    locale: Optional[str] = None
    alias_type: Optional[str] = None
