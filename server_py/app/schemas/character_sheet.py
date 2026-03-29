import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

MAX_SHEET_DATA_BYTES = 512 * 1024  # 512 KB
MAX_SHEET_DATA_DEPTH = 12


def _check_depth(obj: Any, current: int = 0) -> None:
    if current > MAX_SHEET_DATA_DEPTH:
        raise ValueError(f"JSON nesting exceeds maximum depth of {MAX_SHEET_DATA_DEPTH}")
    if isinstance(obj, dict):
        for v in obj.values():
            _check_depth(v, current + 1)
    elif isinstance(obj, list):
        for v in obj:
            _check_depth(v, current + 1)


def _validate_sheet_data(value: Any) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Character sheet data must be a JSON object")
    serialized = json.dumps(value, separators=(",", ":"))
    if len(serialized.encode("utf-8")) > MAX_SHEET_DATA_BYTES:
        raise ValueError(
            f"Character sheet data exceeds maximum size of {MAX_SHEET_DATA_BYTES // 1024} KB"
        )
    _check_depth(value)
    return value


class CharacterSheetRead(BaseModel):
    id: str
    partyId: str
    playerId: str
    data: Any
    sourceDraftId: str | None = None
    deliveredByUserId: str | None = None
    deliveredAt: datetime | None = None
    acceptedAt: datetime | None = None
    createdAt: datetime
    updatedAt: datetime | None = None


class CharacterSheetCreate(BaseModel):
    data: dict

    @field_validator("data")
    @classmethod
    def validate_data(cls, v: Any) -> dict:
        return _validate_sheet_data(v)


class CharacterSheetUpdate(BaseModel):
    data: dict

    @field_validator("data")
    @classmethod
    def validate_data(cls, v: Any) -> dict:
        return _validate_sheet_data(v)
