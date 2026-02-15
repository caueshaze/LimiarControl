from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, func
from sqlmodel import Field, SQLModel

from app.models.campaign import RoleMode


class PartyMemberStatus(str, Enum):
    INVITED = "invited"
    JOINED = "joined"
    DECLINED = "declined"
    LEFT = "left"


class PartyMember(SQLModel, table=True):
    __tablename__ = "party_member"

    party_id: str = Field(foreign_key="party.id", primary_key=True, index=True)
    user_id: str = Field(foreign_key="app_user.id", primary_key=True, index=True)
    role: RoleMode
    status: PartyMemberStatus = Field(
        default=PartyMemberStatus.JOINED,
        sa_column=Column(SAEnum(PartyMemberStatus), nullable=False),
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
