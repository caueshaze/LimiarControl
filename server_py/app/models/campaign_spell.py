from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.base_spell import SpellSchool


def _enum_values(enum_cls: type[SpellSchool]) -> list[str]:
    return [member.value for member in enum_cls]


class CampaignSpell(SQLModel, table=True):
    __tablename__: ClassVar[str] = "campaign_spell"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "canonical_key",
            name="uq_campaign_spell_campaign_canonical_key",
        ),
        UniqueConstraint(
            "campaign_id",
            "base_spell_id",
            name="uq_campaign_spell_campaign_base_spell",
        ),
    )

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    campaign_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("campaign.id"),
            nullable=False,
            index=True,
        )
    )
    base_spell_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("base_spell.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    canonical_key: str = Field(
        sa_column=Column(String, nullable=False, index=True)
    )

    # --- Identity (editorial) ---
    name_en: str
    name_pt: Optional[str] = None
    description_en: str = Field(sa_column=Column(Text, nullable=False))
    description_pt: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    level: int = Field(sa_column=Column(Integer, nullable=False, index=True))
    school: SpellSchool = Field(
        sa_column=Column(
            SAEnum(
                SpellSchool,
                name="spellschool",
                values_callable=_enum_values,
                create_type=False,
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
    casting_time: Optional[str] = None
    range_meters: Optional[int] = None
    range_text: Optional[str] = None
    target_mode: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
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

    # --- Resolution (mechanical) ---
    resolution_type: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    saving_throw: Optional[str] = None
    save_success_outcome: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))

    # --- Effect (mechanical) ---
    damage_dice: Optional[str] = None
    damage_type: Optional[str] = None
    heal_dice: Optional[str] = None

    # --- Upcast (mechanical) ---
    upcast_json: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    upcast_mode: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    upcast_value: Optional[str] = None

    # --- Metadata ---
    source: Optional[str] = None
    source_ref: Optional[str] = None
    is_srd: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
    )
    is_custom: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
    )
    is_enabled: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default="true"),
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
