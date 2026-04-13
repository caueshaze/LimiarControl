from typing import Optional

from pydantic import BaseModel, Field

from app.models.campaign import RoleMode


class MemberRead(BaseModel):
    campaignId: str
    displayName: str
    roleMode: RoleMode


class MemberSummary(BaseModel):
    id: str
    userId: str
    displayName: str
    roleMode: RoleMode


class MemberRoleUpdate(BaseModel):
    roleMode: RoleMode


class MemberUpdate(BaseModel):
    displayName: Optional[str] = Field(default=None, min_length=1, max_length=255)


class MemberRoleAssign(BaseModel):
    roleMode: RoleMode
