from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CurrencyRead(BaseModel):
    cp: int = 0
    sp: int = 0
    ep: int = 0
    gp: int = 0
    pp: int = 0


class InventoryRead(BaseModel):
    id: str
    campaignId: str
    partyId: Optional[str]
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


class InventorySell(BaseModel):
    inventoryItemId: str
    quantity: int = 1


class InventorySellRead(BaseModel):
    inventoryItem: InventoryRead | None
    itemId: str
    itemName: str
    soldQuantity: int
    refundCurrency: CurrencyRead
    refundLabel: str
    currentCurrency: CurrencyRead


class InventoryUpdate(BaseModel):
    quantity: Optional[int] = None
    isEquipped: Optional[bool] = None
    notes: Optional[str] = None
