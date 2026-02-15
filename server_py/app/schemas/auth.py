from typing import Optional

from pydantic import BaseModel

from app.models.campaign import RoleMode


class RegisterRequest(BaseModel):
    username: str
    pin: str
    displayName: Optional[str] = None
    role: RoleMode


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
