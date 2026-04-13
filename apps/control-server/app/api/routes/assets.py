from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_campaign_member, require_gm
from app.db.session import get_session
from app.core.config import settings
from app.models.campaign import RoleMode
from app.models.campaign_entity import CampaignEntity
from app.models.session import Session as CampaignSession, SessionStatus
from app.models.session_entity import SessionEntity
from app.models.user import User
from app.services.media_storage_service import (
    ManagedAssetRef,
    assert_managed_asset_exists,
    build_asset_response_headers,
    get_object_stream,
    stream_object_chunks,
)

router = APIRouter()


def _require_internal_map_access(x_limiar_map_internal_key: str | None = Header(default=None)) -> None:
    if x_limiar_map_internal_key != settings.limiar_map_internal_key:
        raise HTTPException(status_code=403, detail="Forbidden")


def _ensure_visible_entity_asset(
    *,
    campaign_id: str,
    entity_id: str,
    user: User,
    session: Session,
) -> None:
    campaign, member = require_campaign_member(campaign_id, user, session)
    entry = session.exec(
        select(CampaignEntity).where(
            CampaignEntity.id == entity_id,
            CampaignEntity.campaign_id == campaign.id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entity not found")
    if member.role_mode == RoleMode.GM:
        return

    visible = session.exec(
        select(SessionEntity.id)
        .join(CampaignSession, CampaignSession.id == SessionEntity.session_id)
        .where(
            SessionEntity.campaign_entity_id == entity_id,
            SessionEntity.visible_to_players == True,  # noqa: E712
            CampaignSession.campaign_id == campaign_id,
            CampaignSession.status == SessionStatus.ACTIVE,
        )
        .limit(1)
    ).first()
    if visible is None:
        raise HTTPException(status_code=403, detail="Asset not available")


def _stream_managed_asset(ref: ManagedAssetRef) -> StreamingResponse:
    try:
        stream = get_object_stream(ref)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Asset not found") from exc
    headers = build_asset_response_headers(stream.headers)
    return StreamingResponse(
        stream_object_chunks(stream.response),
        media_type=stream.headers.content_type,
        headers=headers,
    )


@router.get("/campaigns/{campaign_id}/maps/{asset_id}")
def get_campaign_map_asset(
    campaign_id: str,
    asset_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_campaign_member(campaign_id, user, session)
    ref = ManagedAssetRef(kind="campaign_map", campaign_id=campaign_id, asset_id=asset_id)
    try:
        assert_managed_asset_exists(ref)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Asset not found") from exc
    return _stream_managed_asset(ref)


@router.get("/internal/campaigns/{campaign_id}/maps/{asset_id}")
def get_campaign_map_asset_internal(
    campaign_id: str,
    asset_id: str,
    _: None = Depends(_require_internal_map_access),
):
    ref = ManagedAssetRef(kind="campaign_map", campaign_id=campaign_id, asset_id=asset_id)
    try:
        assert_managed_asset_exists(ref)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Asset not found") from exc
    return _stream_managed_asset(ref)


@router.get("/campaigns/{campaign_id}/entities/tmp/{asset_id}")
def get_temporary_entity_asset(
    campaign_id: str,
    asset_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    ref = ManagedAssetRef(kind="entity_temp", campaign_id=campaign_id, asset_id=asset_id)
    try:
        assert_managed_asset_exists(ref)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Asset not found") from exc
    return _stream_managed_asset(ref)


@router.get("/campaigns/{campaign_id}/entities/{entity_id}/{asset_id}")
def get_entity_asset(
    campaign_id: str,
    entity_id: str,
    asset_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _ensure_visible_entity_asset(
        campaign_id=campaign_id,
        entity_id=entity_id,
        user=user,
        session=session,
    )
    ref = ManagedAssetRef(
        kind="entity_final",
        campaign_id=campaign_id,
        entity_id=entity_id,
        asset_id=asset_id,
    )
    try:
        assert_managed_asset_exists(ref)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Asset not found") from exc
    return _stream_managed_asset(ref)
