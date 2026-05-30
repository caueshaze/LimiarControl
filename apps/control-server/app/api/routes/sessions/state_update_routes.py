from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import select

from app.models.campaign_member import CampaignMember
from app.models.item import ItemType
from app.models.session_state import SessionState


def clear_my_concentration_impl(
    *,
    session_id: str,
    payload,
    user,
    session,
    get_session_entry,
    require_session_view_access,
    ensure_session_state,
    clear_persisted_concentration_effects,
    finalize_session_state_data,
    publish_state_update,
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

    updated = clear_persisted_concentration_effects(
        state.state_json,
        concentration_group=payload.concentrationGroup,
    )
    state.state_json = finalize_session_state_data(updated)
    session.add(state)
    session.commit()
    session.refresh(state)

    return entry, state, to_state_read, publish_state_update


async def publish_and_return_state(*, entry, user_id: str, state, publish_state_update, to_state_read):
    await publish_state_update(
        entry,
        user_id,
        state.updated_at or state.created_at,
        state.state_json if isinstance(state.state_json, dict) else None,
    )
    return to_state_read(state)
