from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user, require_campaign_member, require_gm
from app.db.session import get_session
from app.models.campaign_entity import CampaignEntity
from app.models.session import Session, SessionStatus
from app.models.session_entity import SessionEntity
from app.models.user import User
from app.schemas.session_entity import (
    SessionEntityCreate,
    SessionEntityPlayerRead,
    SessionEntityRead,
    SessionEntityUpdate,
)
from app.api.routes.campaign_entities import to_campaign_entity_read, to_campaign_entity_public_read
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel

router = APIRouter()


def _get_session_entry(session_id: str, db: DbSession) -> Session:
    entry = db.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    return entry


def _require_session_gm(session_entry: Session, user: User, db: DbSession):
    require_gm(session_entry.campaign_id, user, db)


def _to_session_entity_read(
    se: SessionEntity, ce: CampaignEntity | None
) -> SessionEntityRead:
    return SessionEntityRead(
        id=se.id,
        sessionId=se.session_id,
        campaignEntityId=se.campaign_entity_id,
        visibleToPlayers=se.visible_to_players,
        currentHp=se.current_hp,
        overrides=se.overrides,
        label=se.label,
        revealedAt=se.revealed_at,
        createdAt=se.created_at,
        updatedAt=se.updated_at,
        entity=to_campaign_entity_read(ce) if ce else None,
    )


def _to_session_entity_player_read(
    se: SessionEntity, ce: CampaignEntity | None
) -> SessionEntityPlayerRead:
    return SessionEntityPlayerRead(
        id=se.id,
        sessionId=se.session_id,
        campaignEntityId=se.campaign_entity_id,
        currentHp=se.current_hp,
        label=se.label,
        revealedAt=se.revealed_at,
        entity=to_campaign_entity_public_read(ce) if ce else None,
    )


async def _publish_entity_event(
    session_entry: Session,
    event_type: str,
    payload: dict,
    version_source: datetime | None = None,
) -> None:
    version = event_version(version_source or datetime.now(timezone.utc))
    await centrifugo.publish(
        session_channel(session_entry.id),
        build_event(event_type, payload, version=version),
    )
    await centrifugo.publish(
        campaign_channel(session_entry.campaign_id),
        build_event(event_type, payload, version=version),
    )


def _entity_event_payload(session_entry: Session, se: SessionEntity) -> dict:
    return {
        "sessionId": session_entry.id,
        "campaignId": session_entry.campaign_id,
        "partyId": session_entry.party_id,
        "sessionEntityId": se.id,
        "campaignEntityId": se.campaign_entity_id,
        "visibleToPlayers": se.visible_to_players,
        "label": se.label,
        "currentHp": se.current_hp,
    }


