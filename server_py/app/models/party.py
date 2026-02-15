from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class Party(SQLModel, table=True):
    __tablename__ = "party"

    id: str | None = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    campaign_id: str = Field(foreign_key="campaign.id", index=True)
    gm_user_id: str = Field(foreign_key="app_user.id", index=True)
    name: str
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
