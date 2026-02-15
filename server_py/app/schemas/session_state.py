from datetime import datetime

from pydantic import BaseModel


class SessionStateRead(BaseModel):
    id: str
    sessionId: str
    playerUserId: str
    state: dict
    createdAt: datetime
    updatedAt: datetime | None


class SessionStateUpdate(BaseModel):
    state: dict
