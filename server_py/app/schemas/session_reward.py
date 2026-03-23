from pydantic import BaseModel, Field

from app.schemas.inventory import CurrencyRead, InventoryRead


class SessionGrantCurrencyRequest(BaseModel):
    playerUserId: str
    copperValue: int = Field(ge=1)


class SessionGrantCurrencyRead(BaseModel):
    playerUserId: str
    currentCurrency: CurrencyRead
    grantedCurrency: CurrencyRead


class SessionGrantItemRequest(BaseModel):
    playerUserId: str
    itemId: str
    quantity: int = Field(default=1, ge=1)
    notes: str | None = None


class SessionGrantItemRead(BaseModel):
    playerUserId: str
    itemId: str
    itemName: str
    quantity: int
    inventoryItem: InventoryRead


class SessionGrantXpRequest(BaseModel):
    playerUserId: str
    amount: int = Field(ge=1)


class SessionGrantXpRead(BaseModel):
    playerUserId: str
    grantedAmount: int
    currentXp: int
    currentLevel: int
    nextLevelThreshold: int | None
