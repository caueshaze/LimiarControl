from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, Enum as SAEnum, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.campaign import SystemType


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class BaseItemKind(str, Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    GEAR = "gear"
    TOOL = "tool"
    CONSUMABLE = "consumable"
    FOCUS = "focus"
    AMMO = "ammo"
    PACK = "pack"


class BaseItemCostUnit(str, Enum):
    CP = "cp"
    SP = "sp"
    EP = "ep"
    GP = "gp"
    PP = "pp"


class BaseItemEquipmentCategory(str, Enum):
    ADVENTURING_PACK = "adventuring_pack"
    AMMUNITION = "ammunition"
    BOOK = "book"
    CLOTHING = "clothing"
    CONSUMABLE_SUPPLY = "consumable_supply"
    CONTAINER = "container"
    DOCUMENT = "document"
    GAMING_SET = "gaming_set"
    INSIGNIA = "insignia"
    JEWELRY = "jewelry"
    MEMENTO = "memento"
    MUSICAL_INSTRUMENT = "musical_instrument"
    PET = "pet"
    ROPE = "rope"
    SAILING_GEAR = "sailing_gear"
    SPELLCASTING_FOCUS = "spellcasting_focus"
    SPELLCASTING_GEAR = "spellcasting_gear"
    SUPPLIES = "supplies"
    TOOLS = "tools"
    TROPHY = "trophy"
    UTILITY_TOOL = "utility_tool"
    VEHICLE_PROFICIENCY = "vehicle_proficiency"
    WRITING_SUPPLY = "writing_supply"


class BaseItemWeaponCategory(str, Enum):
    SIMPLE = "simple"
    MARTIAL = "martial"


class BaseItemWeaponRangeType(str, Enum):
    MELEE = "melee"
    RANGED = "ranged"


class BaseItemArmorCategory(str, Enum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    SHIELD = "shield"


class BaseItemDamageType(str, Enum):
    ACID = "acid"
    BLUDGEONING = "bludgeoning"
    COLD = "cold"
    FIRE = "fire"
    FORCE = "force"
    LIGHTNING = "lightning"
    NECROTIC = "necrotic"
    PIERCING = "piercing"
    POISON = "poison"
    PSYCHIC = "psychic"
    RADIANT = "radiant"
    SLASHING = "slashing"
    THUNDER = "thunder"


class BaseItemDexBonusRule(str, Enum):
    FULL = "full"
    MAX_2 = "max_2"
    NONE = "none"


class BaseItemSource(str, Enum):
    ADMIN_PANEL = "admin_panel"
    SEED_JSON_BOOTSTRAP = "seed_json_bootstrap"


class BaseItemProperty(str, Enum):
    AMMUNITION = "ammunition"
    FINESSE = "finesse"
    HEAVY = "heavy"
    LIGHT = "light"
    LOADING = "loading"
    RANGE = "range"
    REACH = "reach"
    SPECIAL = "special"
    THROWN = "thrown"
    TWO_HANDED = "two_handed"
    VERSATILE = "versatile"
    STEALTH_DISADVANTAGE = "stealth_disadvantage"


class BaseItem(SQLModel, table=True):
    __tablename__ = "base_item"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint(
            "system",
            "canonical_key",
            name="uq_base_item_system_canonical_key",
        ),
    )

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    system: SystemType = Field(
        sa_column=Column(SAEnum(SystemType, name="systemtype"), nullable=False, index=True)
    )
    canonical_key: str = Field(
        sa_column=Column(String, nullable=False, index=True)
    )
    name_en: str
    name_pt: str
    description_en: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    description_pt: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    item_kind: BaseItemKind = Field(
        sa_column=Column(
            SAEnum(
                BaseItemKind,
                name="baseitemkind",
                values_callable=_enum_values,
            ),
            nullable=False,
            index=True,
        )
    )
    equipment_category: Optional[BaseItemEquipmentCategory] = Field(
        default=None,
        sa_column=Column(
            SAEnum(
                BaseItemEquipmentCategory,
                name="baseitemequipmentcategory",
                values_callable=_enum_values,
            ),
            nullable=True,
        ),
    )
    cost_quantity: Optional[float] = None
    cost_unit: Optional[BaseItemCostUnit] = Field(
        default=None,
        sa_column=Column(
            SAEnum(
                BaseItemCostUnit,
                name="baseitemcostunit",
                values_callable=_enum_values,
            ),
            nullable=True,
        ),
    )
    weight: Optional[float] = None
    weapon_category: Optional[BaseItemWeaponCategory] = Field(
        default=None,
        sa_column=Column(
            SAEnum(
                BaseItemWeaponCategory,
                name="baseitemweaponcategory",
                values_callable=_enum_values,
            ),
            nullable=True,
        ),
    )
    weapon_range_type: Optional[BaseItemWeaponRangeType] = Field(
        default=None,
        sa_column=Column(
            SAEnum(
                BaseItemWeaponRangeType,
                name="baseitemweaponrangetype",
                values_callable=_enum_values,
            ),
            nullable=True,
        ),
    )
    damage_dice: Optional[str] = None
    damage_type: Optional[BaseItemDamageType] = Field(
        default=None,
        sa_column=Column(
            SAEnum(
                BaseItemDamageType,
                name="baseitemdamagetype",
                values_callable=_enum_values,
            ),
            nullable=True,
        ),
    )
    heal_dice: Optional[str] = None
    heal_bonus: Optional[int] = None
    charges_max: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    recharge_type: Optional[str] = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    magic_effect_json: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    range_normal_meters: Optional[int] = None
    range_long_meters: Optional[int] = None
    versatile_damage: Optional[str] = None
    weapon_properties_json: Optional[list[str]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    armor_category: Optional[BaseItemArmorCategory] = Field(
        default=None,
        sa_column=Column(
            SAEnum(
                BaseItemArmorCategory,
                name="baseitemarmorcategory",
                values_callable=_enum_values,
            ),
            nullable=True,
        ),
    )
    armor_class_base: Optional[int] = None
    dex_bonus_rule: Optional[BaseItemDexBonusRule] = Field(
        default=None,
        sa_column=Column(
            SAEnum(
                BaseItemDexBonusRule,
                name="baseitemdexbonusrule",
                values_callable=_enum_values,
            ),
            nullable=True,
        ),
    )
    strength_requirement: Optional[int] = None
    stealth_disadvantage: Optional[bool] = None
    is_shield: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
    )
    source: BaseItemSource = Field(
        default=BaseItemSource.ADMIN_PANEL,
        sa_column=Column(
            SAEnum(
                BaseItemSource,
                name="baseitemsource",
                values_callable=_enum_values,
            ),
            nullable=False,
            server_default=BaseItemSource.ADMIN_PANEL.value,
        ),
    )
    source_ref: Optional[str] = None
    is_srd: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default="true"),
    )


class BaseItemAlias(SQLModel, table=True):
    __tablename__ = "base_item_alias"  # type: ignore[assignment]

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    base_item_id: str = Field(
        foreign_key="base_item.id",
        index=True,
    )
    alias: str = Field(
        sa_column=Column(String, nullable=False, index=True)
    )
    locale: Optional[str] = None
    alias_type: Optional[str] = None
