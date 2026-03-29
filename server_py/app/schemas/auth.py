from typing import Optional

from pydantic import BaseModel, Field

from app.models.campaign import RoleMode


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    pin: str = Field(min_length=4, max_length=20)
    displayName: Optional[str] = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    username: str
    pin: str


class AuthResponse(BaseModel):
    token: str


class MeResponse(BaseModel):
    userId: str
    username: str
    displayName: Optional[str]
    role: RoleMode
    isSystemAdmin: bool
