from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_gm
from app.db.session import get_session
from app.models.campaign import Campaign, RoleMode, SystemType
from app.models.campaign_member import CampaignMember
from app.models.campaign_tactical_map import CampaignTacticalMap
from app.models.user import User
from app.schemas.campaign import (
    CampaignMapConfigCreate,
    CampaignCreate,
    CampaignMapConfigRead,
    CampaignMapConfigUpdate,
    CampaignOverview,
    CampaignRead,
    CampaignUpdate,
    decode_blocked_cells,
    encode_blocked_cells,
)
from app.services.campaign_catalog import snapshot_campaign_catalog
from app.services.campaign_cleanup import delete_campaign_tree
from app.services.campaign_spells import snapshot_campaign_spells
from app.services.media_storage_service import (
    assert_managed_asset_exists,
    delete_campaign_prefix_best_effort,
    delete_managed_url_best_effort,
    parse_managed_url,
)

router = APIRouter()
ENABLED_CAMPAIGN_SYSTEMS = {SystemType.DND5E}


def _ensure_supported_system(system: SystemType) -> None:
    if system not in ENABLED_CAMPAIGN_SYSTEMS:
        raise HTTPException(status_code=400, detail="Campaign system is not enabled")


def _ensure_unique_campaign_name_for_gm(
    name: str,
    gm_user_id: str,
    session: Session,
    *,
    exclude_campaign_id: str | None = None,
) -> None:
    normalized_name = name.strip()
    if not normalized_name:
        return

    statement = (
        select(Campaign.id)
        .join(CampaignMember, CampaignMember.campaign_id == Campaign.id)
        .where(
            CampaignMember.user_id == gm_user_id,
            CampaignMember.role_mode == RoleMode.GM,
            func.lower(Campaign.name) == normalized_name.lower(),
        )
    )
    if exclude_campaign_id is not None:
        statement = statement.where(Campaign.id != exclude_campaign_id)

    existing_campaign_id = session.exec(statement).first()
    if existing_campaign_id:
        raise HTTPException(
            status_code=409,
            detail="You already have a campaign with this name",
        )


def _list_campaign_map_configs(
    session: Session,
    campaign_id: str,
) -> list[CampaignMapConfigRead]:
    statement = (
        select(CampaignTacticalMap)
        .where(CampaignTacticalMap.campaign_id == campaign_id)
        .order_by(CampaignTacticalMap.created_at.desc())
    )
    entries = session.exec(statement).all()
    return [_serialize_campaign_map_config(entry) for entry in entries]


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

    # blockedCells: None = leave unchanged; [] = clear all; [...] = replace
    if payload.blockedCells is not None:
        entry.blocked_cells_json = encode_blocked_cells(payload.blockedCells)

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


def _serialize_campaign_map_config(campaign: CampaignTacticalMap) -> CampaignMapConfigRead:
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

    return CampaignMapConfigRead(
        id=campaign.id,
        mapName=campaign.name,
        imageUrl=campaign.image_url,
        gridWidth=campaign.grid_width,
        gridHeight=campaign.grid_height,
        calibration=calibration,
        blockedCells=decode_blocked_cells(campaign.blocked_cells_json),
        createdAt=campaign.created_at,
        updatedAt=campaign.updated_at,
    )


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


@router.get("", response_model=List[CampaignRead])
def list_campaigns(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    statement = (
        select(
            Campaign.id,
            Campaign.name,
            Campaign.system,
            Campaign.created_at,
            Campaign.updated_at,
            CampaignMember.role_mode,
        )
        .join(CampaignMember, CampaignMember.campaign_id == Campaign.id)
        .where(CampaignMember.user_id == user.id)
        .order_by(Campaign.created_at.desc())
    )
    entries = session.exec(statement).all()
    return [
        CampaignRead(
            id=campaign_id,
            name=name,
            systemType=system,
            roleMode=role_mode,
            createdAt=created_at,
            updatedAt=updated_at,
        )
        for campaign_id, name, system, created_at, updated_at, role_mode in entries
    ]


@router.get("/{campaign_id}/overview", response_model=CampaignOverview)
def campaign_overview(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign = session.exec(select(Campaign).where(Campaign.id == campaign_id)).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    gm_member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.role_mode == RoleMode.GM,
        )
    ).first()
    return CampaignOverview(
        id=campaign.id,
        name=campaign.name,
        systemType=campaign.system,
        roleMode=campaign.role_mode,
        createdAt=campaign.created_at,
        updatedAt=campaign.updated_at,
        gmName=gm_member.display_name if gm_member else None,
        maps=_list_campaign_map_configs(session, campaign_id),
    )


@router.post("", response_model=CampaignRead, status_code=201)
def create_campaign(
    payload: CampaignCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Invalid payload")
    campaign_name = payload.name.strip()
    _ensure_supported_system(payload.system)
    _ensure_unique_campaign_name_for_gm(campaign_name, user.id, session)
    campaign = Campaign(
        id=str(uuid4()),
        name=campaign_name,
        system=payload.system,
    )
    member = CampaignMember(
        id=str(uuid4()),
        campaign_id=campaign.id,
        user_id=user.id,
        display_name=user.display_name or user.username,
        role_mode=campaign.role_mode,
    )
    session.add(campaign)
    session.add(member)
    session.flush()
    snapshot_campaign_catalog(campaign=campaign, db=session, commit=False)
    snapshot_campaign_spells(campaign=campaign, db=session, commit=False)
    session.commit()
    session.refresh(campaign)
    return CampaignRead(
        id=campaign.id,
        name=campaign.name,
        systemType=campaign.system,
        roleMode=campaign.role_mode,
        createdAt=campaign.created_at,
        updatedAt=campaign.updated_at,
    )


@router.put("/{campaign_id}", response_model=CampaignRead)
def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign, _member = require_gm(campaign_id, user, session)
    if payload.name is not None:
        if not payload.name.strip():
            raise HTTPException(status_code=400, detail="Invalid payload")
        campaign_name = payload.name.strip()
        _ensure_unique_campaign_name_for_gm(
            campaign_name,
            user.id,
            session,
            exclude_campaign_id=campaign.id,
        )
        campaign.name = campaign_name
    if payload.system is not None:
        _ensure_supported_system(payload.system)
        campaign.system = payload.system
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return CampaignRead(
        id=campaign.id,
        name=campaign.name,
        systemType=campaign.system,
        roleMode=campaign.role_mode,
        createdAt=campaign.created_at,
        updatedAt=campaign.updated_at,
    )


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
    entry = CampaignTacticalMap(
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


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign, _member = require_gm(campaign_id, user, session)
    delete_campaign_tree(session, campaign)
    session.commit()
    delete_campaign_prefix_best_effort(campaign_id)
    return None
