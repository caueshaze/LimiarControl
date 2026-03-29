from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CurrencyRead(BaseModel):
    copperValue: int = 0


class InventoryRead(BaseModel):
    id: str
    campaignId: str
    partyId: Optional[str]
    memberId: str
    itemId: str
    quantity: int
    chargesCurrent: Optional[int] = None
    isEquipped: bool
    notes: Optional[str]
    sourceSpellCanonicalKey: Optional[str] = None
    expiresAt: Optional[datetime] = None
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
