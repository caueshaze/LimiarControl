from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_gm
from app.db.session import get_session
from app.models.npc import NPC
from app.models.user import User
from app.schemas.npc import NpcCreate, NpcRead, NpcUpdate

router = APIRouter()


def to_npc_read(entry: NPC) -> NpcRead:
    return NpcRead(
        id=entry.id,
        campaignId=entry.campaign_id,
        name=entry.name,
        race=entry.race,
        role=entry.role,
        trait=entry.trait,
        goal=entry.goal,
        secret=entry.secret,
        notes=entry.notes,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


@router.get("/{campaign_id}/npcs", response_model=list[NpcRead])
def list_npcs(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    statement = select(NPC).where(NPC.campaign_id == campaign_id).order_by(NPC.created_at.desc())
    entries = session.exec(statement).all()
    return [to_npc_read(entry) for entry in entries]


@router.post("/{campaign_id}/npcs", response_model=NpcRead, status_code=201)
def create_npc(
    campaign_id: str,
    payload: NpcCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    if not payload.name.strip() or not payload.trait.strip() or not payload.goal.strip():
        raise HTTPException(status_code=400, detail="Invalid payload")
    entry = NPC(
        id=str(uuid4()),
        campaign_id=campaign_id,
        name=payload.name.strip(),
        race=payload.race,
        role=payload.role,
        trait=payload.trait.strip(),
        goal=payload.goal.strip(),
        secret=payload.secret,
        notes=payload.notes,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return to_npc_read(entry)


@router.put("/{campaign_id}/npcs/{npc_id}", response_model=NpcRead)
def update_npc(
    campaign_id: str,
    npc_id: str,
    payload: NpcUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    entry = session.exec(
        select(NPC).where(NPC.id == npc_id, NPC.campaign_id == campaign_id)
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="NPC not found")
    if not payload.name.strip() or not payload.trait.strip() or not payload.goal.strip():
        raise HTTPException(status_code=400, detail="Invalid payload")
    entry.name = payload.name.strip()
    entry.race = payload.race
    entry.role = payload.role
    entry.trait = payload.trait.strip()
    entry.goal = payload.goal.strip()
    entry.secret = payload.secret
    entry.notes = payload.notes
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return to_npc_read(entry)


@router.delete("/{campaign_id}/npcs/{npc_id}", status_code=204)
def delete_npc(
    campaign_id: str,
    npc_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    entry = session.exec(
        select(NPC).where(NPC.id == npc_id, NPC.campaign_id == campaign_id)
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="NPC not found")
    session.delete(entry)
    session.commit()
    return None
