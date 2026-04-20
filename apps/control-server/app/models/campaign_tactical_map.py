from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func
from sqlmodel import Field, SQLModel


class CampaignTacticalMap(SQLModel, table=True):
    __tablename__ = "campaign_tactical_map"  # type: ignore[assignment]

    id: str | None = Field(default=None, primary_key=True)
    campaign_id: str = Field(foreign_key="campaign.id", index=True)
    name: str | None = Field(default=None, sa_column=Column(String, nullable=True))
    image_url: str | None = Field(default=None, sa_column=Column(String, nullable=True))
    grid_width: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    grid_height: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    calibration_x: float | None = Field(default=None, sa_column=Column(Float, nullable=True))
    calibration_y: float | None = Field(default=None, sa_column=Column(Float, nullable=True))
    calibration_width: float | None = Field(default=None, sa_column=Column(Float, nullable=True))
    calibration_height: float | None = Field(default=None, sa_column=Column(Float, nullable=True))
    # JSON-encoded list of blocked cell coordinates: [{"x": int, "y": int}, ...]
    # Legacy Phase 1 storage — superseded by obstacles_json for new maps.
    blocked_cells_json: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    # JSON-encoded semantic obstacles: [{x, y, blocksMovement, blocksEffect, blocksVision,
    # cover, clipsDiagonalMovement, movementCostMultiplier}, ...]
    # Authoritative when present; blocked_cells_json is ignored.
    obstacles_json: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
