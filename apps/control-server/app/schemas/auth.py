from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.campaign import RoleMode


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    pin: str = Field(min_length=4, max_length=20)
    displayName: Optional[str] = Field(default=None, max_length=255)
    role: RoleMode = Field(default=RoleMode.PLAYER)


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
    avatarUrl: Optional[str] = None
    tokenColor: Optional[str] = None
    tokenImageUrl: Optional[str] = None
    onboardedAt: Optional[datetime] = None


_HEX_COLOR_RE = __import__("re").compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")


class UpdateProfileRequest(BaseModel):
    displayName: Optional[str] = Field(default=None, max_length=255)
    avatarUrl: Optional[str] = Field(default=None, max_length=1024)
    tokenColor: Optional[str] = Field(default=None, max_length=9)
    tokenImageUrl: Optional[str] = Field(default=None, max_length=1024)
    markOnboarded: Optional[bool] = None

    @field_validator("tokenColor")
    @classmethod
    def _validate_color(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return value
        if not _HEX_COLOR_RE.match(value):
            raise ValueError("tokenColor must be '#RRGGBB' or '#RRGGBBAA'")
        return value
