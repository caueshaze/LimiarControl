import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.campaign import RoleMode, SystemType
from app.services.media_storage_service import is_managed_url

MAX_GRID_DIMENSION = 150


class BlockedCell(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)


def decode_blocked_cells(raw_json: str | None) -> list[BlockedCell]:
    """Parse blocked_cells_json from DB into a list of BlockedCell objects."""
    if not raw_json:
        return []
    try:
        items = json.loads(raw_json)
        if not isinstance(items, list):
            return []
        return [BlockedCell(**item) for item in items if isinstance(item, dict)]
    except Exception:
        return []


def encode_blocked_cells(cells: list[BlockedCell] | None) -> str | None:
    """Serialize blocked cells to JSON for DB storage."""
    if not cells:
        return None
    return json.dumps([{"x": c.x, "y": c.y} for c in cells])


class CampaignCreate(BaseModel):
    name: str
    system: SystemType


class CampaignRead(BaseModel):
    id: str
    name: str

    systemType: SystemType
    roleMode: RoleMode
    createdAt: datetime
    updatedAt: Optional[datetime]


class CampaignMapCalibration(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.x + self.width > 1:
            raise ValueError("Map calibration width exceeds image bounds")
        if self.y + self.height > 1:
            raise ValueError("Map calibration height exceeds image bounds")
        return self


class CampaignMapConfigRead(BaseModel):
    id: str
    mapName: Optional[str] = None
    imageUrl: Optional[str] = None
    gridWidth: Optional[int] = Field(default=None, ge=1, le=MAX_GRID_DIMENSION)
    gridHeight: Optional[int] = Field(default=None, ge=1, le=MAX_GRID_DIMENSION)
    calibration: Optional[CampaignMapCalibration] = None
    # Movement-blocking cells defined at the campaign map level (Phase 1 obstacles).
    blockedCells: list[BlockedCell] = Field(default_factory=list)
    createdAt: datetime
    updatedAt: Optional[datetime] = None


class CampaignOverview(BaseModel):
    id: str
    name: str

    systemType: SystemType
    roleMode: RoleMode
    createdAt: datetime
    updatedAt: Optional[datetime]
    gmName: Optional[str] = None
    maps: list[CampaignMapConfigRead] = Field(default_factory=list)


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    system: Optional[SystemType] = None


class CampaignMapConfigWrite(BaseModel):
    mapName: Optional[str] = None
    imageUrl: Optional[str] = None
    gridWidth: Optional[int] = Field(default=None, ge=1, le=MAX_GRID_DIMENSION)
    gridHeight: Optional[int] = Field(default=None, ge=1, le=MAX_GRID_DIMENSION)
    calibration: Optional[CampaignMapCalibration] = None
    # Movement-blocking cells for Phase 1 obstacle handling.
    # None means "leave existing cells unchanged"; [] means "clear all blocked cells".
    blockedCells: Optional[list[BlockedCell]] = None

    @field_validator("mapName", "imageUrl", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]):
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("imageUrl")
    @classmethod
    def validate_managed_image_url(cls, value: Optional[str]):
        if value is None:
            return None
        if not is_managed_url(value):
            raise ValueError("imageUrl must use the canonical managed asset URL")
        return value

    @model_validator(mode="after")
    def validate_pairing(self):
        has_grid_width = self.gridWidth is not None
        has_grid_height = self.gridHeight is not None
        if has_grid_width != has_grid_height:
            raise ValueError("Grid width and height must be provided together")
        has_any_value = any(
            value is not None
            for value in (
                self.mapName,
                self.imageUrl,
                self.gridWidth,
                self.gridHeight,
                self.calibration,
                self.blockedCells,
            )
        )
        if not has_any_value:
            raise ValueError("Map payload must include at least one field")
        return self


class CampaignMapConfigCreate(CampaignMapConfigWrite):
    pass


class CampaignMapConfigUpdate(CampaignMapConfigWrite):
    pass


class RoleModeUpdate(BaseModel):
    roleMode: RoleMode


class RoleModeRead(BaseModel):
    roleMode: RoleMode
