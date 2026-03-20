from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.campaign_entity import CampaignEntityPublicRead, CampaignEntityRead


class SessionEntityCreate(BaseModel):
    campaignEntityId: str
    label: Optional[str] = None
    currentHp: Optional[int] = None


class SessionEntityUpdate(BaseModel):
    visibleToPlayers: Optional[bool] = None
    currentHp: Optional[int] = None
    label: Optional[str] = None
    overrides: Optional[dict] = None


class SessionEntityRead(BaseModel):
    id: str
    sessionId: str
    campaignEntityId: str
    visibleToPlayers: bool
    currentHp: Optional[int]
    overrides: Optional[dict]
    label: Optional[str]
    revealedAt: Optional[datetime]
    createdAt: datetime
    updatedAt: Optional[datetime]
    entity: Optional[CampaignEntityRead] = None


class SessionEntityPlayerRead(BaseModel):
    id: str
    sessionId: str
    campaignEntityId: str
    currentHp: Optional[int]
    label: Optional[str]
    revealedAt: Optional[datetime]
    entity: Optional[CampaignEntityPublicRead] = None
