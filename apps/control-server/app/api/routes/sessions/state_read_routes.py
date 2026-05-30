from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import select

from app.models.session_state import SessionState


def get_my_session_state_impl(
    *,
    session_id: str,
    user,
    session,
    get_session_entry,
    require_session_view_access,
    ensure_session_state,
    to_state_read,
):
    entry = get_session_entry(session_id, session)
    require_session_view_access(entry, user, session, user.id)
    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == user.id,
        )
    ).first()
    state = ensure_session_state(state, session_id, user.id, entry.party_id, session)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found")
    return to_state_read(state)


def get_player_session_state_impl(
    *,
    session_id: str,
    player_user_id: str,
    user,
    session,
    get_session_entry,
    require_session_view_access,
    ensure_session_state,
    to_state_read,
):
    entry = get_session_entry(session_id, session)
    require_session_view_access(entry, user, session, player_user_id)
    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == player_user_id,
        )
    ).first()
    state = ensure_session_state(state, session_id, player_user_id, entry.party_id, session)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found")
    return to_state_read(state)
