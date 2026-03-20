from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_campaign_member, require_gm
from app.db.session import get_session
from app.models.campaign_entity import CampaignEntity
from app.models.session import Session as SessionModel, SessionStatus
from app.models.session_entity import SessionEntity
from app.models.user import User
from app.schemas.campaign_entity import (
    VALID_CATEGORIES,
    AbilityStats,
    CampaignEntityCreate,
    CampaignEntityPublicRead,
    CampaignEntityRead,
    CampaignEntityUpdate,
)

router = APIRouter()


def _stats_to_dict(stats: AbilityStats | None) -> dict | None:
    if stats is None:
        return None
    dumped = stats.model_dump(exclude_none=True)
    return dumped if dumped else None


def _dict_to_stats(raw: dict | None) -> AbilityStats | None:
    if not raw:
        return None
    return AbilityStats(**raw)


def to_campaign_entity_read(entry: CampaignEntity) -> CampaignEntityRead:
    return CampaignEntityRead(
        id=entry.id,
        campaignId=entry.campaign_id,
        name=entry.name,
        category=entry.category,
        description=entry.description,
        imageUrl=entry.image_url,
        baseHp=entry.base_hp,
        baseAc=entry.base_ac,
        stats=_dict_to_stats(entry.stats),
        actions=entry.actions,
        notesPrivate=entry.notes_private,
        notesPublic=entry.notes_public,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


def to_campaign_entity_public_read(entry: CampaignEntity) -> CampaignEntityPublicRead:
    return CampaignEntityPublicRead(
        id=entry.id,
        campaignId=entry.campaign_id,
        name=entry.name,
        category=entry.category,
        description=entry.description,
        imageUrl=entry.image_url,
        baseHp=entry.base_hp,
        baseAc=entry.base_ac,
        stats=_dict_to_stats(entry.stats),
        actions=entry.actions,
        notesPublic=entry.notes_public,
        createdAt=entry.created_at,
    )


@router.get("/{campaign_id}/entities", response_model=list[CampaignEntityRead])
def list_campaign_entities(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    statement = (
        select(CampaignEntity)
        .where(CampaignEntity.campaign_id == campaign_id)
        .order_by(CampaignEntity.created_at.desc())
    )
    entries = session.exec(statement).all()
    return [to_campaign_entity_read(e) for e in entries]


@router.post("/{campaign_id}/entities", response_model=CampaignEntityRead, status_code=201)
def create_campaign_entity(
    campaign_id: str,
    payload: CampaignEntityCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}")
    entry = CampaignEntity(
        id=str(uuid4()),
        campaign_id=campaign_id,
        name=payload.name.strip(),
        category=payload.category,
        description=payload.description,
        image_url=payload.imageUrl,
        base_hp=payload.baseHp,
        base_ac=payload.baseAc,
        stats=_stats_to_dict(payload.stats),
        actions=payload.actions,
        notes_private=payload.notesPrivate,
        notes_public=payload.notesPublic,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return to_campaign_entity_read(entry)


@router.put("/{campaign_id}/entities/{entity_id}", response_model=CampaignEntityRead)
def update_campaign_entity(
    campaign_id: str,
    entity_id: str,
    payload: CampaignEntityUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    entry = session.exec(
        select(CampaignEntity).where(
            CampaignEntity.id == entity_id,
            CampaignEntity.campaign_id == campaign_id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entity not found")
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}")
    entry.name = payload.name.strip()
    entry.category = payload.category
    entry.description = payload.description
    entry.image_url = payload.imageUrl
    entry.base_hp = payload.baseHp
    entry.base_ac = payload.baseAc
    entry.stats = _stats_to_dict(payload.stats)
    entry.actions = payload.actions
    entry.notes_private = payload.notesPrivate
    entry.notes_public = payload.notesPublic
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return to_campaign_entity_read(entry)


@router.delete("/{campaign_id}/entities/{entity_id}", status_code=204)
def delete_campaign_entity(
    campaign_id: str,
    entity_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    entry = session.exec(
        select(CampaignEntity).where(
            CampaignEntity.id == entity_id,
            CampaignEntity.campaign_id == campaign_id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entity not found")
    session.delete(entry)
    session.commit()
    return None


@router.get("/{campaign_id}/entities/public", response_model=list[CampaignEntityPublicRead])
def list_public_campaign_entities(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_campaign_member(campaign_id, user, session)
    # Return campaign entities that are currently revealed in any active session
    statement = (
        select(CampaignEntity)
        .join(SessionEntity, SessionEntity.campaign_entity_id == CampaignEntity.id)
        .join(SessionModel, SessionModel.id == SessionEntity.session_id)
        .where(
            CampaignEntity.campaign_id == campaign_id,
            SessionEntity.visible_to_players == True,
            SessionModel.status == SessionStatus.ACTIVE,
        )
        .distinct()
    )
    entries = session.exec(statement).all()
    return [to_campaign_entity_public_read(e) for e in entries]
