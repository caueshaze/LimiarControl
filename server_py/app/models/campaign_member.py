from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SAEnum, UniqueConstraint, func
from sqlmodel import Field, SQLModel

from app.models.campaign import RoleMode


class CampaignMember(SQLModel, table=True):
    __tablename__ = "campaign_member"
    __table_args__ = (UniqueConstraint("campaign_id", "user_id"),)

    id: str | None = Field(default=None, primary_key=True)
    campaign_id: str = Field(foreign_key="campaign.id", index=True)
    user_id: str = Field(foreign_key="app_user.id", index=True)
    display_name: str
    role_mode: RoleMode = Field(sa_column=Column(SAEnum(RoleMode), nullable=False))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
