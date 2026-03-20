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


class SpellSchool(str, Enum):
    ABJURATION = "abjuration"
    CONJURATION = "conjuration"
    DIVINATION = "divination"
    ENCHANTMENT = "enchantment"
    EVOCATION = "evocation"
    ILLUSION = "illusion"
    NECROMANCY = "necromancy"
    TRANSMUTATION = "transmutation"


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

    casting_time: Optional[str] = None
    range_text: Optional[str] = None
    duration: Optional[str] = None
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

    damage_type: Optional[str] = None
    saving_throw: Optional[str] = None

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
        foreign_key="base_spell.id",
        index=True,
    )
    alias: str = Field(
        sa_column=Column(String, nullable=False, index=True)
    )
    locale: Optional[str] = None
    alias_type: Optional[str] = None
