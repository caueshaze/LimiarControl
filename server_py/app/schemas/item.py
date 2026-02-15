from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.item import ItemType


class ItemCreate(BaseModel):
    name: str
    type: ItemType
    description: str
    price: Optional[float] = None
    weight: Optional[float] = None
    damageDice: Optional[str] = None
    rangeMeters: Optional[float] = None
    properties: list[str] = []


class ItemUpdate(ItemCreate):
    pass


class ItemRead(BaseModel):
    id: str
    campaignId: str
    name: str
    type: ItemType
    description: str
    price: Optional[float]
    weight: Optional[float]
    damageDice: Optional[str]
    rangeMeters: Optional[float]
    properties: list[str]
    createdAt: datetime
    updatedAt: Optional[datetime]
