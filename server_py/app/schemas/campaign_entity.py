from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


VALID_CATEGORIES = {"npc", "enemy", "creature", "ally"}

_Int = int


class AbilityStats(BaseModel):
    str: Optional[_Int] = None
    dex: Optional[_Int] = None
    con: Optional[_Int] = None
    int: Optional[_Int] = None
    wis: Optional[_Int] = None
    cha: Optional[_Int] = None


class CampaignEntityCreate(BaseModel):
    name: str
    category: str = "npc"
    description: Optional[str] = None
    imageUrl: Optional[str] = None
    baseHp: Optional[int] = None
    baseAc: Optional[int] = None
    stats: Optional[AbilityStats] = None
    actions: Optional[str] = None
    notesPrivate: Optional[str] = None
    notesPublic: Optional[str] = None


class CampaignEntityUpdate(CampaignEntityCreate):
    pass


class CampaignEntityRead(BaseModel):
    id: str
    campaignId: str
    name: str
    category: str
    description: Optional[str]
    imageUrl: Optional[str]
    baseHp: Optional[int]
    baseAc: Optional[int]
    stats: Optional[AbilityStats]
    actions: Optional[str]
    notesPrivate: Optional[str]
    notesPublic: Optional[str]
    createdAt: datetime
    updatedAt: Optional[datetime]


class CampaignEntityPublicRead(BaseModel):
    id: str
    campaignId: str
    name: str
    category: str
    description: Optional[str]
    imageUrl: Optional[str]
    baseHp: Optional[int]
    baseAc: Optional[int]
    stats: Optional[AbilityStats]
    actions: Optional[str]
    notesPublic: Optional[str]
    createdAt: datetime
