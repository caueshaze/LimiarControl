import random
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.campaign_member import CampaignMember
from app.models.roll_event import RollEvent
from app.models.session import Session, SessionStatus
from app.models.user import User
from app.schemas.roll_event import RollEventRead
from app.schemas.session import ManualRollRequest, RollRequest
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, event_version, session_channel
from ._shared import parse_expression, to_roll_read_local

router = APIRouter()


@router.get("/sessions/{session_id}/rolls", response_model=list[RollEventRead])
def list_rolls(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    entries = session.exec(
        select(RollEvent)
        .where(RollEvent.session_id == session_id)
        .order_by(RollEvent.created_at.desc())
        .limit(limit)
    ).all()
    return [to_roll_read_local(e) for e in entries]


@router.post("/sessions/{session_id}/rolls", response_model=RollEventRead)
async def submit_roll(
    session_id: str,
    body: RollRequest,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status not in (SessionStatus.ACTIVE, SessionStatus.LOBBY):
        raise HTTPException(status_code=400, detail="Session is not active")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")

    parsed = parse_expression(body.expression)
    if not parsed:
        raise HTTPException(status_code=400, detail="Invalid dice expression")

    count, sides, modifier = parsed
    label = body.label
    advantage = body.advantage

    if advantage in ("advantage", "disadvantage"):
        set_a = [random.randint(1, sides) for _ in range(count)]
        set_b = [random.randint(1, sides) for _ in range(count)]
        sum_a = sum(set_a)
        sum_b = sum(set_b)
        if advantage == "advantage":
            chosen, other = (set_a, set_b) if sum_a >= sum_b else (set_b, set_a)
        else:
            chosen, other = (set_a, set_b) if sum_a <= sum_b else (set_b, set_a)
        results = chosen + other
        total = sum(chosen) + modifier
        suffix = " (Advantage)" if advantage == "advantage" else " (Disadvantage)"
        label = (label + suffix) if label else suffix.strip()
    else:
        results = [random.randint(1, sides) for _ in range(count)]
        total = sum(results) + modifier

    event = RollEvent(
        id=str(uuid4()),
        campaign_id=entry.campaign_id,
        session_id=session_id,
        user_id=user.id,
        author_name=member.display_name,
        role_mode=member.role_mode,
        label=label,
        expression=body.expression.strip(),
        count=count,
        sides=sides,
        modifier=modifier,
        results=results,
        total=total,
    )
    session.add(event)
    session.commit()
    session.refresh(event)

    roll_read = to_roll_read_local(event)
    payload_out = roll_read.model_dump(mode="json")
    await centrifugo.publish(
        session_channel(session_id),
        build_event("roll_created", payload_out, version=event_version(event.created_at)),
    )

    return roll_read


@router.post("/sessions/{session_id}/rolls/manual", response_model=dict)
async def submit_manual_roll(
    session_id: str,
    payload: ManualRollRequest,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    parsed = parse_expression(payload.expression)
    count, sides, modifier = parsed if parsed else (1, 20, 0)
    event = RollEvent(
        id=str(uuid4()),
        campaign_id=entry.campaign_id,
        session_id=session_id,
        user_id=user.id,
        author_name=member.display_name,
        role_mode=member.role_mode,
        label=payload.label,
        expression=payload.expression,
        count=count,
        sides=sides,
        modifier=modifier,
        results=[payload.result],
        total=payload.result,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    payload_out = to_roll_read_local(event).model_dump(mode="json")
    await centrifugo.publish(
        session_channel(session_id),
        build_event("roll_created", payload_out, version=event_version(event.created_at)),
    )
    return payload_out
