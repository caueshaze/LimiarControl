from typing import Any, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select

from app.api.deps import get_current_user, require_gm
from app.db.session import get_session
from app.models.campaign_tactical_map import CampaignTacticalMap
from app.models.user import User
from app.schemas.campaign import (
    CampaignMapConfigCreate,
    CampaignMapConfigRead,
    CampaignMapConfigUpdate,
    decode_blocked_cells,
    decode_edge_obstacles,
    decode_obstacles,
    encode_blocked_cells,
    encode_edge_obstacles,
    encode_obstacles,
)
from app.services.media_storage_service import (
    assert_managed_asset_exists,
    delete_managed_url_best_effort,
)
from app.services.media_types import parse_managed_url

router = APIRouter()


def _serialize_campaign_map_config(campaign: CampaignTacticalMap) -> CampaignMapConfigRead:
    assert campaign.id is not None  # persisted map always has an id
    calibration = None
    if all(
        value is not None
        for value in (
            campaign.calibration_x,
            campaign.calibration_y,
            campaign.calibration_width,
            campaign.calibration_height,
        )
    ):
        calibration = {
            "x": campaign.calibration_x,
            "y": campaign.calibration_y,
            "width": campaign.calibration_width,
            "height": campaign.calibration_height,
        }

    obstacles = decode_obstacles(getattr(campaign, "obstacles_json", None))
    edge_obstacles = decode_edge_obstacles(getattr(campaign, "edge_obstacles_json", None))
    return CampaignMapConfigRead(
        id=campaign.id,
        mapName=campaign.name,
        imageUrl=campaign.image_url,
        gridWidth=campaign.grid_width,
        gridHeight=campaign.grid_height,
        calibration=cast(Any, calibration),
        obstacles=obstacles,
        edgeObstacles=edge_obstacles,
        blockedCells=decode_blocked_cells(getattr(campaign, "blocked_cells_json", None)) if obstacles is None else [],
        createdAt=campaign.created_at,
        updatedAt=campaign.updated_at,
    )


def _list_campaign_map_configs(
    session: Session,
    campaign_id: str,
) -> list[CampaignMapConfigRead]:
    statement = (
        select(CampaignTacticalMap)
        .where(CampaignTacticalMap.campaign_id == campaign_id)
        .order_by(col(CampaignTacticalMap.created_at).desc())
    )
    entries = session.exec(statement).all()
    return [_serialize_campaign_map_config(entry) for entry in entries]


def _validate_campaign_map_image_url(
    campaign_id: str,
    image_url: str | None,
) -> str | None:
    if image_url is None:
        return None
    try:
        ref = parse_managed_url(image_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if ref.kind != "campaign_map" or ref.campaign_id != campaign_id:
        raise HTTPException(
            status_code=400,
            detail="imageUrl must reference a managed map asset for this campaign",
        )
    try:
        assert_managed_asset_exists(ref)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail="Map image asset not found") from exc
    return ref.url


def _apply_campaign_map_payload(
    entry: CampaignTacticalMap,
    payload: CampaignMapConfigCreate | CampaignMapConfigUpdate,
    *,
    campaign_id: str,
) -> tuple[str | None, str | None]:
    previous_image_url = entry.image_url
    next_image_url = _validate_campaign_map_image_url(campaign_id, payload.imageUrl)

    entry.name = payload.mapName.strip() if payload.mapName and payload.mapName.strip() else None
    entry.image_url = next_image_url
    entry.grid_width = payload.gridWidth
    entry.grid_height = payload.gridHeight

    if payload.calibration is None:
        entry.calibration_x = None
        entry.calibration_y = None
        entry.calibration_width = None
        entry.calibration_height = None
    else:
        entry.calibration_x = payload.calibration.x
        entry.calibration_y = payload.calibration.y
        entry.calibration_width = payload.calibration.width
        entry.calibration_height = payload.calibration.height

    if payload.obstacles is not None:
        entry.obstacles_json = encode_obstacles(payload.obstacles)
        entry.blocked_cells_json = None
    elif payload.blockedCells is not None:
        entry.blocked_cells_json = encode_blocked_cells(payload.blockedCells)

    if payload.edgeObstacles is not None:
        entry.edge_obstacles_json = encode_edge_obstacles(payload.edgeObstacles)

    return previous_image_url, entry.image_url


def _require_campaign_map(
    session: Session,
    *,
    campaign_id: str,
    map_id: str,
) -> CampaignTacticalMap:
    entry = session.exec(
        select(CampaignTacticalMap).where(
            CampaignTacticalMap.id == map_id,
            CampaignTacticalMap.campaign_id == campaign_id,
        )
    ).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Campaign map not found")
    return entry


@router.get("/{campaign_id}/maps", response_model=list[CampaignMapConfigRead])
def list_campaign_map_configs(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    return _list_campaign_map_configs(session, campaign_id)


@router.post("/{campaign_id}/maps", response_model=CampaignMapConfigRead, status_code=201)
def create_campaign_map_config(
    campaign_id: str,
    payload: CampaignMapConfigCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    entry = CampaignTacticalMap(  # type: ignore[call-arg]  # created_at/updated_at filled by DB defaults
        id=str(uuid4()),
        campaign_id=campaign_id,
    )
    _apply_campaign_map_payload(entry, payload, campaign_id=campaign_id)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return _serialize_campaign_map_config(entry)


@router.put("/{campaign_id}/maps/{map_id}", response_model=CampaignMapConfigRead)
def update_campaign_map_config(
    campaign_id: str,
    map_id: str,
    payload: CampaignMapConfigUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    entry = _require_campaign_map(session, campaign_id=campaign_id, map_id=map_id)
    previous_image_url, next_image_url = _apply_campaign_map_payload(
        entry,
        payload,
        campaign_id=campaign_id,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    if previous_image_url != next_image_url:
        delete_managed_url_best_effort(previous_image_url)
    return _serialize_campaign_map_config(entry)


@router.delete("/{campaign_id}/maps/{map_id}", status_code=204)
def delete_campaign_map_config(
    campaign_id: str,
    map_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    entry = _require_campaign_map(session, campaign_id=campaign_id, map_id=map_id)
    image_url = entry.image_url
    session.delete(entry)
    session.commit()
    delete_managed_url_best_effort(image_url)
    return None
