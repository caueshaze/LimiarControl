from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NpcCreate(BaseModel):
    name: str
    race: Optional[str] = None
    role: Optional[str] = None
    trait: str
    goal: str
    secret: Optional[str] = None
    notes: Optional[str] = None


class NpcUpdate(NpcCreate):
    pass


class NpcRead(BaseModel):
    id: str
    campaignId: str
    name: str
    race: Optional[str]
    role: Optional[str]
    trait: str
    goal: str
    secret: Optional[str]
    notes: Optional[str]
    createdAt: datetime
    updatedAt: Optional[datetime]
