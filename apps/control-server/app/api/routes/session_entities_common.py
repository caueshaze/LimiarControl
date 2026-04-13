from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session as DbSession, select

from app.api.deps import require_gm
from app.api.routes.campaign_entities import (
    to_campaign_entity_public_read,
    to_campaign_entity_read,
)
from app.models.campaign_entity import CampaignEntity
from app.models.session import Session, SessionStatus
from app.models.session_entity import SessionEntity
from app.models.user import User
from app.schemas.session_entity import (
    SessionEntityPlayerRead,
    SessionEntityRead,
)
from app.services.centrifugo import centrifugo
from app.services.realtime import (
    build_event,
    campaign_channel,
    event_version,
    session_channel,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def require_identifier(value: str | None, detail: str) -> str:
    if value is None:
        raise HTTPException(status_code=500, detail=detail)
    return value


def session_id(session_entry: Session) -> str:
    return require_identifier(session_entry.id, "Session is missing an id")


def session_entity_id(session_entity: SessionEntity) -> str:
    return require_identifier(session_entity.id, "Session entity is missing an id")


def get_session_entry(session_id_value: str, db: DbSession) -> Session:
    entry = db.get(Session, session_id_value)
    if entry is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return entry


def require_session_gm(session_entry: Session, user: User, db: DbSession):
    return require_gm(session_entry.campaign_id, user, db)[1]


def get_session_entity(
    session_id_value: str,
    session_entity_id_value: str,
    db: DbSession,
) -> SessionEntity | None:
    return db.exec(
        select(SessionEntity).where(
            SessionEntity.id == session_entity_id_value,
            SessionEntity.session_id == session_id_value,
        )
    ).first()


def get_session_entity_or_404(
    session_id_value: str,
    session_entity_id_value: str,
    db: DbSession,
) -> SessionEntity:
    entry = get_session_entity(session_id_value, session_entity_id_value, db)
    if entry is None:
        raise HTTPException(status_code=404, detail="Session entity not found")
    return entry


def get_campaign_entity(
    campaign_entity_id: str,
    db: DbSession,
) -> CampaignEntity | None:
    return db.get(CampaignEntity, campaign_entity_id)


def get_campaign_entity_for_session_or_404(
    campaign_entity_id: str,
    session_entry: Session,
    db: DbSession,
) -> CampaignEntity:
    campaign_entity = db.exec(
        select(CampaignEntity).where(
            CampaignEntity.id == campaign_entity_id,
            CampaignEntity.campaign_id == session_entry.campaign_id,
        )
    ).first()
    if campaign_entity is None:
        raise HTTPException(status_code=404, detail="Campaign entity not found")
    return campaign_entity


def to_session_entity_read(
    session_entity: SessionEntity,
    campaign_entity: CampaignEntity | None,
) -> SessionEntityRead:
    return SessionEntityRead(
        id=session_entity_id(session_entity),
        sessionId=session_entity.session_id,
        campaignEntityId=session_entity.campaign_entity_id,
        visibleToPlayers=session_entity.visible_to_players,
        currentHp=session_entity.current_hp,
        overrides=session_entity.overrides,
        label=session_entity.label,
        revealedAt=session_entity.revealed_at,
        createdAt=session_entity.created_at,
        updatedAt=session_entity.updated_at,
        entity=to_campaign_entity_read(campaign_entity) if campaign_entity else None,
    )


def to_session_entity_player_read(
    session_entity: SessionEntity,
    campaign_entity: CampaignEntity | None,
) -> SessionEntityPlayerRead:
    return SessionEntityPlayerRead(
        id=session_entity_id(session_entity),
        sessionId=session_entity.session_id,
        campaignEntityId=session_entity.campaign_entity_id,
        currentHp=session_entity.current_hp,
        label=session_entity.label,
        revealedAt=session_entity.revealed_at,
        entity=to_campaign_entity_public_read(campaign_entity) if campaign_entity else None,
    )


def entity_event_payload(
    session_entry: Session,
    session_entity: SessionEntity,
    campaign_entity: CampaignEntity | None,
    *,
    previous_hp: int | None = None,
    hp_delta: int | None = None,
) -> dict:
    payload = {
        "sessionId": session_id(session_entry),
        "campaignId": session_entry.campaign_id,
        "partyId": session_entry.party_id,
        "sessionEntityId": session_entity_id(session_entity),
        "campaignEntityId": session_entity.campaign_entity_id,
        "visibleToPlayers": session_entity.visible_to_players,
        "label": session_entity.label,
        "currentHp": session_entity.current_hp,
        "entityName": campaign_entity.name if campaign_entity else (session_entity.label or "Entity"),
        "entityCategory": campaign_entity.category if campaign_entity else None,
        "maxHp": campaign_entity.max_hp if campaign_entity else None,
        "armorClass": campaign_entity.armor_class if campaign_entity else None,
        "speedMeters": campaign_entity.speed_meters if campaign_entity else None,
    }
    if previous_hp is not None:
        payload["previousHp"] = previous_hp
    if hp_delta is not None:
        payload["hpDelta"] = hp_delta
    return payload


async def publish_entity_event(
    session_entry: Session,
    event_type: str,
    payload: dict,
    version_source: datetime | None = None,
) -> None:
    version = event_version(version_source or utcnow())
    event = build_event(event_type, payload, version=version)
    await centrifugo.publish(session_channel(session_id(session_entry)), event)
    await centrifugo.publish(campaign_channel(session_entry.campaign_id), event)


def list_session_entity_pairs(
    session_id_value: str,
    db: DbSession,
    *,
    visible_only: bool = False,
) -> list[tuple[SessionEntity, CampaignEntity | None]]:
    statement = select(SessionEntity).where(SessionEntity.session_id == session_id_value)
    if visible_only:
        statement = statement.where(SessionEntity.visible_to_players == True)
    entries = list(db.exec(statement).all())
    entries.sort(key=lambda entry: entry.created_at)
    return [(entry, get_campaign_entity(entry.campaign_entity_id, db)) for entry in entries]
