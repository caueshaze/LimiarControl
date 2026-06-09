from pydantic import BaseModel
from typing import Optional

from app.models.campaign import RoleMode

class UserSearchRead(BaseModel):
    id: str
    displayName: str
    username: str


class UserProfileRead(BaseModel):
    id: str
    displayName: str
    username: str
    avatarUrl: Optional[str] = None
    tokenColor: Optional[str] = None
    tokenImageUrl: Optional[str] = None
    preferredWorkspaceMode: Optional[RoleMode] = None
