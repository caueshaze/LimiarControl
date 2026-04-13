from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PartyCharacterSheetDraftRead(BaseModel):
    id: str
    partyId: str
    name: str
    data: Any
    status: str
    createdByUserId: str
    archivedAt: datetime | None = None
    lastDerivedAt: datetime | None = None
    createdAt: datetime
    updatedAt: datetime | None = None


class PartyCharacterSheetDraftCreate(BaseModel):
    name: str
    data: Any


class PartyCharacterSheetDraftUpdate(BaseModel):
    name: str
    data: Any


class PartyCharacterSheetDraftDeriveRequest(BaseModel):
    playerUserId: str
