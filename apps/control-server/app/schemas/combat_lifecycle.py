from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator
from app.schemas.campaign import (
    BlockedCell,
    CampaignEdgeObstacle,
    CampaignMapCalibration,
    CampaignObstacle,
    MAX_GRID_DIMENSION,
)

CombatActionCost = Literal["action", "bonus_action", "reaction", "free"]


class CombatParticipant(BaseModel):
    id: str
    kind: Literal["player", "session_entity"]
    ref_id: str
    display_name: str
    initiative: Optional[int] = None
    status: Literal["active", "downed", "stable", "dead", "defeated"] = "active"
    team: Literal["players", "enemies", "allies", "neutral"] = "neutral"
    visible: bool = True
    actor_user_id: Optional[str] = None
    active_effects: list[dict] = Field(default_factory=list)
    turn_resources: dict = Field(
        default_factory=lambda: {
            "action_used": False,
            "bonus_action_used": False,
            "reaction_used": False,
        }
    )


class CombatMapChoice(BaseModel):
    kind: Literal["campaign_map", "demo_map"]
    mapId: str | None = None


class CombatLocalDistanceEntry(BaseModel):
    from_ref_id: str
    to_ref_id: str
    distance_meters: float = Field(ge=0)


class CombatUpdateDistancesRequest(BaseModel):
    distances: list[CombatLocalDistanceEntry]


class CombatMapSelection(BaseModel):
    kind: Literal["campaign_map", "demo_map"]
    mapId: str | None = None
    mapName: str
    imageUrl: str
    gridWidth: int = Field(ge=1, le=MAX_GRID_DIMENSION)
    gridHeight: int = Field(ge=1, le=MAX_GRID_DIMENSION)
    calibration: CampaignMapCalibration
    obstacles: list[CampaignObstacle] | None = None
    edgeObstacles: list[CampaignEdgeObstacle] = Field(default_factory=list)
    blockedCells: list[BlockedCell] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_map_id(self):
        if self.kind == "campaign_map" and (
            self.mapId is None or not self.mapId.strip()
        ):
            raise ValueError("campaign_map selections must include mapId")
        return self


class CombatStartRequest(BaseModel):
    participants: list[CombatParticipant]
    selectedMap: CombatMapChoice | None = None
    useMap: bool = True
    initialDistances: list[CombatLocalDistanceEntry] | None = None

    @model_validator(mode="after")
    def validate_selected_map(self):
        if (
            self.selectedMap is not None
            and self.selectedMap.kind == "campaign_map"
            and (self.selectedMap.mapId is None or not self.selectedMap.mapId.strip())
        ):
            raise ValueError("selectedMap.mapId is required for campaign_map")
        return self


class CombatSetInitiativeParticipant(BaseModel):
    id: str
    initiative: int


class CombatSetInitiativeRequest(BaseModel):
    initiatives: list[CombatSetInitiativeParticipant]


class CombatNextTurnRequest(BaseModel):
    actor_participant_id: Optional[str] = None
