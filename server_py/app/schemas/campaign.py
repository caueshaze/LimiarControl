from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.campaign import RoleMode, SystemType


class CampaignCreate(BaseModel):
    name: str
    system: SystemType


class CampaignRead(BaseModel):
    id: str
    name: str
    joinCode: Optional[str] = None
    systemType: SystemType
    roleMode: RoleMode
    createdAt: datetime
    updatedAt: Optional[datetime]


class CampaignOverview(BaseModel):
    id: str
    name: str
    joinCode: Optional[str] = None
    systemType: SystemType
    roleMode: RoleMode
    createdAt: datetime
    updatedAt: Optional[datetime]
    gmName: Optional[str] = None


class CampaignJoinRequest(BaseModel):
    joinCode: str


class CampaignJoinResponse(BaseModel):
    campaignId: str
    campaignName: str
    gmName: Optional[str] = None
    memberId: str
    displayName: str
    roleMode: RoleMode


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    system: Optional[SystemType] = None


class RoleModeUpdate(BaseModel):
    roleMode: RoleMode


class RoleModeRead(BaseModel):
    roleMode: RoleMode
