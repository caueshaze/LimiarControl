from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel

from app.models.base_item import BaseItemCostUnit, BaseItemKind


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class ItemType(str, Enum):
    WEAPON = "WEAPON"
    ARMOR = "ARMOR"
    CONSUMABLE = "CONSUMABLE"
    MISC = "MISC"
    MAGIC = "MAGIC"


class Item(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "base_item_id",
            name="uq_item_campaign_base_item",
        ),
    )

    id: str | None = Field(default=None, primary_key=True)
    campaign_id: str = Field(foreign_key="campaign.id", index=True)
    name: str
    type: ItemType = Field(sa_column=Column(SAEnum(ItemType), nullable=False))
    description: str
    price: float | None = None
    weight: float | None = None
    damage_dice: str | None = None
    range_meters: float | None = None
    properties: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String), nullable=False, server_default="{}"),
    )

    base_item_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("base_item.id"),
            nullable=True,
            index=True,
        ),
    )
    canonical_key_snapshot: Optional[str] = None
    name_en_snapshot: Optional[str] = None
    name_pt_snapshot: Optional[str] = None
    item_kind: Optional[BaseItemKind] = Field(
        default=None,
        sa_column=Column(
            SAEnum(
                BaseItemKind,
                name="baseitemkind",
                values_callable=_enum_values,
                create_type=False,
            ),
            nullable=True,
        ),
    )
    cost_unit: Optional[BaseItemCostUnit] = Field(
        default=None,
        sa_column=Column(
            SAEnum(
                BaseItemCostUnit,
                name="baseitemcostunit",
                values_callable=_enum_values,
                create_type=False,
            ),
            nullable=True,
        ),
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
