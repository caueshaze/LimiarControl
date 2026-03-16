from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.api.deprecation import log_deprecated_route
from app.db.session import get_session
from app.models.campaign import RoleMode
from app.models.campaign_member import CampaignMember
from app.models.party import Party
from app.models.session import Session, SessionStatus
from app.models.session_runtime import SessionRuntime
from app.schemas.session import ActiveSessionRead
from app.services.centrifugo import centrifugo
from app.services.realtime import (
    build_event,
    campaign_channel,
    event_version,
    session_channel,
)
from ._shared import (
    DEPRECATION_REMOVAL_DATE,
    require_party_gm,
    resolve_party_id_for_campaign,
    to_session_read,
)

router = APIRouter()


@router.post("/parties/{party_id}/sessions/{session_id}/close", response_model=ActiveSessionRead)
async def close_party_session(
    party_id: str,
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    party = require_party_gm(party_id, user, session)
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry or entry.party_id != party.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status not in (SessionStatus.ACTIVE, SessionStatus.LOBBY):
        raise HTTPException(status_code=400, detail="Session is not active")
    now = datetime.now(timezone.utc)
    entry.status = SessionStatus.CLOSED
    entry.ended_at = now
    if entry.started_at:
        entry.duration_seconds = max(
            0, entry.duration_seconds + int((now - entry.started_at).total_seconds())
        )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    runtime = session.exec(
        select(SessionRuntime).where(SessionRuntime.session_id == entry.id)
    ).first()
    if runtime:
        runtime.lobby_expected = []
        runtime.lobby_ready = []
        runtime.shop_open = False
        session.add(runtime)
        session.commit()
        session.refresh(entry)
    closed_payload = {
        "sessionId": entry.id,
        "campaignId": party.campaign_id,
        "partyId": party.id,
        "endedAt": now.isoformat(),
    }
    version = event_version(now)
    await centrifugo.publish(
        session_channel(entry.id),
        build_event("session_closed", closed_payload, version=version),
    )
    await centrifugo.publish(
        campaign_channel(party.campaign_id),
        build_event("session_closed", closed_payload, version=version),
    )
    return ActiveSessionRead(**to_session_read(entry).model_dump())


@router.post("/sessions/{session_id}/close", response_model=ActiveSessionRead)
async def close_session(
    session_id: str,
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
    if not member or member.role_mode != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")
    if entry.party_id:
        party = session.exec(select(Party).where(Party.id == entry.party_id)).first()
        if not party or party.gm_user_id != user.id:
            raise HTTPException(status_code=403, detail="GM required")
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")
    now = datetime.now(timezone.utc)
    entry.status = SessionStatus.CLOSED
    entry.ended_at = now
    if entry.started_at:
        entry.duration_seconds = max(
            0, entry.duration_seconds + int((now - entry.started_at).total_seconds())
        )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    runtime = session.exec(
        select(SessionRuntime).where(SessionRuntime.session_id == entry.id)
    ).first()
    if runtime:
        runtime.lobby_expected = []
        runtime.lobby_ready = []
        runtime.shop_open = False
        session.add(runtime)
        session.commit()
        session.refresh(entry)
    closed_payload = {
        "sessionId": entry.id,
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "endedAt": now.isoformat(),
    }
    version = event_version(now)
    await centrifugo.publish(
        session_channel(entry.id),
        build_event("session_closed", closed_payload, version=version),
    )
    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event("session_closed", closed_payload, version=version),
    )
    return ActiveSessionRead(**to_session_read(entry).model_dump())


@router.post(
    "/campaigns/{campaign_id}/session/end",
    response_model=ActiveSessionRead,
    deprecated=True,
)
async def end_session_deprecated(
    campaign_id: str,
    request: Request,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    """Deprecated. Remove after 2026-06-01. Use /api/sessions/{session_id}/close."""
    log_deprecated_route(
        request,
        old_path="/api/campaigns/{campaign_id}/session/end",
        new_path="/api/sessions/{session_id}/close",
        removal_date=DEPRECATION_REMOVAL_DATE,
        extra={"campaign_id": campaign_id, "user_id": getattr(user, "id", None)},
    )
    party_id = resolve_party_id_for_campaign(campaign_id, session)
    if party_id:
        active = session.exec(
            select(Session).where(
                Session.party_id == party_id, Session.status == SessionStatus.ACTIVE,
            )
        ).first()
    else:
        active = session.exec(
            select(Session).where(
                Session.campaign_id == campaign_id, Session.status == SessionStatus.ACTIVE,
            )
        ).first()
    if not active:
        raise HTTPException(status_code=404, detail="No active session to end")
    return await close_session(active.id, user, session)


@router.post("/sessions/{session_id}/resume", response_model=ActiveSessionRead)
async def resume_session(
    session_id: str,
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
    if not member or member.role_mode != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")
    if entry.party_id:
        party = session.exec(select(Party).where(Party.id == entry.party_id)).first()
        if not party or party.gm_user_id != user.id:
            raise HTTPException(status_code=403, detail="GM required")

    active = session.exec(
        select(Session).where(
            Session.campaign_id == entry.campaign_id, Session.status == SessionStatus.ACTIVE,
        )
    ).first()
    if active and active.id != entry.id:
        now = datetime.now(timezone.utc)
        active.status = SessionStatus.CLOSED
        active.ended_at = now
        if active.started_at:
            active.duration_seconds = max(
                0, active.duration_seconds + int((now - active.started_at).total_seconds())
            )
        session.add(active)
        session.commit()
        closed_payload = {
            "sessionId": active.id,
            "campaignId": active.campaign_id,
            "endedAt": now.isoformat(),
        }
        version = event_version(now)
        await centrifugo.publish(
            session_channel(active.id),
            build_event("session_closed", closed_payload, version=version),
        )
        await centrifugo.publish(
            campaign_channel(active.campaign_id),
            build_event("session_closed", closed_payload, version=version),
        )

    now = datetime.now(timezone.utc)
    entry.status = SessionStatus.ACTIVE
    entry.started_at = now
    entry.ended_at = None
    session.add(entry)
    session.commit()
    session.refresh(entry)
    resumed_payload = {
        "sessionId": entry.id,
        "campaignId": entry.campaign_id,
        "joinCode": entry.join_code,
        "startedAt": entry.started_at.isoformat() if entry.started_at else None,
    }
    version = event_version(entry.started_at or now)
    await centrifugo.publish(
        session_channel(entry.id),
        build_event("session_resumed", resumed_payload, version=version),
    )
    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event(
            "session_resumed",
            {
                "sessionId": entry.id,
                "campaignId": entry.campaign_id,
                "startedAt": entry.started_at.isoformat() if entry.started_at else None,
            },
            version=version,
        ),
    )
    return ActiveSessionRead(**to_session_read(entry).model_dump())
