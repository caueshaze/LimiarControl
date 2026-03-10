from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.db.session import get_session
from app.models.campaign import RoleMode
from app.models.campaign_member import CampaignMember
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session, SessionStatus
from app.schemas.session import ActiveSessionRead, LobbyStatusRead
from ._shared import (
    _lobby_expected,
    _lobby_ready,
    check_character_sheets,
    to_session_read,
)

router = APIRouter()


@router.get("/sessions/{session_id}/lobby")
def get_lobby_status(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    expected = _lobby_expected.get(session_id, {})
    ready = list(_lobby_ready.get(session_id, set()))
    return LobbyStatusRead(
        sessionId=session_id,
        expected=[{"userId": uid, "displayName": name} for uid, name in expected.items()],
        ready=ready,
    )


@router.post("/sessions/{session_id}/lobby/join")
async def join_lobby(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status != SessionStatus.LOBBY:
        raise HTTPException(status_code=400, detail="Session is not in lobby state")

    if entry.party_id:
        member = session.exec(
            select(PartyMember).where(
                PartyMember.party_id == entry.party_id,
                PartyMember.user_id == user.id,
                PartyMember.status == PartyMemberStatus.JOINED,
            )
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not a party member")

    expected = _lobby_expected.get(session_id, {})
    if session_id not in _lobby_ready:
        _lobby_ready[session_id] = set()
    _lobby_ready[session_id].add(user.id)

    display_name = expected.get(user.id, user.display_name or user.username or user.id)
    ready_count = len(_lobby_ready[session_id])
    total_count = len(expected)
    join_version = event_version()

    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event(
            "player_joined_lobby",
            {
                "sessionId": session_id,
                "userId": user.id,
                "displayName": display_name,
                "readyCount": ready_count,
                "totalCount": total_count,
            },
            version=join_version,
        ),
    )

    if expected and _lobby_ready[session_id] >= set(expected.keys()):
        now = datetime.now(timezone.utc)
        entry.status = SessionStatus.ACTIVE
        entry.started_at = now
        session.add(entry)
        session.commit()
        session.refresh(entry)
        _lobby_ready.pop(session_id, None)
        _lobby_expected.pop(session_id, None)
        version = event_version(entry.started_at or now)
        started_payload = {
            "sessionId": entry.id,
            "campaignId": entry.campaign_id,
            "title": entry.title,
            "startedAt": now.isoformat(),
        }
        await centrifugo.publish(
            session_channel(entry.id),
            build_event("session_started", started_payload, version=version),
        )
        await centrifugo.publish(
            campaign_channel(entry.campaign_id),
            build_event("session_started", started_payload, version=version),
        )

    return {"ok": True}


@router.post("/sessions/{session_id}/lobby/force-start")
async def force_start_lobby(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status == SessionStatus.ACTIVE:
        # Already activated (e.g. all players joined simultaneously) — idempotent
        return ActiveSessionRead(**to_session_read(entry).model_dump())
    if entry.status != SessionStatus.LOBBY:
        raise HTTPException(status_code=400, detail="Session is not in lobby state")

    if entry.party_id:
        party = session.exec(select(Party).where(Party.id == entry.party_id)).first()
        if not party or party.gm_user_id != user.id:
            raise HTTPException(status_code=403, detail="GM required")
    else:
        member = session.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == entry.campaign_id,
                CampaignMember.user_id == user.id,
            )
        ).first()
        if not member or member.role_mode != RoleMode.GM:
            raise HTTPException(status_code=403, detail="GM required")

    if entry.party_id:
        player_members = session.exec(
            select(PartyMember).where(
                PartyMember.party_id == entry.party_id,
                PartyMember.role == RoleMode.PLAYER,
                PartyMember.status == PartyMemberStatus.JOINED,
            )
        ).all()
        check_character_sheets(entry.party_id, player_members, session)

    now = datetime.now(timezone.utc)
    entry.status = SessionStatus.ACTIVE
    entry.started_at = now
    session.add(entry)
    session.commit()
    session.refresh(entry)
    _lobby_ready.pop(session_id, None)
    _lobby_expected.pop(session_id, None)
    version = event_version(entry.started_at or now)
    started_payload = {
        "sessionId": entry.id,
        "campaignId": entry.campaign_id,
        "title": entry.title,
        "startedAt": now.isoformat(),
    }

    await centrifugo.publish(
        session_channel(entry.id),
        build_event("session_started", started_payload, version=version),
    )
    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event("session_started", started_payload, version=version),
    )
    return ActiveSessionRead(**to_session_read(entry).model_dump())
