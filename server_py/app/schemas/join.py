from pydantic import BaseModel

from app.models.campaign import RoleMode


class MemberRead(BaseModel):
    campaignId: str
    displayName: str
    roleMode: RoleMode


class MemberSummary(BaseModel):
    id: str
    displayName: str
    roleMode: RoleMode


class MemberRoleUpdate(BaseModel):
    roleMode: RoleMode


class MemberUpdate(BaseModel):
    role: RoleMode
