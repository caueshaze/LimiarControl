from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, Integer, String, func
from sqlmodel import Field, SQLModel


class SystemType(str, Enum):
    DND5E = "DND5E"
    T20 = "T20"
    PF2E = "PF2E"
    COC = "COC"
    CUSTOM = "CUSTOM"


class RoleMode(str, Enum):
    GM = "GM"
    PLAYER = "PLAYER"


class Campaign(SQLModel, table=True):
    id: str | None = Field(default=None, primary_key=True)
    name: str

    system: SystemType = Field(sa_column=Column(SAEnum(SystemType), nullable=False))
    role_mode: RoleMode = Field(
        default=RoleMode.GM, sa_column=Column(SAEnum(RoleMode), nullable=False)
    )
    item_catalog_snapshot_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    spell_catalog_snapshot_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    map_name: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    map_image_url: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    map_grid_width: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    map_grid_height: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    map_calibration_x: float | None = Field(
        default=None,
        sa_column=Column(Float, nullable=True),
    )
    map_calibration_y: float | None = Field(
        default=None,
        sa_column=Column(Float, nullable=True),
    )
    map_calibration_width: float | None = Field(
        default=None,
        sa_column=Column(Float, nullable=True),
    )
    map_calibration_height: float | None = Field(
        default=None,
        sa_column=Column(Float, nullable=True),
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
