from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.campaign import RoleMode
from app.models.session import SessionStatus


class SessionRead(BaseModel):
    id: str
    campaignId: str
    number: int
    title: str
    joinCode: Optional[str] = None
    status: SessionStatus
    isActive: bool
    startedAt: Optional[datetime] = None
    endedAt: Optional[datetime] = None
    durationSeconds: int
    createdAt: datetime
    updatedAt: Optional[datetime]


class SessionJoinRequest(BaseModel):
    joinCode: str


class SessionJoinResponse(BaseModel):
    campaignId: str
    campaignName: str
    gmName: Optional[str] = None
    sessionId: str
    memberId: str
    displayName: str
    roleMode: RoleMode


class SessionActivateRequest(BaseModel):
    title: str


class SessionCommandRequest(BaseModel):
    type: str
    payload: Optional[dict] = None


class ActiveSessionRead(BaseModel):
    id: str
    campaignId: str
    number: int
    title: str
    joinCode: Optional[str] = None
    status: SessionStatus
    isActive: bool
    startedAt: Optional[datetime] = None
    endedAt: Optional[datetime] = None
    durationSeconds: int
    createdAt: datetime
    updatedAt: Optional[datetime]
