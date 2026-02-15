from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.models.campaign import RoleMode

class User(SQLModel, table=True):
    __tablename__ = "app_user"

    id: str | None = Field(default=None, primary_key=True)
    username: str = Field(sa_column=Column(String, unique=True, nullable=False, index=True))
    display_name: str | None = None
    pin_hash: str
    role: RoleMode = Field(
        default=RoleMode.PLAYER,
        sa_column=Column(SAEnum(RoleMode), nullable=False, server_default=RoleMode.PLAYER.value),
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
