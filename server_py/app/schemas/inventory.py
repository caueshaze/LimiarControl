from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class InventoryRead(BaseModel):
    id: str
    campaignId: str
    memberId: str
    itemId: str
    quantity: int
    isEquipped: bool
    notes: Optional[str]
    createdAt: datetime
    updatedAt: Optional[datetime]


class InventoryBuy(BaseModel):
    itemId: str
    quantity: int = 1


class InventoryUpdate(BaseModel):
    quantity: Optional[int] = None
    isEquipped: Optional[bool] = None
    notes: Optional[str] = None
