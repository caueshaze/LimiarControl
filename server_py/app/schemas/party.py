from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.campaign import RoleMode
from app.models.party_member import PartyMemberStatus
from app.schemas.session import ActiveSessionRead


class PartyCreate(BaseModel):
    campaignId: str
    name: str
    playerIds: list[str] = []


class PartyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    campaignId: str = Field(validation_alias="campaign_id")
    gmUserId: str = Field(validation_alias="gm_user_id")
    name: str
    createdAt: datetime = Field(validation_alias="created_at")


class PartyMemberAdd(BaseModel):
    userId: str
    role: RoleMode
    status: PartyMemberStatus = PartyMemberStatus.JOINED


class PartyMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    userId: str = Field(validation_alias="user_id")
    role: RoleMode
    status: PartyMemberStatus
    createdAt: datetime = Field(validation_alias="created_at")
    displayName: Optional[str] = Field(default=None, validation_alias="display_name")
    username: Optional[str] = None


class PartyDetail(PartyRead):
    members: list[PartyMemberRead]


class PartyActiveSession(BaseModel):
    party: PartyRead
    activeSession: Optional[ActiveSessionRead] = None


class PartyInviteRead(BaseModel):
    party: PartyRead
    campaignName: str
    status: PartyMemberStatus
    activeSession: Optional[ActiveSessionRead] = None
