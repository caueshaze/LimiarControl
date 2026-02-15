from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.campaign import RoleMode


class RollDice(BaseModel):
    count: int
    sides: int
    modifier: int


class RollEventRead(BaseModel):
    id: str
    campaignId: str
    sessionId: str
    authorName: str
    roleMode: RoleMode
    label: Optional[str]
    expression: str
    dice: RollDice
    results: list[int]
    total: int
    createdAt: datetime
