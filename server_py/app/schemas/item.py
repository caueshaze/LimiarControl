from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.base_item import BaseItemCostUnit, BaseItemKind
from app.models.item import ItemType


class ItemCreate(BaseModel):
    name: str
    type: ItemType
    description: str
    price: Optional[float] = None
    weight: Optional[float] = None
    damageDice: Optional[str] = None
    rangeMeters: Optional[float] = None
    properties: list[str] = Field(default_factory=list)


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
    baseItemId: Optional[str] = None
    canonicalKeySnapshot: Optional[str] = None
    nameEnSnapshot: Optional[str] = None
    namePtSnapshot: Optional[str] = None
    itemKind: Optional[BaseItemKind] = None
    costUnit: Optional[BaseItemCostUnit] = None
    isCustom: bool = False
    isEnabled: bool = True
    createdAt: datetime
    updatedAt: Optional[datetime]
