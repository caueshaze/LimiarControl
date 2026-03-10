from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CharacterSheetRead(BaseModel):
    id: str
    partyId: str
    playerId: str
    data: Any
    createdAt: datetime
    updatedAt: datetime | None = None


class CharacterSheetCreate(BaseModel):
    data: Any


class CharacterSheetUpdate(BaseModel):
    data: Any
