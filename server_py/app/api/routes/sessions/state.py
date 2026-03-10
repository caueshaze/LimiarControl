from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version
from app.models.campaign import RoleMode
from app.models.campaign_member import CampaignMember
from app.models.character_sheet import CharacterSheet
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session, SessionStatus
from app.models.session_state import SessionState
from app.schemas.session_state import SessionStateRead, SessionStateUpdate

router = APIRouter()

_REQUIRED_SHEET_KEYS = {
    "name",
    "class",
    "level",
    "background",
    "playerName",
    "race",
    "alignment",
    "abilities",
    "savingThrowProficiencies",
    "skillProficiencies",
    "equippedArmor",
    "currency",
    "conditions",
}


def _to_read(entry: SessionState) -> SessionStateRead:
    return SessionStateRead(
        id=entry.id,
        sessionId=entry.session_id,
        playerUserId=entry.player_user_id,
        state=entry.state_json,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


def _get_session_entry(session_id: str, db: DbSession) -> Session:
    entry = db.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status not in (SessionStatus.LOBBY, SessionStatus.ACTIVE):
        raise HTTPException(status_code=400, detail="Session is not active")
    return entry


def _require_session_view_access(
    entry: Session,
    user,
    db: DbSession,
    player_user_id: str | None = None,
) -> None:
    if entry.party_id:
        party = db.exec(select(Party).where(Party.id == entry.party_id)).first()
        if not party:
            raise HTTPException(status_code=404, detail="Party not found")
        if party.gm_user_id == user.id:
            return

        member = db.exec(
            select(PartyMember).where(
                PartyMember.party_id == entry.party_id,
                PartyMember.user_id == user.id,
                PartyMember.status == PartyMemberStatus.JOINED,
            )
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not a party member")
        if player_user_id and player_user_id != user.id:
            raise HTTPException(status_code=403, detail="GM required")
        return

    campaign_member = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not campaign_member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    if player_user_id and player_user_id != user.id and campaign_member.role_mode != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")


def _require_session_gm(entry: Session, user, db: DbSession) -> None:
    if entry.party_id:
        party = db.exec(select(Party).where(Party.id == entry.party_id)).first()
        if not party or party.gm_user_id != user.id:
            raise HTTPException(status_code=403, detail="GM required")
        return

    campaign_member = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not campaign_member or campaign_member.role_mode != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")


def _seed_state_from_character_sheet(
    session_id: str,
    player_user_id: str,
    party_id: str | None,
    db: DbSession,
) -> SessionState | None:
    if not party_id:
        return None
    base_sheet = db.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == player_user_id,
        )
    ).first()
    if not base_sheet:
        return None
    entry = SessionState(
        id=str(uuid4()),
        session_id=session_id,
        player_user_id=player_user_id,
        state_json=base_sheet.data if isinstance(base_sheet.data, dict) else {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _ensure_session_state(
    state: SessionState | None,
    session_id: str,
    player_user_id: str,
    party_id: str | None,
    db: DbSession,
) -> SessionState | None:
    if not state:
        return _seed_state_from_character_sheet(session_id, player_user_id, party_id, db)

    if isinstance(state.state_json, dict) and _REQUIRED_SHEET_KEYS.issubset(state.state_json.keys()):
        return state

    base_sheet = db.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == player_user_id,
        )
    ).first()
    if not base_sheet or not isinstance(base_sheet.data, dict):
        return state

    state.state_json = dict(base_sheet.data)
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


@router.get("/sessions/{session_id}/state/me", response_model=SessionStateRead)
def get_my_session_state(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = _get_session_entry(session_id, session)
    _require_session_view_access(entry, user, session, user.id)
    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == user.id,
        )
    ).first()
    state = _ensure_session_state(state, session_id, user.id, entry.party_id, session)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found")
    return _to_read(state)


@router.get("/sessions/{session_id}/state/{player_user_id}", response_model=SessionStateRead)
def get_player_session_state(
    session_id: str,
    player_user_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = _get_session_entry(session_id, session)
    _require_session_view_access(entry, user, session, player_user_id)
    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == player_user_id,
        )
    ).first()
    state = _ensure_session_state(state, session_id, player_user_id, entry.party_id, session)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found")
    return _to_read(state)


@router.put("/sessions/{session_id}/state/{player_user_id}", response_model=SessionStateRead)
async def update_player_session_state(
    session_id: str,
    player_user_id: str,
    payload: SessionStateUpdate,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = _get_session_entry(session_id, session)
    _require_session_gm(entry, user, session)
    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == player_user_id,
        )
    ).first()
    state = _ensure_session_state(state, session_id, player_user_id, entry.party_id, session)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found")

    state.state_json = payload.state
    session.add(state)
    session.commit()
    session.refresh(state)

    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event(
            "session_state_updated",
            {
                "sessionId": entry.id,
                "campaignId": entry.campaign_id,
                "partyId": entry.party_id,
                "playerUserId": player_user_id,
            },
            version=event_version(state.updated_at or state.created_at),
        ),
    )
    return _to_read(state)