@router.get("/sessions/{session_id}/entities", response_model=list[SessionEntityRead])
def list_session_entities(
    session_id: str,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    session_entry = _get_session_entry(session_id, session)
    _require_session_gm(session_entry, user, session)
    results = session.exec(
        select(SessionEntity, CampaignEntity)
        .outerjoin(CampaignEntity, CampaignEntity.id == SessionEntity.campaign_entity_id)
        .where(SessionEntity.session_id == session_id)
        .order_by(SessionEntity.created_at.asc())
    ).all()
    return [_to_session_entity_read(se, ce) for se, ce in results]


@router.post("/sessions/{session_id}/entities", response_model=SessionEntityRead, status_code=201)
async def add_session_entity(
    session_id: str,
    payload: SessionEntityCreate,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    session_entry = _get_session_entry(session_id, session)
    _require_session_gm(session_entry, user, session)
    if session_entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")
    # Validate campaign entity belongs to same campaign
    ce = session.exec(
        select(CampaignEntity).where(
            CampaignEntity.id == payload.campaignEntityId,
            CampaignEntity.campaign_id == session_entry.campaign_id,
        )
    ).first()
    if not ce:
        raise HTTPException(status_code=404, detail="Campaign entity not found")
    se = SessionEntity(
        id=str(uuid4()),
        session_id=session_id,
        campaign_entity_id=payload.campaignEntityId,
        current_hp=payload.currentHp if payload.currentHp is not None else ce.base_hp,
        label=payload.label,
    )
    session.add(se)
    session.commit()
    session.refresh(se)
    await _publish_entity_event(
        session_entry,
        "session_entity_added",
        _entity_event_payload(session_entry, se),
        se.created_at,
    )
    return _to_session_entity_read(se, ce)


@router.put("/sessions/{session_id}/entities/{session_entity_id}", response_model=SessionEntityRead)
async def update_session_entity(
    session_id: str,
    session_entity_id: str,
    payload: SessionEntityUpdate,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    session_entry = _get_session_entry(session_id, session)
    _require_session_gm(session_entry, user, session)
    se = session.exec(
        select(SessionEntity).where(
            SessionEntity.id == session_entity_id,
            SessionEntity.session_id == session_id,
        )
    ).first()
    if not se:
        raise HTTPException(status_code=404, detail="Session entity not found")
    hp_changed = False
    visibility_changed = False
    if payload.visibleToPlayers is not None and payload.visibleToPlayers != se.visible_to_players:
        visibility_changed = True
        se.visible_to_players = payload.visibleToPlayers
        if payload.visibleToPlayers:
            se.revealed_at = datetime.now(timezone.utc)
        else:
            se.revealed_at = None
    if payload.currentHp is not None and payload.currentHp != se.current_hp:
        hp_changed = True
        se.current_hp = payload.currentHp
    if payload.label is not None:
        se.label = payload.label
    if payload.overrides is not None:
        se.overrides = payload.overrides
    session.add(se)
    session.commit()
    session.refresh(se)
    ce = session.exec(select(CampaignEntity).where(CampaignEntity.id == se.campaign_entity_id)).first()
    event_payload = _entity_event_payload(session_entry, se)
    if visibility_changed:
        event_type = "entity_revealed" if se.visible_to_players else "entity_hidden"
        await _publish_entity_event(session_entry, event_type, event_payload, se.updated_at or se.created_at)
    if hp_changed:
        await _publish_entity_event(session_entry, "entity_hp_updated", event_payload, se.updated_at or se.created_at)
    return _to_session_entity_read(se, ce)


@router.delete("/sessions/{session_id}/entities/{session_entity_id}", status_code=204)
async def remove_session_entity(
    session_id: str,
    session_entity_id: str,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    session_entry = _get_session_entry(session_id, session)
    _require_session_gm(session_entry, user, session)
    se = session.exec(
        select(SessionEntity).where(
            SessionEntity.id == session_entity_id,
            SessionEntity.session_id == session_id,
        )
    ).first()
    if not se:
        raise HTTPException(status_code=404, detail="Session entity not found")
    payload = _entity_event_payload(session_entry, se)
    session.delete(se)
    session.commit()
    await _publish_entity_event(session_entry, "session_entity_removed", payload)
    return None


@router.post("/sessions/{session_id}/entities/{session_entity_id}/reveal", response_model=SessionEntityRead)
async def reveal_session_entity(
    session_id: str,
    session_entity_id: str,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    session_entry = _get_session_entry(session_id, session)
    _require_session_gm(session_entry, user, session)
    se = session.exec(
        select(SessionEntity).where(
            SessionEntity.id == session_entity_id,
            SessionEntity.session_id == session_id,
        )
    ).first()
    if not se:
        raise HTTPException(status_code=404, detail="Session entity not found")
    se.visible_to_players = True
    se.revealed_at = datetime.now(timezone.utc)
    session.add(se)
    session.commit()
    session.refresh(se)
    ce = session.exec(select(CampaignEntity).where(CampaignEntity.id == se.campaign_entity_id)).first()
    await _publish_entity_event(
        session_entry,
        "entity_revealed",
        _entity_event_payload(session_entry, se),
        se.revealed_at,
    )
    return _to_session_entity_read(se, ce)


@router.post("/sessions/{session_id}/entities/{session_entity_id}/hide", response_model=SessionEntityRead)
async def hide_session_entity(
    session_id: str,
    session_entity_id: str,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    session_entry = _get_session_entry(session_id, session)
    _require_session_gm(session_entry, user, session)
    se = session.exec(
        select(SessionEntity).where(
            SessionEntity.id == session_entity_id,
            SessionEntity.session_id == session_id,
        )
    ).first()
    if not se:
        raise HTTPException(status_code=404, detail="Session entity not found")
    se.visible_to_players = False
    se.revealed_at = None
    session.add(se)
    session.commit()
    session.refresh(se)
    ce = session.exec(select(CampaignEntity).where(CampaignEntity.id == se.campaign_entity_id)).first()
    await _publish_entity_event(
        session_entry,
        "entity_hidden",
        _entity_event_payload(session_entry, se),
        se.updated_at or se.created_at,
    )
    return _to_session_entity_read(se, ce)


@router.get("/sessions/{session_id}/entities/visible", response_model=list[SessionEntityPlayerRead])
def list_visible_session_entities(
    session_id: str,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    session_entry = _get_session_entry(session_id, session)
    require_campaign_member(session_entry.campaign_id, user, session)
    results = session.exec(
        select(SessionEntity, CampaignEntity)
        .outerjoin(CampaignEntity, CampaignEntity.id == SessionEntity.campaign_entity_id)
        .where(
            SessionEntity.session_id == session_id,
            SessionEntity.visible_to_players == True,
        )
        .order_by(SessionEntity.created_at.asc())
    ).all()
    return [_to_session_entity_player_read(se, ce) for se, ce in results]
